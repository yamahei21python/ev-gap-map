import os
import json
import sqlite3
import logging
import math
import jismesh.utils as ju

logger = logging.getLogger(__name__)

def run_gap_analysis():
    ev_db_path = os.path.join("data", "ev_chargers.db")
    pop_db_path = os.path.join("data", "population.db")
    output_geojson = os.path.join("data", "gap_map.geojson")

    if not os.path.exists(ev_db_path) or not os.path.exists(pop_db_path):
        logger.error("必要なデータベースが見つかりません。ev_chargers.db と population.db を確認してください。")
        return

    # 1. EV充電器データの読み込みとメッシュへの割り当て
    logger.info("EV充電器データを読み込んでいます...")
    ev_conn = sqlite3.connect(ev_db_path)
    ev_conn.row_factory = sqlite3.Row
    ev_cursor = ev_conn.cursor()
    
    # ジオコーディング成功(1)の各スタンド情報を取得
    ev_cursor.execute("""
        SELECT s.latitude, s.longitude, s.name, s.url, COALESCE(SUM(c.count), 1) as total_chargers
        FROM stations s
        LEFT JOIN chargers c ON s.id = c.station_id
        WHERE s.geocoding_status = 1 AND s.latitude IS NOT NULL AND s.longitude IS NOT NULL
        GROUP BY s.id
    """)
    
    mesh_ev_counts = {}
    total_ev_chargers = 0
    
    for row in ev_cursor:
        lat, lon, count = row["latitude"], row["longitude"], row["total_chargers"]
        name, url = row["name"], row["url"]
        
        # 3次メッシュ(1km)コードを計算し文字列化してキーを統一
        meshcode = str(ju.to_meshcode(lat, lon, 3))
        if meshcode not in mesh_ev_counts:
            mesh_ev_counts[meshcode] = {"count": 0, "stations": []}
        
        mesh_ev_counts[meshcode]["count"] += count
        mesh_ev_counts[meshcode]["stations"].append({
            "name": name,
            "url": url,
            "count": int(count)
        })
        total_ev_chargers += count

    ev_conn.close()
    logger.info(f"合計 {total_ev_chargers} 基の充電器を {len(mesh_ev_counts)} 個のメッシュに割り当てました。")

    # 2. 人口データの読み込み
    logger.info("人口データを読み込んでいます...")
    pop_conn = sqlite3.connect(pop_db_path)
    pop_conn.row_factory = sqlite3.Row
    pop_cursor = pop_conn.cursor()
    
    pop_cursor.execute("SELECT mesh_code, population, lat_min, lon_min, lat_max, lon_max, address FROM mesh_population")
    
    mesh_data = {}
    total_population = 0
    
    for row in pop_cursor:
        pop = row["population"]
        if pop <= 0:
            continue
        code = row["mesh_code"]
        # もし9桁(500m)等なら先頭8桁をとって3次メッシュ(1km)に集約する
        code_str = str(code)
        if len(code_str) >= 8:
            code_3rd = code_str[:8]
        else:
            continue
            
        if code_3rd not in mesh_data:
            # 元データの境界(lat_min等)は500m枠の可能性があるため、
            # 新たに1km(3次)メッシュとしての正しい境界座標を計算し直す
            lat, lon = ju.to_meshpoint(code_3rd, 0, 0)
            dlat = 1.0 / 120.0
            dlon = 1.0 / 80.0
            mesh_data[code_3rd] = {
                "population": 0,
                "lat_min": lat,
                "lon_min": lon,
                "lat_max": lat + dlat,
                "lon_max": lon + dlon,
                "address": row["address"] or "取得中"
            }
        mesh_data[code_3rd]["population"] += pop
        total_population += pop

    pop_conn.close()
    
    # ev_countsのキーをマージ(EVはあるが人口が無い地域もカバー)
    for code in mesh_ev_counts.keys():
        if code not in mesh_data:
            # 緯度経度の境界を計算
            lat, lon = ju.to_meshpoint(code, 0, 0)
            dlat = 1.0 / 120.0
            dlon = 1.0 / 80.0
            mesh_data[code] = {
                "population": 0,
                "lat_min": lat,
                "lon_min": lon,
                "lat_max": lat + dlat,
                "lon_max": lon + dlon
            }

    logger.info(f"合計 {total_population} 人のデータを読み込みました。対象メッシュ数: {len(mesh_data)} 個")

    # 3. Gap分析（全国平均からの差分）
    # 全国平均 1人あたりの充電器数
    if total_population == 0:
        logger.error("人口が0のため計算できません。")
        return
        
    national_ratio = total_ev_chargers / total_population
    logger.info(f"全国平均: {national_ratio:.6f} 基/人 (1万人に {national_ratio * 10000:.2f} 基)")

    features = []
    
    for code, data in mesh_data.items():
        pop = data["population"]
        mesh_ev = mesh_ev_counts.get(code, {"count": 0, "stations": []})
        chargers = mesh_ev["count"]
        station_list = mesh_ev["stations"]
        
        # 不要データの除外（軽量化）: 人口が0かつ充電器も0のメッシュは描画しない
        if pop == 0 and chargers == 0:
            continue
            
        # 適正期待値（そのメッシュにあるべき充電器の数）
        expected_chargers = pop * national_ratio
        
        # ギャップ（実際の数 - 期待値）
        gap = chargers - expected_chargers
        
        # GeoJSONのポリゴンを作成
        polygon = [[
            [data["lon_min"], data["lat_min"]],
            [data["lon_max"], data["lat_min"]],
            [data["lon_max"], data["lat_max"]],
            [data["lon_min"], data["lat_max"]],
            [data["lon_min"], data["lat_min"]]
        ]]
        
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": polygon
            },
            "properties": {
                "mesh_code": str(code),
                "population": int(pop),
                "chargers": int(chargers),
                "expected": float(round(expected_chargers, 2)),
                "gap": float(round(gap, 2)),
                "address": data.get("address", "取得中"),
                "stations": station_list
            }
        })

    logger.info(f"GeoJSON 生成開始: 対象 {len(features)} メッシュ")
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    with open(output_geojson, "w", encoding="utf-8") as f:
        json.dump(geojson, f)
        
    logger.info(f"出力完了: {output_geojson}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_gap_analysis()
