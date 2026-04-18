"""e-Stat APIクライアントおよび人口データの取得・保存・GeoJSON出力クラス"""
import os
import json
import logging
import time
import requests
import jismesh.utils as ju
from scraper.models import get_connection, init_db, upsert_mesh_population

logger = logging.getLogger(__name__)

# e-Stat API設定
APP_ID = "ba7f4455a7464f319da1a2323405cea4060bcaff"
BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"

MESH_MAP_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mesh_map.json")


class PopulationFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.stats = {"fetched": 0, "saved": 0, "skipped": 0, "errors": 0}

    def get_polygon(self, meshcode):
        """メッシュコードから境界座標(BBOX)を取得"""
        lat, lon = ju.to_meshpoint(meshcode, 0, 0)
        level = ju.to_meshlevel(meshcode)
        
        # 3次メッシュ (1km) または 4次メッシュ (500m)
        if level == 3:
            dlat = 1.0 / 120.0
            dlon = 1.0 / 80.0
        elif level == 4:
            dlat = 1.0 / 240.0
            dlon = 1.0 / 160.0
        else:
            # デフォルトは3次メッシュを想定
            dlat = 1.0 / 120.0
            dlon = 1.0 / 80.0
            
        return {
            "lat_min": lat,
            "lon_min": lon,
            "lat_max": lat + dlat,
            "lon_max": lon + dlon
        }

    def fetch_all(self, db_path=None):
        """
        全国のメッシュデータを取得。
        e-Statのメッシュデータは1次メッシュごとに統計表が分かれているため、
        作成済みのメッシュ<=>統計IDマッピング (mesh_map.json) を読み込んで全件取得する。
        """
        init_db(db_path)
        conn = get_connection(db_path)

        if not os.path.exists(MESH_MAP_FILE):
            logger.error(f"メッシュマップファイルが見つかりません: {MESH_MAP_FILE}")
            return

        with open(MESH_MAP_FILE, "r") as f:
            mesh_map = json.load(f)
        
        logger.info(f"全 {len(mesh_map)} 個の1次メッシュ領域の人口データ取得を開始")

        for idx, (mesh_code, stats_id) in enumerate(sorted(mesh_map.items()), 1):
            url = f"{BASE_URL}?appId={APP_ID}&statsDataId={stats_id}&cdCat01=0010&metaGetFlg=N"
            
            try:
                # タイムアウトを長めに設定 (大量データ対策)
                response = self.session.get(url, timeout=60)
                if response.status_code != 200:
                    logger.warning(f"Error {response.status_code}: Mesh {mesh_code} (ID: {stats_id})")
                    time.sleep(2)
                    continue

                data = response.json()
                result_info = data.get("GET_STATS_DATA", {}).get("RESULT", {})
                
                # データなし
                if result_info.get("STATUS") != 0:
                    logger.warning(f"Mesh {mesh_code}: STATUS {result_info.get('STATUS')}")
                    continue
                    
                value_list = data.get("GET_STATS_DATA", {}).get("STATISTICAL_DATA", {}).get("DATA_INF", {}).get("VALUE", [])
                
                if not value_list:
                    continue
                    
                # 1件取得の場合、リストではなく辞書になる対応
                if isinstance(value_list, dict):
                    value_list = [value_list]

                saved_count = 0
                for item in value_list:
                    sub_mesh_code = item.get("@area")
                    pop_str = item.get("$")
                    
                    if not pop_str or pop_str == "-" or pop_str == "***" or pop_str == "X":
                        self.stats["skipped"] += 1
                        continue
                        
                    try:
                        pop = int(pop_str)
                    except ValueError:
                        self.stats["skipped"] += 1
                        continue

                    # メッシュ境界の計算
                    bbox = self.get_polygon(sub_mesh_code)
                    
                    # DBへ格納
                    upsert_mesh_population(conn, {
                        "mesh_code": sub_mesh_code,
                        "population": pop,
                        "lat_min": bbox["lat_min"],
                        "lon_min": bbox["lon_min"],
                        "lat_max": bbox["lat_max"],
                        "lon_max": bbox["lon_max"]
                    })
                    saved_count += 1
                    self.stats["saved"] += 1

                conn.commit()
                self.stats["fetched"] += len(value_list)
                logger.info(f"[{idx}/{len(mesh_map)}] 1次メッシュ {mesh_code}: {saved_count} 件保存 (累計: {self.stats['saved']})")

                # e-Stat APIの負荷軽減・制限回避のためスリープ
                time.sleep(1.0)

            except requests.Timeout:
                logger.error(f"Timeout processing Mesh {mesh_code} (ID: {stats_id})")
                self.stats["errors"] += 1
            except Exception as e:
                logger.error(f"Error processing Mesh {mesh_code} (ID: {stats_id}): {e}")
                self.stats["errors"] += 1

        conn.close()
        logger.info("=== 人口データ取得完了 ===")
        self.print_stats()
        
        # 取得完了後に GeoJSON を生成
        output_path = "data/mesh_population.geojson" if not db_path else "data/test_mesh.geojson"
        self.export_geojson(output_path=output_path, db_path=db_path)

    def export_geojson(self, output_path="data/mesh_population.geojson", db_path=None):
        """DBから全メッシュデータを読み込み GeoJSON として出力"""
        logger.info(f"GeoJSON 生成開始: {output_path}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        conn = get_connection(db_path)
        features = []
        
        # メモリ節約のためカーソルで逐次処理
        cursor = conn.execute("SELECT * FROM mesh_population")
        for row in cursor:
            # BBOXからポリゴン(5点)を構築
            polygon = [[
                [row["lon_min"], row["lat_min"]],
                [row["lon_max"], row["lat_min"]],
                [row["lon_max"], row["lat_max"]],
                [row["lon_min"], row["lat_max"]],
                [row["lon_min"], row["lat_min"]]
            ]]
            
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": polygon
                },
                "properties": {
                    "mesh_code": row["mesh_code"],
                    "population": row["population"]
                }
            }
            features.append(feature)
            
        conn.close()
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(geojson, f)
            
        logger.info(f"GeoJSON 出力完了: {len(features)} 件記載")

    def print_stats(self):
        logger.info("--- 統計 ---")
        logger.info(f"API取得件数: {self.stats['fetched']}")
        logger.info(f"DB保存件数: {self.stats['saved']}")
        logger.info(f"スキップ数: {self.stats['skipped']}")
        logger.info(f"エラー数:   {self.stats['errors']}")
