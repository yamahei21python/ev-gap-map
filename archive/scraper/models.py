"""SQLiteデータベース操作"""
import os
import sqlite3
from datetime import datetime
from .config import DB_PATH, DATA_DIR


def get_connection(db_path=None):
    """DB接続を取得"""
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path=None):
    """テーブルを作成"""
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
            geocoding_status INTEGER DEFAULT 0, -- 0:未処理, 1:成功, 2:失敗
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


def upsert_station(conn, station_data):
    """スタンドをUPSERT"""
    conn.execute("""
        INSERT INTO stations (id, name, address, prefecture, business_hours, closed_days, url, updated_at)
        VALUES (:id, :name, :address, :prefecture, :business_hours, :closed_days, :url, :updated_at)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            address = excluded.address,
            prefecture = excluded.prefecture,
            business_hours = COALESCE(excluded.business_hours, stations.business_hours),
            closed_days = COALESCE(excluded.closed_days, stations.closed_days),
            url = excluded.url,
            updated_at = excluded.updated_at,
            -- 住所が変わった場合はジオコーディングをやり直す
            geocoding_status = CASE WHEN stations.address != excluded.address THEN 0 ELSE stations.geocoding_status END
    """, {
        **station_data,
        "updated_at": datetime.now().isoformat(),
    })


def insert_chargers(conn, station_id, chargers):
    """充電器情報を挿入（既存は削除して再挿入）"""
    conn.execute("DELETE FROM chargers WHERE station_id = ?", (station_id,))
    for charger in chargers:
        conn.execute("""
            INSERT INTO chargers (station_id, charger_type, count, power_kw, max_ampere, is_paid, parking_fee)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            station_id,
            charger.get("charger_type", ""),
            charger.get("count", 1),
            charger.get("power_kw"),
            charger.get("max_ampere"),
            charger.get("is_paid"),
            charger.get("parking_fee"),
        ))


def update_progress(conn, prefecture_code, last_page, total_pages=None, completed=False):
    """スクレイピング進捗を更新"""
    conn.execute("""
        INSERT INTO scrape_progress (prefecture_code, last_page, total_pages, completed, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(prefecture_code) DO UPDATE SET
            last_page = excluded.last_page,
            total_pages = COALESCE(excluded.total_pages, scrape_progress.total_pages),
            completed = excluded.completed,
            updated_at = excluded.updated_at
    """, (
        prefecture_code,
        last_page,
        total_pages,
        completed,
        datetime.now().isoformat(),
    ))


def upsert_mesh_population(conn, mesh_data):
    """人口メッシュ情報をUPSERT"""
    conn.execute("""
        INSERT INTO mesh_population (mesh_code, population, lat_min, lon_min, lat_max, lon_max, updated_at)
        VALUES (:mesh_code, :population, :lat_min, :lon_min, :lat_max, :lon_max, :updated_at)
        ON CONFLICT(mesh_code) DO UPDATE SET
            population = excluded.population,
            lat_min = excluded.lat_min,
            lon_min = excluded.lon_min,
            lat_max = excluded.lat_max,
            lon_max = excluded.lon_max,
            updated_at = excluded.updated_at
    """, {
        **mesh_data,
        "updated_at": datetime.now().isoformat(),
    })


def get_progress(conn, prefecture_code):
    """スクレイピング進捗を取得"""
    row = conn.execute(
        "SELECT * FROM scrape_progress WHERE prefecture_code = ?",
        (prefecture_code,)
    ).fetchone()
    return dict(row) if row else None


def get_stats(conn):
    """統計情報を取得"""
    stats = {}
    stats["total_stations"] = conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
    stats["total_chargers"] = conn.execute("SELECT COUNT(*) FROM chargers").fetchone()[0]
    stats["by_type"] = {}
    for row in conn.execute(
        "SELECT charger_type, SUM(count) as total FROM chargers GROUP BY charger_type"
    ):
        stats["by_type"][row["charger_type"]] = row["total"]
    stats["by_prefecture"] = {}
    for row in conn.execute(
        "SELECT prefecture, COUNT(*) as cnt FROM stations GROUP BY prefecture ORDER BY cnt DESC"
    ):
        stats["by_prefecture"][row["prefecture"]] = row["cnt"]
    return stats
