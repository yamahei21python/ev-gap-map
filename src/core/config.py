"""Configuration - Application settings and constants"""

import os

# ==================== Paths ====================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# If BASE_DIR is 'src', go up one level
if os.path.basename(BASE_DIR) == "src":
    BASE_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "ev_chargers.db")
POP_DB_PATH = os.path.join(DATA_DIR, "population.db")
MESH_MAP_FILE = os.path.join(DATA_DIR, "mesh_map.json")

# ==================== e-Stat API ====================
APP_ID = "ba7f4455a7464f319da1a2323405cea4060bcaff"
ESTAT_BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"

# ==================== EV Charging Site ====================
EV_BASE_URL = "https://ev.gogo.gs"
EV_SEARCH_URL = f"{EV_BASE_URL}/search"
EV_DETAIL_URL = f"{EV_BASE_URL}/detail"

# ==================== Request Settings ====================
REQUEST_DELAY = 1.5
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
GEOCODE_DELAY = 0.5

# ==================== HTTP Settings ====================
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

# ==================== GSI Geocoding ====================
GSI_GEOCODE_URL = "https://msearch.gsi.go.jp/address-search/AddressSearch"

# ==================== Prefectures ====================
PREFECTURES = {
    "1": "北海道",
    "2": "青森県",
    "3": "岩手県",
    "4": "宮城県",
    "5": "秋田県",
    "6": "山形県",
    "7": "福島県",
    "8": "茨城県",
    "9": "栃木県",
    "10": "群馬県",
    "11": "埼玉県",
    "12": "千葉県",
    "13": "東京都",
    "14": "神奈川県",
    "15": "新潟県",
    "16": "富山県",
    "17": "石川県",
    "18": "福井県",
    "19": "山梨県",
    "20": "長野県",
    "21": "岐阜県",
    "22": "静岡県",
    "23": "愛知県",
    "24": "三重県",
    "25": "滋賀県",
    "26": "京都府",
    "27": "大阪府",
    "28": "兵庫県",
    "29": "奈良県",
    "30": "和歌山県",
    "31": "鳥取県",
    "32": "島根県",
    "33": "岡山県",
    "34": "広島県",
    "35": "山口県",
    "36": "徳島県",
    "37": "香川県",
    "38": "愛媛県",
    "39": "高知県",
    "40": "福岡県",
    "41": "佐賀県",
    "42": "長崎県",
    "43": "熊本県",
    "44": "大分県",
    "45": "宮崎県",
    "46": "鹿児島県",
    "47": "沖縄県",
}
