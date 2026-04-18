"""Database connection management"""

import os
import sqlite3
from pathlib import Path
from typing import Optional

from ..core.config import DB_PATH, DATA_DIR


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Get database connection

    Args:
        db_path: Custom DB path (default: from config)

    Returns:
        SQLite connection with row factory
    """
    path = db_path or DB_PATH

    # Ensure parent directory exists
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Optional[str] = None):
    """
    Initialize database tables

    Args:
        db_path: Custom DB path (default: from config)
    """
    conn = get_connection(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS stations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            prefecture TEXT,
            latitude REAL,
            longitude REAL,
            business_hours TEXT,
            closed_days TEXT,
            url TEXT,
            geocoding_status INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS chargers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT NOT NULL,
            charger_type TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            power_kw REAL,
            max_ampere REAL,
            is_paid BOOLEAN,
            parking_fee TEXT,
            FOREIGN KEY (station_id) REFERENCES stations(id)
        );

        CREATE TABLE IF NOT EXISTS scrape_progress (
            prefecture_code TEXT PRIMARY KEY,
            last_page INTEGER DEFAULT 0,
            total_pages INTEGER,
            completed BOOLEAN DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS mesh_population (
            mesh_code TEXT PRIMARY KEY,
            population INTEGER NOT NULL,
            lat_min REAL,
            lon_min REAL,
            lat_max REAL,
            lon_max REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_stations_prefecture ON stations(prefecture);
        CREATE INDEX IF NOT EXISTS idx_chargers_station_id ON chargers(station_id);
        CREATE INDEX IF NOT EXISTS idx_chargers_type ON chargers(charger_type);
        CREATE INDEX IF NOT EXISTS idx_mesh_population ON mesh_population(population);
    """)
    conn.commit()
    conn.close()
