"""Gap map command"""

import os
import json
from typing import Dict, Any, List

from ..core.logging import get_logger
from ..core.geojson import polygon_to_feature, create_feature_collection
from ..db.connection import get_connection
from ..mesh.utils import get_mesh_polygon, normalize_to_3rd_mesh, to_meshcode
from ..db.queries import (
    SELECT_GEOCODED_STATIONS,
    SELECT_ALL_MESH,
)


logger = get_logger(__name__)


def run_gap_analysis():
    """Run gap analysis between EV chargers and population"""
    from ..core.config import DB_PATH, POP_DB_PATH

    ev_db_path = os.path.join("data", "ev_chargers.db")
    pop_db_path = os.path.join("data", "population.db")
    output_path = os.path.join("data", "gap_map.geojson")
    public_output_dir = os.path.join("public", "data")
    public_output_path = os.path.join(public_output_dir, "gap_map.geojson")

    if not os.path.exists(ev_db_path) or not os.path.exists(pop_db_path):
        logger.error("DBが見つかりません: ev_chargers.db, population.db を確認")
        return

    # 1. EV charger data
    logger.info("EV充電器データを読み込み中...")
    ev_conn = get_connection(ev_db_path)

    rows = ev_conn.execute(SELECT_GEOCODED_STATIONS).fetchall()
    ev_conn.close()

    mesh_ev_counts: Dict[str, Dict[str, Any]] = {}
    total_ev_chargers = 0

    for row in rows:
        lat, lon = row["latitude"], row["longitude"]
        count = row["total_chargers"]
        name, url = row["name"], row["url"]

        meshcode = to_meshcode(lat, lon, 3)
        if meshcode not in mesh_ev_counts:
            mesh_ev_counts[meshcode] = {"count": 0, "stations": []}

        mesh_ev_counts[meshcode]["count"] += count
        mesh_ev_counts[meshcode]["stations"].append(
            {
                "name": name,
                "url": url,
                "count": int(count),
            }
        )
        total_ev_chargers += count

    logger.info(
        f"合計 {total_ev_chargers} 基を {len(mesh_ev_counts)} メッシュに割り当て"
    )

    # 2. Population data
    logger.info("人口データを読み込み中...")
    pop_conn = get_connection(pop_db_path)
    rows = pop_conn.execute(SELECT_ALL_MESH).fetchall()
    pop_conn.close()

    mesh_data: Dict[str, Dict[str, Any]] = {}
    total_population = 0

    for row in rows:
        pop = row["population"]
        if pop <= 0:
            continue

        code = normalize_to_3rd_mesh(row["mesh_code"])
        if code not in mesh_data:
            polygon = get_mesh_polygon(code)
            mesh_data[code] = {
                "population": 0,
                **polygon,
            }
        mesh_data[code]["population"] += pop
        total_population += pop

    # Add EV-only meshes (no population)
    for code in mesh_ev_counts:
        if code not in mesh_data:
            polygon = get_mesh_polygon(code)
            mesh_data[code] = {"population": 0, **polygon}

    logger.info(f"人口データ: {total_population} 人, {len(mesh_data)} メッシュ")

    # 3. Gap analysis
    if total_population == 0:
        logger.error("人口が0のため計算できません")
        return

    national_ratio = total_ev_chargers / total_population
    logger.info(f"全国平均: {national_ratio:.6f} 基/人")

    features: List[Dict[str, Any]] = []

    for code, data in mesh_data.items():
        pop = data["population"]
        mesh_ev = mesh_ev_counts.get(code, {"count": 0, "stations": []})
        chargers = mesh_ev["count"]
        station_list = mesh_ev["stations"]

        if pop == 0 and chargers == 0:
            continue

        expected = pop * national_ratio
        gap = chargers - expected

        feature = polygon_to_feature(
            data["lon_min"],
            data["lat_min"],
            data["lon_max"],
            data["lat_max"],
            {
                "mesh_code": str(code),
                "population": int(pop),
                "chargers": int(chargers),
                "expected": float(round(expected, 2)),
                "gap": float(round(gap, 2)),
                "stations": station_list,
            },
        )
        features.append(feature)

    # Output
    geojson = create_feature_collection(features)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f)
    logger.info(f"出力完了: {output_path}")

    if os.path.exists(public_output_dir):
        with open(public_output_path, "w", encoding="utf-8") as f:
            json.dump(geojson, f)
        logger.info(f"Vercel用出力完了: {public_output_path}")


def cmd_gap_map(args):
    """Gap map command handler"""
    run_gap_analysis()


def add_parser(subparsers):
    """Add gap-map subparser"""
    return subparsers.add_parser("gap-map", help="ギャップ分析を実行")
