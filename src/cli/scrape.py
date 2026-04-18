"""Scrape command"""

import sys
from typing import Optional

from ..core.config import PREFECTURES, REQUEST_DELAY
from ..core.logging import setup_logging, get_logger
from ..db.models import (
    init_db,
    get_connection,
    upsert_station,
    insert_chargers,
    update_progress,
    get_progress,
)
from ..db.connection import get_connection as db_get_connection
from ..core.http import HTTPClient


logger = get_logger(__name__)


class EVScraper:
    """EV charging station scraper"""

    def __init__(self, delay: float = REQUEST_DELAY):
        self.http = HTTPClient(delay=delay)
        self.stats = {
            "pages_scraped": 0,
            "stations_found": 0,
            "details_fetched": 0,
            "errors": 0,
        }

    def scrape_prefecture(
        self,
        prefecture_code: str,
        max_pages: Optional[int] = None,
        force_update: bool = False,
    ):
        """Scrape single prefecture"""
        from ..core.config import EV_SEARCH_URL, EV_DETAIL_URL
        from ..core.parser import parse_search_page, parse_detail_page

        pref_name = PREFECTURES.get(prefecture_code, prefecture_code)
        logger.info(f"=== {pref_name} ({prefecture_code}) のスクレイピング開始 ===")

        init_db()
        conn = db_get_connection()

        # Check progress
        progress = get_progress(conn, prefecture_code)
        start_page = 1

        if force_update:
            logger.info("強制アップデートモード: ページ 1 から再スキャン")
        elif progress and not progress["completed"]:
            start_page = progress["last_page"] + 1
            logger.info(f"前回の続き: ページ {start_page} から再開")
        elif progress and progress["completed"]:
            logger.info(f"{pref_name} は既に完了。スキップ")
            conn.close()
            return

        # Phase 1: Search pages
        page = start_page
        total_pages = None

        while True:
            url = f"{EV_SEARCH_URL}?ac={prefecture_code}&page={page}"
            logger.info(f"ページ {page} を取得中: {url}")

            html = self.http.get(url)
            if not html:
                logger.error(f"ページ {page} の取得に失敗。スキップ")
                page += 1
                continue

            stations, detected_total = parse_search_page(html)

            if total_pages is None:
                total_pages = detected_total
                logger.info(f"総ページ数: {total_pages}")

            if page > total_pages:
                logger.info(f"ページ {page} は範囲外。終了")
                break

            if not stations:
                if page <= total_pages:
                    logger.warning(f"ページ {page} にスタンドが見つからず")
                break

            # Save stations
            for station in stations:
                upsert_station(
                    conn,
                    {
                        "id": station["id"],
                        "name": station["name"],
                        "address": station["address"],
                        "prefecture": station["prefecture"],
                        "business_hours": None,
                        "closed_days": None,
                        "url": station["url"],
                    },
                )
                self.stats["stations_found"] += 1

            conn.commit()
            self.stats["pages_scraped"] += 1
            update_progress(conn, prefecture_code, page, total_pages)
            conn.commit()

            logger.info(
                f"  → {len(stations)} 件保存 (累計: {self.stats['stations_found']})"
            )

            page += 1
            if max_pages and page > start_page + max_pages - 1:
                logger.info(f"最大ページ数 ({max_pages}) に達")
                break

        # Phase 2: Detail pages
        logger.info("=== 詳細ページ取得開始 ===")
        cursor = conn.execute(
            "SELECT id, url FROM stations WHERE prefecture = ? AND business_hours IS NULL",
            (pref_name,),
        )
        stations_to_detail = cursor.fetchall()
        total_detail = len(stations_to_detail)
        logger.info(f"詳細未取得: {total_detail} 件")

        for i, row in enumerate(stations_to_detail, 1):
            station_id = row["id"]
            detail_url = row["url"]

            logger.info(f"  [{i}/{total_detail}] 詳細取得中: {station_id}")

            html = self.http.get(detail_url)
            if not html:
                continue

            station_info, chargers = parse_detail_page(html)

            if station_info:
                upsert_station(
                    conn,
                    {
                        "id": station_id,
                        "name": station_info.get("name", row["id"]),
                        "address": station_info.get("address", ""),
                        "prefecture": station_info.get("prefecture"),
                        "business_hours": station_info.get("business_hours"),
                        "closed_days": station_info.get("closed_days"),
                        "url": detail_url,
                    },
                )

            if chargers:
                insert_chargers(conn, station_id, chargers)

            conn.commit()
            self.stats["details_fetched"] += 1

            if i % 10 == 0:
                logger.info(f"  進捗: {i}/{total_detail} ({i * 100 // total_detail}%)")

        # Mark complete
        if not max_pages or page > total_pages:
            update_progress(
                conn, prefecture_code, page - 1, total_pages, completed=True
            )
            conn.commit()

        conn.close()
        logger.info(f"=== {pref_name} 完了 ===")
        self._print_stats()

    def scrape_all(
        self,
        max_pages_per_pref: Optional[int] = None,
        resume_only: bool = False,
        force_update: bool = False,
    ):
        """Scrape all prefectures"""
        init_db()
        conn = db_get_connection()

        for code in sorted(PREFECTURES.keys(), key=lambda x: int(x)):
            if resume_only and not force_update:
                progress = get_progress(conn, code)
                if progress and progress["completed"]:
                    continue
            try:
                self.scrape_prefecture(
                    code, max_pages=max_pages_per_pref, force_update=force_update
                )
            except Exception as e:
                logger.error(f"都道府県 {code} でエラー: {e}")
                continue

        conn.close()

    def _print_stats(self):
        """Print statistics"""
        logger.info("--- 統計 ---")
        logger.info(f"ページ数: {self.stats['pages_scraped']}")
        logger.info(f"スタンド: {self.stats['stations_found']}")
        logger.info(f"詳細: {self.stats['details_fetched']}")
        logger.info(f"エラー: {self.stats['errors']}")


def cmd_scrape(args):
    """Scrape command handler"""
    scraper = EVScraper(delay=args.delay)

    if args.prefecture:
        code = args.prefecture.zfill(2)
        if code not in PREFECTURES:
            code = args.prefecture
        if code not in PREFECTURES:
            print(f"エラー: 不明な都道府県コード '{args.prefecture}'")
            print(
                "有効なコード:",
                ", ".join(
                    f"{k}={v}"
                    for k, v in sorted(PREFECTURES.items(), key=lambda x: int(x[0]))
                ),
            )
            sys.exit(1)
        scraper.scrape_prefecture(code, max_pages=args.max_pages)
    else:
        scraper.scrape_all(max_pages_per_pref=args.max_pages, resume_only=args.resume)


def add_parser(subparsers):
    """Add scrape subparser"""
    parser = subparsers.add_parser("scrape", help="スクレイピング実行")
    parser.add_argument("-p", "--prefecture", type=str, help="都道府県コード (例: 13)")
    parser.add_argument(
        "-m", "--max-pages", type=int, default=None, help="最大ページ数"
    )
    parser.add_argument("-d", "--delay", type=float, default=2.0, help="リクエスト間隔")
    parser.add_argument("-r", "--resume", action="store_true", help="未完了のみ")
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細ログ")
    return parser
