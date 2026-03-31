"""メインスクレイピングロジック"""
import time
import random
import logging
import requests
from .config import SEARCH_URL, DETAIL_URL, BASE_URL, HEADERS, REQUEST_DELAY, REQUEST_TIMEOUT, MAX_RETRIES, PREFECTURES
from .parser import parse_search_page, parse_detail_page
from .models import get_connection, init_db, upsert_station, insert_chargers, update_progress, get_progress

logger = logging.getLogger(__name__)


class EVScraper:
    """EV充電スタンドスクレイパー"""

    def __init__(self, delay=REQUEST_DELAY):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.delay = delay
        self.stats = {"pages_scraped": 0, "stations_found": 0, "details_fetched": 0, "errors": 0}

    def _fetch(self, url, retries=MAX_RETRIES):
        """URLからHTMLを取得（リトライ・レートリミット対応）"""
        for attempt in range(retries):
            try:
                # ランダムな遅延でボット検知を回避
                jitter = random.uniform(0.5, 1.5)
                time.sleep(self.delay * jitter)
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)

                # HTTP 202 or 空レスポンス = レートリミット
                if response.status_code == 202 or len(response.text) < 100:
                    backoff = min(60, self.delay * (2 ** (attempt + 1)))
                    logger.warning(f"Rate limited (status={response.status_code}, len={len(response.text)}). "
                                   f"Backing off {backoff:.0f}s (attempt {attempt + 1}/{retries})")
                    time.sleep(backoff)
                    continue

                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {url} - {e}")
                if attempt < retries - 1:
                    backoff = min(60, self.delay * (2 ** (attempt + 1)))
                    time.sleep(backoff)
                else:
                    logger.error(f"All retries failed: {url}")
                    self.stats["errors"] += 1
                    return None
        logger.error(f"All retries exhausted (rate limit): {url}")
        self.stats["errors"] += 1
        return None

    def scrape_prefecture(self, prefecture_code, max_pages=None, force_update=False):
        """
        1つの都道府県のスタンド情報をスクレイピング

        Args:
            prefecture_code: 都道府県コード (例: "13")
            max_pages: 最大ページ数 (None で全ページ)
            force_update: 完了済みでも強制的にページ1から再スキャンするか
        """
        pref_name = PREFECTURES.get(prefecture_code, prefecture_code)
        logger.info(f"=== {pref_name} ({prefecture_code}) のスクレイピング開始 ===")

        init_db()
        conn = get_connection()

        # 進捗確認 - 前回の続きから
        progress = get_progress(conn, prefecture_code)
        start_page = 1
        
        if force_update:
            logger.info(f"強制アップデートモード(差分チェック): ページ 1 から再スキャンします")
        elif progress and not progress["completed"]:
            start_page = progress["last_page"] + 1
            logger.info(f"前回の続き: ページ {start_page} から再開")
        elif progress and progress["completed"]:
            logger.info(f"{pref_name} は既にスクレイピング完了済み。スキップします。")
            conn.close()
            return

        # フェーズ1: 検索ページを巡回してスタンドURLを収集 & 概要保存
        page = start_page
        total_pages = None

        while True:
            url = f"{SEARCH_URL}?ac={prefecture_code}&page={page}"
            logger.info(f"ページ {page} を取得中: {url}")

            html = self._fetch(url)
            if not html:
                logger.error(f"ページ {page} の取得に失敗。スキップします。")
                page += 1
                continue

            stations, detected_total = parse_search_page(html)

            if total_pages is None:
                total_pages = detected_total
                logger.info(f"総ページ数: {total_pages}")

            # 再開ページが既に最終ページを超えている場合のハンドリング
            if page > total_pages:
                logger.info(f"ページ {page} は既に範囲外です（総ページ数: {total_pages}）。検索を終了します。")
                break

            if not stations:
                # 栃木(9)などのデータがあるはずの県で、かつ範囲内のページで0件なのは異常
                if page <= total_pages:
                    logger.warning(f"ページ {page} にスタンドが見つかりませんが、総ページ数は {total_pages} です。")
                    logger.error(f"{pref_name} のデータが取得できないため、レートリミットの可能性があります。1分待機して中断します。")
                    time.sleep(60) 
                    conn.close()
                    return
                
                logger.info(f"ページ {page} にスタンドが見つかりません。終了します。")
                break


            # 各スタンションの概要を保存
            for station in stations:
                upsert_station(conn, {
                    "id": station["id"],
                    "name": station["name"],
                    "address": station["address"],
                    "prefecture": station["prefecture"],
                    "business_hours": None,
                    "closed_days": None,
                    "url": station["url"],
                })
                self.stats["stations_found"] += 1

            conn.commit()
            self.stats["pages_scraped"] += 1

            # 進捗更新
            update_progress(conn, prefecture_code, page, total_pages)
            conn.commit()

            logger.info(f"  → {len(stations)} 件のスタンドを保存 (累計: {self.stats['stations_found']})")

            # 次のページへ
            page += 1
            if max_pages and page > start_page + max_pages - 1:
                logger.info(f"最大ページ数 ({max_pages}) に達しました。")
                break
            if page > total_pages:
                break

        # フェーズ2: 各スタンドの詳細ページを取得
        logger.info(f"=== 詳細ページの取得開始 ===")
        cursor = conn.execute(
            "SELECT id, url FROM stations WHERE prefecture = ? AND business_hours IS NULL",
            (pref_name,)
        )
        stations_to_detail = cursor.fetchall()
        total_detail = len(stations_to_detail)
        logger.info(f"詳細未取得のスタンド: {total_detail} 件")

        for i, row in enumerate(stations_to_detail, 1):
            station_id = row["id"]
            detail_url = row["url"]

            logger.info(f"  [{i}/{total_detail}] 詳細取得中: {station_id}")

            html = self._fetch(detail_url)
            if not html:
                continue

            station_info, chargers = parse_detail_page(html)

            if station_info:
                # 詳細情報で更新
                update_data = {
                    "id": station_id,
                    "name": station_info.get("name", row["id"]),
                    "address": station_info.get("address", ""),
                    "prefecture": station_info.get("prefecture"),
                    "business_hours": station_info.get("business_hours"),
                    "closed_days": station_info.get("closed_days"),
                    "url": detail_url,
                }
                upsert_station(conn, update_data)

            if chargers:
                insert_chargers(conn, station_id, chargers)

            conn.commit()
            self.stats["details_fetched"] += 1

            if i % 10 == 0:
                logger.info(f"  進捗: {i}/{total_detail} ({i * 100 // total_detail}%)")

        # 完了マーク
        if not max_pages or page > total_pages:
            update_progress(conn, prefecture_code, page - 1, total_pages, completed=True)
            conn.commit()

        conn.close()
        logger.info(f"=== {pref_name} のスクレイピング完了 ===")
        self._print_stats()

    def scrape_all(self, max_pages_per_pref=None, resume_only=False, force_update=False):
        """全都道府県をスクレイピング
        
        Args:
            max_pages_per_pref: 各県の最大ページ数
            resume_only: True の場合、未完了の県のみ再実行
            force_update: True の場合、未・完了問わず強制的にページ1から指定ページ数だけ再走査
        """
        init_db()
        conn = get_connection()

        for code in sorted(PREFECTURES.keys(), key=lambda x: int(x)):
            if resume_only and not force_update:
                progress = get_progress(conn, code)
                if progress and progress["completed"]:
                    continue
            try:
                self.scrape_prefecture(code, max_pages=max_pages_per_pref, force_update=force_update)
            except Exception as e:
                logger.error(f"都道府県 {code} でエラー: {e}")
                continue

        conn.close()

    def _print_stats(self):
        """統計情報を表示"""
        logger.info(f"--- 統計 ---")
        logger.info(f"スクレイピング済みページ数: {self.stats['pages_scraped']}")
        logger.info(f"発見したスタンド数: {self.stats['stations_found']}")
        logger.info(f"詳細取得済みスタンド数: {self.stats['details_fetched']}")
        logger.info(f"エラー数: {self.stats['errors']}")
