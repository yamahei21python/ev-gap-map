"""国土地理院 (GSI) API を使用したジオコーディング"""
import requests
import urllib.parse
import time
import logging

logger = logging.getLogger(__name__)

GSI_GEOCODE_URL = "https://msearch.gsi.go.jp/address-search/AddressSearch"

def get_coordinates(address):
    """
    住所文字列から緯度経度を取得する
    
    Returns:
        tuple: (latitude, longitude) または None
    """
    if not address:
        return None
        
    try:
        params = {"q": address}
        # 国土地理院のAPIはUser-Agentが必要な場合がある
        headers = {"User-Agent": "EVCharge-Scraper/1.0"}
        response = requests.get(GSI_GEOCODE_URL, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.warning(f"GSI API Error: {response.status_code} for {address}")
            return None
            
        data = response.json()
        if not data:
            return None
            
        # 最初のヒットを採用
        result = data[0]
        lon, lat = result.get("geometry", {}).get("coordinates", [None, None])
        
        if lat is not None and lon is not None:
            return lat, lon
            
    except Exception as e:
        logger.error(f"Geocoding error for {address}: {e}")
        
    return None

def batch_geocode(conn):
    """
    データベース内の未処理のスタンドに対してジオコーディングを行う
    """
    from .models import get_connection
    
    # geocoding_status = 0 (未処理) のスタンドを取得
    rows = conn.execute("SELECT id, address FROM stations WHERE geocoding_status = 0").fetchall()
    
    if not rows:
        logger.info("ジオコーディングが必要なスタンドはありません。")
        return
        
    logger.info(f"{len(rows)} 件のスタンドをジオコーディング中...")
    
    updated_count = 0
    failed_count = 0
    
    try:
        for row in rows:
            station_id = row["id"]
            address = row["address"]
            
            coords = get_coordinates(address)
            if coords:
                lat, lon = coords
                conn.execute(
                    "UPDATE stations SET latitude = ?, longitude = ?, geocoding_status = 1, updated_at = ? WHERE id = ?",
                    (lat, lon, time.strftime("%Y-%m-%dT%H:%M:%S"), station_id)
                )
                updated_count += 1
            else:
                # 失敗として記録（status=2）
                conn.execute(
                    "UPDATE stations SET geocoding_status = 2, updated_at = ? WHERE id = ?",
                    (time.strftime("%Y-%m-%dT%H:%M:%S"), station_id)
                )
                failed_count += 1
                
            if (updated_count + failed_count) % 10 == 0:
                conn.commit()
                logger.info(f"Progress: {updated_count + failed_count}/{len(rows)} processed (Success: {updated_count}, Failed: {failed_count})")
                
            # API負荷軽減
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        logger.info("ジオコーディングが中断されました。")
    finally:
        conn.commit()
        logger.info(f"ジオコーディング完了: {updated_count} 件成功, {failed_count} 件失敗（再試行スキップ対象）")
