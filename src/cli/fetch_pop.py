"""Fetch population command"""

import os
from typing import Optional

from ..core.config import (
    APP_ID,
    ESTAT_BASE_URL,
    MESH_MAP_FILE,
    POP_DB_PATH,
)
from ..core.logging import get_logger
from ..core.http import HTTPClient
from ..db.models import init_db, get_connection, upsert_mesh_population
from ..mesh.utils import get_mesh_polygon


logger = get_logger(__name__)


class PopulationFetcher:
    """Population data fetcher"""

    def __init__(self):
        self.http = HTTPClient(delay=1.0)
        self.stats = {"fetched": 0, "saved": 0, "skipped": 0, "errors": 0}

    def fetch_all(self, db_path: Optional[str] = None):
        """Fetch all population data"""
        init_db(db_path)
        conn = get_connection(db_path)

        if not os.path.exists(MESH_MAP_FILE):
            logger.error(f"mesh_map.json が見つかりません: {MESH_MAP_FILE}")
            return

        import json

        with open(MESH_MAP_FILE, "r") as f:
            mesh_map = json.load(f)

        logger.info(f"全 {len(mesh_map)} 個の1次メッシュ人口データ取得開始")

        for idx, (mesh_code, stats_id) in enumerate(sorted(mesh_map.items()), 1):
            url = f"{ESTAT_BASE_URL}?appId={APP_ID}&statsDataId={stats_id}&cdCat01=0010&metaGetFlg=N"

            try:
                response = self.http.get(url)
                if not response:
                    logger.warning(f"Error: Mesh {mesh_code}")
                    continue

                import json

                data = json.loads(response)
                result_info = data.get("GET_STATS_DATA", {}).get("RESULT", {})

                if result_info.get("STATUS") != 0:
                    logger.warning(
                        f"Mesh {mesh_code}: STATUS {result_info.get('STATUS')}"
                    )
                    continue

                value_list = (
                    data.get("GET_STATS_DATA", {})
                    .get("STATISTICAL_DATA", {})
                    .get("DATA_INF", {})
                    .get("VALUE", [])
                )

                if not value_list:
                    continue

                if isinstance(value_list, dict):
                    value_list = [value_list]

                saved_count = 0
                for item in value_list:
                    sub_mesh_code = item.get("@area")
                    pop_str = item.get("$")

                    if not pop_str or pop_str in ("-", "***", "X"):
                        self.stats["skipped"] += 1
                        continue

                    try:
                        pop = int(pop_str)
                    except ValueError:
                        self.stats["skipped"] += 1
                        continue

                    bbox = get_mesh_polygon(sub_mesh_code)

                    upsert_mesh_population(
                        conn,
                        {
                            "mesh_code": sub_mesh_code,
                            "population": pop,
                            "lat_min": bbox["lat_min"],
                            "lon_min": bbox["lon_min"],
                            "lat_max": bbox["lat_max"],
                            "lon_max": bbox["lon_max"],
                        },
                    )
                    saved_count += 1
                    self.stats["saved"] += 1

                conn.commit()
                self.stats["fetched"] += len(value_list)
                logger.info(
                    f"[{idx}/{len(mesh_map)}] 1次{Mesh_code}: {saved_count} 件保存"
                )

            except Exception as e:
                logger.error(f"Error: Mesh {mesh_code}: {e}")
                self.stats["errors"] += 1

        conn.close()
        logger.info("=== 人口データ取得完了 ===")

        output_path = (
            "data/mesh_population.geojson" if not db_path else "data/test_mesh.geojson"
        )
        self.export_geojson(output_path=output_path, db_path=db_path)

    def export_geojson(
        self,
        output_path: str = "data/mesh_population.geojson",
        db_path: Optional[str] = None,
    ):
        """Export population to GeoJSON"""
        from ..core.geojson import create_polygon, create_feature_collection

        logger.info(f"GeoJSON 生成開始: {output_path}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        conn = get_connection(db_path)
        features = []

        for row in conn.execute("SELECT * FROM mesh_population"):
            polygon = create_polygon(
                row["lon_min"],
                row["lat_min"],
                row["lon_max"],
                row["lat_max"],
            )
            feature = create_feature(
                "Polygon",
                polygon,
                {
                    "mesh_code": row["mesh_code"],
                    "population": row["population"],
                },
            )
            features.append(feature)

        conn.close()

        import json

        geojson = {"type": "FeatureCollection", "features": features}

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(geojson, f)

        logger.info(f"GeoJSON 出力完了: {len(features)} 件")


def cmd_fetch_pop(args):
    """Fetch population command handler"""
    db_path = None
    if args.test_db:
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "test_population.db",
        )
        print(f"Using test DB: {db_path}")

    fetcher = PopulationFetcher()

    if args.geojson_only:
        fetcher.export_geojson(db_path=db_path)
    else:
        fetcher.fetch_all(db_path=db_path)


def add_parser(subparsers):
    """Add fetch-pop subparser"""
    parser = subparsers.add_parser("fetch-pop", help="人口データ取得")
    parser.add_argument("--geojson-only", action="store_true", help="GeoJSON出力のみ")
    parser.add_argument("--test-db", action="store_true", help="テスト用DB使用")
    return parser
