"""スクレイピング設定"""
import os

# ベースURL
BASE_URL = "https://ev.gogo.gs"
SEARCH_URL = f"{BASE_URL}/search"
DETAIL_URL = f"{BASE_URL}/detail"

# リクエスト設定
REQUEST_DELAY = 1.5  # リクエスト間の遅延(秒)
REQUEST_TIMEOUT = 30  # タイムアウト(秒)
MAX_RETRIES = 3  # リトライ回数

# ユーザーエージェント
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
}

# データベース
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DATA_DIR, "ev_chargers.db")

# 都道府県コード (ev.gogo.gs独自 = 1〜47, サイトのselectのvalue値)
PREFECTURES = {
    "1": "北海道", "2": "青森県", "3": "岩手県", "4": "宮城県",
    "5": "秋田県", "6": "山形県", "7": "福島県", "8": "茨城県",
    "9": "栃木県", "10": "群馬県", "11": "埼玉県", "12": "千葉県",
    "13": "東京都", "14": "神奈川県", "15": "新潟県", "16": "富山県",
    "17": "石川県", "18": "福井県", "19": "山梨県", "20": "長野県",
    "21": "岐阜県", "22": "静岡県", "23": "愛知県", "24": "三重県",
    "25": "滋賀県", "26": "京都府", "27": "大阪府", "28": "兵庫県",
    "29": "奈良県", "30": "和歌山県", "31": "鳥取県", "32": "島根県",
    "33": "岡山県", "34": "広島県", "35": "山口県", "36": "徳島県",
    "37": "香川県", "38": "愛媛県", "39": "高知県", "40": "福岡県",
    "41": "佐賀県", "42": "長崎県", "43": "熊本県", "44": "大分県",
    "45": "宮崎県", "46": "鹿児島県", "47": "沖縄県",
}

# 充電タイプ
CHARGER_TYPES = {
    "1": "CHAdeMO",
    "2": "200V",
    "3": "100V",
    "4": "NACS",
}
