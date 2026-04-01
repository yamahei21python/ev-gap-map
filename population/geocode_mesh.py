import os
import sqlite3
import time
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Nominatim APIは 1秒に1リクエスト までという厳格な規約があります
DELAY_SECONDS = 0.5
BATCH_SIZE = 50

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def run_geocoder():
    db_path = os.path.join("data", "population.db")
    if not os.path.exists(db_path):
        logger.error(f"データベースが見つかりません: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 未取得のメッシュ数をカウント
    cursor.execute("SELECT COUNT(*) FROM mesh_population WHERE address IS NULL")
    remaining_count = cursor.fetchone()[0]
    
    if remaining_count == 0:
        logger.info("全てのメッシュの地名が既に取得済みです！")
        return

    logger.info(f"========== 地名取得バッチ処理 開始 ==========")
    logger.info(f"未取得のメッシュ: 残り {remaining_count} 件")
    logger.info(f"※Nominatim APIの利用規約(1秒1件制限)に従い、完了まで約 {remaining_count * DELAY_SECONDS / 3600:.1f} 時間かかります。")
    logger.info(f"いつでも Ctrl+C で安全に中断でき、後で続きから再開できます。")
    logger.info(f"=============================================")

    session = requests.Session()
    # ユーザーエージェントを設定 (Nominatim APIの規約で必須)
    session.headers.update({
        "User-Agent": "EVCharge-Gap-Map-Builder/1.0",
        "Accept-Language": "ja"
    })

    processed_in_session = 0
    start_time = time.time()

    try:
        while True:
            # BATCH_SIZE件ずつ取得して処理（メモリ節約と中断しやすさのため）
            # 人口の多い重要なメッシュから優先的に地名を取得する
            cursor.execute("""
                SELECT mesh_code, lat_min, lon_min, lat_max, lon_max 
                FROM mesh_population 
                WHERE address IS NULL 
                ORDER BY population DESC
                LIMIT ?
            """, (BATCH_SIZE,))
            rows = cursor.fetchall()

            if not rows:
                break # 全て完了

            for row in rows:
                mesh_code = row["mesh_code"]
                # メッシュの中心座標を計算
                center_lat = (row["lat_min"] + row["lat_max"]) / 2.0
                center_lon = (row["lon_min"] + row["lon_max"]) / 2.0

                url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={center_lat}&lon={center_lon}&zoom=14&addressdetails=1"
                
                try:
                    res = session.get(url, timeout=10)
                    time.sleep(DELAY_SECONDS) # 規約遵守のためのウェイト

                    if res.status_code == 200:
                        data = res.json()
                        if data and "address" in data:
                            addr = data["address"]
                            pref = addr.get("province", "")
                            city = addr.get("city", addr.get("town", addr.get("village", addr.get("county", ""))))
                            subub = addr.get("suburb", addr.get("neighbourhood", addr.get("quarter", "")))
                            full_name = f"{pref}{city}{subub}"
                            
                            # 空の場合は「データなし」ではなくあえて空文字や地名不明を入れる
                            if not full_name:
                                full_name = "地名不明"
                        else:
                            full_name = "地名不明"
                    else:
                        logger.warning(f"API Error {res.status_code} on mesh {mesh_code}")
                        full_name = "取得失敗"

                except Exception as e:
                    logger.error(f"通信エラー ({mesh_code}): {e}")
                    full_name = "取得エラー"

                # DB更新
                cursor.execute(
                    "UPDATE mesh_population SET address = ? WHERE mesh_code = ?",
                    (full_name, mesh_code)
                )

                processed_in_session += 1
                if processed_in_session % 10 == 0:
                    elapsed = time.time() - start_time
                    logger.info(f"進捗: {processed_in_session}件 処理完了 (残 {remaining_count - processed_in_session}件, 今回の経過時間: {elapsed/60:.1f}分)")

            # バッチ完了ごとにコミット
            conn.commit()

    except KeyboardInterrupt:
        logger.info("\n[停止] ユーザー操作により中断されました。")
        conn.commit()
    except Exception as e:
        logger.error(f"予期せぬエラーで停止しました: {e}")
        conn.commit()
    finally:
        conn.close()
        logger.info(f"処理終了: 今回は合計 {processed_in_session} 件の地名データを保存しました。")

if __name__ == "__main__":
    setup_logging()
    run_geocoder()
