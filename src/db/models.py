"""Database models - ORM-like functions"""

from datetime import datetime
from typing import Optional, Dict, Any, List
import sqlite3

from .connection import get_connection, init_db as _init_db
from . import queries as Q


def init_db(db_path: Optional[str] = None):
    """Initialize database (wrapper)"""
    _init_db(db_path)


def upsert_station(conn: sqlite3.Connection, station_data: Dict[str, Any]):
    """Insert or update station"""
    conn.execute(
        Q.INSERT_STATION,
        {
            **station_data,
            "updated_at": datetime.now().isoformat(),
        },
    )


def update_geocoding(
    conn: sqlite3.Connection,
    station_id: str,
    lat: float,
    lon: float,
    status: int = 1,
):
    """Update geocoding result"""
    conn.execute(
        Q.UPDATE_GEOCODING,
        {
            "id": station_id,
            "lat": lat,
            "lon": lon,
            "status": status,
            "updated_at": datetime.now().isoformat(),
        },
    )


def insert_chargers(
    conn: sqlite3.Connection, station_id: str, chargers: List[Dict[str, Any]]
):
    """Insert chargers (replace existing)"""
    conn.execute(Q.DELETE_CHARGERS, (station_id,))
    for charger in chargers:
        conn.execute(
            Q.INSERT_CHARGER,
            (
                station_id,
                charger.get("charger_type", ""),
                charger.get("count", 1),
                charger.get("power_kw"),
                charger.get("max_ampere"),
                charger.get("is_paid"),
                charger.get("parking_fee"),
            ),
        )


def update_progress(
    conn: sqlite3.Connection,
    prefecture_code: str,
    last_page: int,
    total_pages: Optional[int] = None,
    completed: bool = False,
):
    """Update scrape progress"""
    conn.execute(
        Q.INSERT_PROGRESS,
        (
            prefecture_code,
            last_page,
            total_pages,
            completed,
            datetime.now().isoformat(),
        ),
    )


def get_progress(
    conn: sqlite3.Connection, prefecture_code: str
) -> Optional[Dict[str, Any]]:
    """Get scrape progress"""
    row = conn.execute(Q.SELECT_PROGRESS, (prefecture_code,)).fetchone()
    return dict(row) if row else None


def get_all_progress(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Get all scrape progress"""
    return [dict(row) for row in conn.execute(Q.SELECT_ALL_PROGRESS)]


def upsert_mesh_population(conn: sqlite3.Connection, mesh_data: Dict[str, Any]):
    """Insert or update mesh population"""
    conn.execute(
        Q.INSERT_MESH_POPULATION,
        {
            **mesh_data,
            "updated_at": datetime.now().isoformat(),
        },
    )


def get_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Get database statistics"""
    stats = {}
    stats["total_stations"] = conn.execute(Q.SELECT_TOTAL_STATIONS).fetchone()[0]
    stats["total_chargers"] = conn.execute(Q.SELECT_TOTAL_CHARGERS).fetchone()[0]
    stats["by_type"] = {}
    for row in conn.execute(Q.SELECT_CHARGER_STATS):
        stats["by_type"][row["charger_type"]] = row["total"]
    stats["by_prefecture"] = {}
    for row in conn.execute(Q.SELECT_PREFECTURE_STATS):
        stats["by_prefecture"][row["prefecture"]] = row["cnt"]
    return stats


def delete_progress(conn: sqlite3.Connection, prefecture_code: Optional[str] = None):
    """Delete progress (single or all)"""
    if prefecture_code:
        conn.execute(Q.DELETE_PROGRESS, (prefecture_code,))
    else:
        conn.execute(Q.DELETE_ALL_PROGRESS)
