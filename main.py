#!/usr/bin/env python3
"""EV充電スタンド スクレイピング - CLIエントリポイント"""
import argparse
import logging
import sys

from scraper.scraper import EVScraper
from scraper.models import init_db, get_connection, get_stats
from scraper.config import PREFECTURES


def setup_logging(verbose=False):
    """ロギング設定"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_scrape(args):
    """スクレイピング実行"""
    scraper = EVScraper(delay=args.delay)

    if args.prefecture:
        code = args.prefecture.zfill(2)
        if code not in PREFECTURES:
            # Try without zero-padding
            code = args.prefecture
        if code not in PREFECTURES:
            print(f"エラー: 不明な都道府県コード '{args.prefecture}'")
            print("有効なコード:", ", ".join(f"{k}={v}" for k, v in sorted(PREFECTURES.items(), key=lambda x: int(x[0]))))
            sys.exit(1)
        scraper.scrape_prefecture(code, max_pages=args.max_pages)
    else:
        scraper.scrape_all(max_pages_per_pref=args.max_pages, resume_only=args.resume)


def cmd_stats(args):
    """統計情報表示"""
    init_db()
    conn = get_connection()
    stats = get_stats(conn)
    conn.close()

    print(f"\n{'='*50}")
    print(f"EV充電スタンド データベース統計")
    print(f"{'='*50}")
    print(f"総スタンド数: {stats['total_stations']:,}")
    print(f"総充電器数:   {stats['total_chargers']:,}")

    if stats["by_type"]:
        print(f"\n--- 充電タイプ別 ---")
        for ctype, count in sorted(stats["by_type"].items()):
            print(f"  {ctype}: {count:,} 基")

    if stats["by_prefecture"]:
        print(f"\n--- 都道府県別 (上位10) ---")
        for pref, count in list(stats["by_prefecture"].items())[:10]:
            print(f"  {pref}: {count:,} 件")

    print()


def cmd_reset(args):
    """進捗リセット"""
    init_db()
    conn = get_connection()
    if args.prefecture:
        code = args.prefecture.zfill(2)
        conn.execute("DELETE FROM scrape_progress WHERE prefecture_code = ?", (code,))
        print(f"都道府県 {code} ({PREFECTURES.get(code, '?')}) の進捗をリセットしました。")
    else:
        conn.execute("DELETE FROM scrape_progress")
        print("全ての進捗をリセットしました。")
    conn.commit()
    conn.close()


def cmd_fetch_pop(args):
    """人口データ取得実行"""
    from population.fetcher import PopulationFetcher
    import os
    
    fetcher = PopulationFetcher()
    db_path = None
    if args.test_db:
        db_path = os.path.join(os.path.dirname(__file__), "data", "test_population.db")
        print(f"Using test DB: {db_path}")

    if args.geojson_only:
        fetcher.export_geojson(db_path=db_path)
    else:
        fetcher.fetch_all(db_path=db_path)


def cmd_geocode(args):
    """ジオコーディング実行"""
    from scraper.models import get_connection
    from scraper.geocoder import batch_geocode
    
    conn = get_connection()
    try:
        batch_geocode(conn)
    finally:
        conn.close()


def cmd_gap_map(args):
    """ギャップマップ生成実行"""
    from population.gap_analysis import run_gap_analysis
    run_gap_analysis()


def cmd_update(args):
    """DBの差分アップデート（各都道府県の最新3ページだけをチェックし、新着を追加・更新する）"""
    from scraper.scraper import EVScraper
    logging.info(f"=== 差分アップデート開始 (各都道府県上位 {args.pages} ページをチェック) ===")
    scraper = EVScraper(delay=2.0)
    scraper.scrape_all(max_pages_per_pref=args.pages, resume_only=False, force_update=True)
    logging.info("=== 差分アップデート完了 ===")


def main():
    parser = argparse.ArgumentParser(
        description="EV充電スタンド スクレイピング＆人口データツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 東京都の最初の1ページだけテスト
  python main.py scrape --prefecture 13 --max-pages 1

  # 全都道府県スクレイピング（再開）
  python main.py scrape --resume

  # 統計情報を表示
  python main.py stats

  # 人口メッシュデータを取得して保存＆GeoJSON出力
  python main.py fetch-pop

  # テスト用DBに人口データを取得・保存
  python main.py fetch-pop --test-db

  # 既存DBからGeoJSONのみ再出力
  python main.py fetch-pop --geojson-only

  # スタンドの住所から緯度経度を算出（ジオコーディング）
  python main.py geocode
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="コマンド")

    # scrape コマンド
    sp_scrape = subparsers.add_parser("scrape", help="スクレイピング実行")
    sp_scrape.add_argument("-p", "--prefecture", type=str, help="都道府県コード (例: 13=東京都)")
    sp_scrape.add_argument("-m", "--max-pages", type=int, default=None, help="最大ページ数")
    sp_scrape.add_argument("-d", "--delay", type=float, default=2.0, help="リクエスト間隔(秒)")
    sp_scrape.add_argument("-r", "--resume", action="store_true", help="未完了の県のみ再実行")
    sp_scrape.add_argument("-v", "--verbose", action="store_true", help="詳細ログ")

    # stats コマンド
    sp_stats = subparsers.add_parser("stats", help="統計情報表示")

    # fetch-pop コマンド
    sp_fetch_pop = subparsers.add_parser("fetch-pop", help="人口データ取得")
    sp_fetch_pop.add_argument("--geojson-only", action="store_true", help="API取得をスキップし、DBからGeoJSON出力のみ行う")
    sp_fetch_pop.add_argument("--test-db", action="store_true", help="本番DBではなくテスト用DB(test_population.db)を使用する")

    # geocode コマンド
    sp_geocode = subparsers.add_parser("geocode", help="住所から緯度経度を算出（国土地理院APIを使用）")

    # gap-map コマンド
    sp_gap_map = subparsers.add_parser("gap-map", help="ギャップ分析を実行し、gap_map.geojsonを作成")

    # update-stations コマンド
    parser_update = subparsers.add_parser("update-stations", help="DBの差分アップデート（各都道府県の最新3ページだけをチェックし、新着を追加・更新する）")
    parser_update.add_argument("--pages", type=int, default=3, help="各都道府県でチェックするページ数 (デフォルト: 3)")

    # reset コマンド
    sp_reset = subparsers.add_parser("reset", help="進捗をリセット")
    sp_reset.add_argument("-p", "--prefecture", type=str, help="都道府県コード")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    setup_logging(getattr(args, "verbose", False))

    if args.command == "scrape":
        cmd_scrape(args)
    elif args.command == "update-stations":
        cmd_update(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "fetch-pop":
        cmd_fetch_pop(args)
    elif args.command == "geocode":
        cmd_geocode(args)
    elif args.command == "gap-map":
        cmd_gap_map(args)
    elif args.command == "reset":
        cmd_reset(args)


if __name__ == "__main__":
    main()
