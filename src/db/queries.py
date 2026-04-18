"""SQL query constants"""

# ==================== Stations ====================
INSERT_STATION = """
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
        geocoding_status = CASE WHEN stations.address != excluded.address THEN 0 ELSE stations.geocoding_status END
"""

UPDATE_GEOCODING = """
    UPDATE stations 
    SET latitude = :lat, longitude = :lon, geocoding_status = :status, updated_at = :updated_at
    WHERE id = :id
"""

SELECT_UNGEOCODED = """
    SELECT id, address FROM stations WHERE geocoding_status = 0
"""

SELECT_GEOCODED_STATIONS = """
    SELECT s.latitude, s.longitude, s.name, s.url, COALESCE(SUM(c.count), 1) as total_chargers
    FROM stations s
    LEFT JOIN chargers c ON s.id = c.station_id
    WHERE s.geocoding_status = 1 AND s.latitude IS NOT NULL AND s.longitude IS NOT NULL
    GROUP BY s.id
"""

# ==================== Chargers ====================
DELETE_CHARGERS = "DELETE FROM chargers WHERE station_id = ?"

INSERT_CHARGER = """
    INSERT INTO chargers (station_id, charger_type, count, power_kw, max_ampere, is_paid, parking_fee)
    VALUES (?, ?, ?, ?, ?, ?, ?)
"""

SELECT_CHARGER_STATS = """
    SELECT charger_type, SUM(count) as total FROM chargers GROUP BY charger_type
"""

# ==================== Progress ====================
INSERT_PROGRESS = """
    INSERT INTO scrape_progress (prefecture_code, last_page, total_pages, completed, updated_at)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(prefecture_code) DO UPDATE SET
        last_page = excluded.last_page,
        total_pages = COALESCE(excluded.total_pages, scrape_progress.total_pages),
        completed = excluded.completed,
        updated_at = excluded.updated_at
"""

SELECT_PROGRESS = "SELECT * FROM scrape_progress WHERE prefecture_code = ?"

SELECT_ALL_PROGRESS = "SELECT * FROM scrape_progress"

DELETE_PROGRESS = "DELETE FROM scrape_progress WHERE prefecture_code = ?"

DELETE_ALL_PROGRESS = "DELETE FROM scrape_progress"

# ==================== Mesh Population ====================
INSERT_MESH_POPULATION = """
    INSERT INTO mesh_population (mesh_code, population, lat_min, lon_min, lat_max, lon_max, updated_at)
    VALUES (:mesh_code, :population, :lat_min, :lon_min, :lat_max, :lon_max, :updated_at)
    ON CONFLICT(mesh_code) DO UPDATE SET
        population = excluded.population,
        lat_min = excluded.lat_min,
        lon_min = excluded.lon_min,
        lat_max = excluded.lat_max,
        lon_max = excluded.lon_max,
        updated_at = excluded.updated_at
"""

SELECT_ALL_MESH = "SELECT mesh_code, population, lat_min, lon_min, lat_max, lon_max FROM mesh_population"

SELECT_MESH_BY_CODE = "SELECT * FROM mesh_population WHERE mesh_code = ?"

# ==================== Stats ====================
SELECT_TOTAL_STATIONS = "SELECT COUNT(*) FROM stations"
SELECT_TOTAL_CHARGERS = "SELECT COUNT(*) FROM chargers"
SELECT_PREFECTURE_STATS = "SELECT prefecture, COUNT(*) as cnt FROM stations GROUP BY prefecture ORDER BY cnt DESC"
