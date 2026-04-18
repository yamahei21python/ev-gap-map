import sqlite3
import re
import os

DB_PATH = os.path.join("data", "ev_chargers.db")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT id, address FROM stations WHERE geocoding_status = 2")
rows = cursor.fetchall()

def clean_address(addr):
    # 1. 付近
    addr = addr.replace("　付近", "").replace(" 付近", "").replace("付近", "")
    
    # 2. 奥州市水沢区 -> 奥州市水沢 (平成30年の市制変更)
    addr = addr.replace("奥州市水沢区", "奥州市水沢")
    
    # 3. 浜松市南区 -> 浜松市中央区 (令和6年の区再編)
    addr = addr.replace("浜松市南区", "浜松市中央区")
    
    # 4. 重複
    addr = addr.replace("宮城県宮城県", "宮城県")
    addr = addr.replace("泉南郡泉南郡", "泉南郡")
    
    # 5. 京都の通り名を削除 (京都市〇〇区の後の通〜入ル、上ル、下ルなどを消す)
    # 例: 京都府京都市下京区東堀川通り塩小路下ル松明町1 -> 京都府京都市下京区松明町1
    addr = re.sub(r'(京都市.+?区)(.+?通.+?[上下入]ル?)(.+)', r'\1\3', addr)
    addr = addr.replace("西入ﾙ", "") # 残った半角カナ除去

    # 6. 愛知県犬山市の大字・字の削除方針
    addr = addr.replace("大字犬山字", "犬山")
    
    return addr

updates = 0
for row in rows:
    old_addr = row["address"]
    new_addr = clean_address(old_addr)
    # 全件強制リセットして再試行対象(0)にする
    cursor.execute("UPDATE stations SET address = ?, geocoding_status = 0 WHERE id = ?", (new_addr, row["id"]))
    if new_addr != old_addr:
        updates += 1
        print(f"[{row['id']}] {old_addr} -> {new_addr}")
        
conn.commit()
print(f"Total {updates} addresses cleaned. Geocoding status reset to 0 for all {len(rows)} items.")
conn.close()
