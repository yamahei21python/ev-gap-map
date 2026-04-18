"""Geocode mesh command - Get place names from coordinates using Nominatim"""

import time
from typing import Optional

from ..core.logging import get_logger
from ..core.http import HTTPClient
from ..db.connection import get_connection
from ..mesh.utils import get_mesh_center

logger = get_logger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
DELAY_SECONDS = 1.0  # Nominatim uses 1 request/sec limit


def get_address_from_coords(lat: float, lon: float, http: HTTPClient) -> Optional[str]:
    """Reverse geocode coordinates to address using Nominatim"""
    try:
        params = {
            "format": "json",
            "lat": lat,
            "lon": lon,
            "zoom": 14,
            "addressdetails": 1,
        }
        headers = {
            "User-Agent": "EVCharge-Gap-Map/1.0",
            "Accept-Language": "ja",
        }

        response = http.get(NOMINATIM_URL, params=params, headers=headers)

        if not response:
            return None

        import json

        data = json.loads(response)
        if not data or "address" not in data:
            return None

        addr = data["address"]
        pref = addr.get("state", addr.get("province", ""))
        city = addr.get("city", addr.get("town", addr.get("village", "")))
        suburb = addr.get("suburb", addr.get("neighbourhood", ""))

        full_name = f"{pref}{city}{suburb}" if pref and city else None

        if not full_name:
            return "地名不明"

        return full_name

    except Exception as e:
        logger.error(f"Reverse geocode error ({lat}, {lon}): {e}")
        return None


def batch_geocode_mesh():
    """Batch geocode all unprocessed mesh populations"""
    from ..core.config import POP_DB_PATH

    http = HTTPClient(delay=DELAY_SECONDS)

    conn = get_connection(POP_DB_PATH)

    # Check remaining
    cursor = conn.execute(
        "SELECT COUNT(*) FROM mesh_population WHERE address IS NULL"
    ).fetchone()
    remaining = cursor[0] if cursor else 0

    if remaining == 0:
        logger.info("全てのメッシュの地名が取得済みです")
        conn.close()
        http.close()
        return

    logger.info(f"残り {remaining} 件の地名を取得します")
    logger.info(f"※完了まで約 {remaining * DELAY_SECONDS / 3600:.1f} 時間必要です")

    processed = 0

    try:
        while True:
            # Get batch (50 items, prioritize high population)
            rows = conn.execute(
                """
                SELECT mesh_code, lat_min, lon_min, lat_max, lon_max
                FROM mesh_population
                WHERE address IS NULL
                ORDER BY population DESC
                LIMIT 50
                """
            ).fetchall()

            if not rows:
                break

            for row in rows:
                mesh_code = row["mesh_code"]
                center_lat, center_lon = get_mesh_center(
                    row["lat_min"], row["lon_min"], row["lat_max"], row["lon_max"]
                )

                address = get_address_from_coords(center_lat, center_lon, http)

                if address:
                    conn.execute(
                        "UPDATE mesh_population SET address = ? WHERE mesh_code = ?",
                        (address, mesh_code),
                    )
                    processed += 1

                time.sleep(DELAY_SECONDS)

                if processed % 10 == 0:
                    logger.info(
                        f"進捗: {processed} 件取得 (残 {remaining - processed})"
                    )

            conn.commit()

    except KeyboardInterrupt:
        logger.info("\n中断されました")
        conn.commit()
    finally:
        conn.close()
        http.close()

    logger.info(f"完了: {processed} 件の地名を取得しました")


def cmd_geocode_mesh(args):
    """Geocode mesh command handler"""
    batch_geocode_mesh()


def add_parser(subparsers):
    """Add geocode-mesh subparser"""
    return subparsers.add_parser(
        "geocode-mesh",
        help="人口メッシュの中心座標から地名を取得 (Nominatim API)",
    )
