"""Geocode command"""

import time
from typing import Optional, Tuple

from ..core.config import GSI_GEOCODE_URL
from ..core.logging import get_logger
from ..core.http import HTTPClient
from ..db.connection import get_connection
from ..db.models import update_geocoding
from ..db.queries import SELECT_UNGEOCODED


logger = get_logger(__name__)


def get_coordinates(address: str, http: HTTPClient) -> Optional[Tuple[float, float]]:
    """Get coordinates from address using GSI API"""
    if not address:
        return None

    try:
        params = {"q": address}
        headers = {"User-Agent": "EVCharge-Scraper/1.0"}

        # Use HTTP retry client
        response = http.get(GSI_GEOCODE_URL, params=params, headers=headers)

        if not response:
            return None

        import json

        data = json.loads(response)
        if not data:
            return None

        result = data[0]
        lon, lat = result.get("geometry", {}).get("coordinates", [None, None])

        if lat is not None and lon is not None:
            return lat, lon

    except Exception as e:
        logger.error(f"Geocoding error: {address}: {e}")

    return None


def batch_geocode():
    """Batch geocode all unprocessed stations"""
    http = HTTPClient(delay=0.5)

    conn = get_connection()
    rows = conn.execute(SELECT_UNGEOCODED).fetchall()

    if not rows:
        logger.info("ジオコーディングが必要なスタンドはありません")
        conn.close()
        return

    logger.info(f"{len(rows)} 件のスタンドをジオコーディング中...")

    updated = 0
    failed = 0

    try:
        for row in rows:
            station_id = row["id"]
            address = row["address"]

            coords = get_coordinates(address, http)
            if coords:
                lat, lon = coords
                update_geocoding(conn, station_id, lat, lon, status=1)
                updated += 1
            else:
                update_geocoding(conn, station_id, 0, 0, status=2)
                failed += 1

            if (updated + failed) % 10 == 0:
                conn.commit()
                logger.info(
                    f"進捗: {updated + failed}/{len(rows)} (成功: {updated}, 失敗: {failed})"
                )

            time.sleep(0.5)

    except KeyboardInterrupt:
        logger.info("中断されました")
    finally:
        conn.commit()
        conn.close()
        http.close()

    logger.info(f"完了: {updated} 件成功, {failed} 件失敗")


def cmd_geocode(args):
    """Geocode command handler"""
    batch_geocode()


def add_parser(subparsers):
    """Add geocode subparser"""
    return subparsers.add_parser("geocode", help="住所から緯度経度を算出")
