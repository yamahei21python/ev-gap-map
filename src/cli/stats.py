"""Stats command"""

from ..db.models import init_db, get_stats
from ..db.connection import get_connection


def cmd_stats(args):
    """Stats command handler"""
    init_db()
    conn = get_connection()
    stats = get_stats(conn)
    conn.close()

    print(f"\n{'=' * 50}")
    print(f"EV充電スタンド データベース統計")
    print(f"{'=' * 50}")
    print(f"総スタンド数: {stats['total_stations']:,}")
    print(f"総充电器数:   {stats['total_chargers']:,}")

    if stats["by_type"]:
        print(f"\n--- 充電タイプ別 ---")
        for ctype, count in sorted(stats["by_type"].items()):
            print(f"  {ctype}: {count:,} 基")

    if stats["by_prefecture"]:
        print(f"\n--- 都道府県別 (上位10) ---")
        for pref, count in list(stats["by_prefecture"].items())[:10]:
            print(f"  {pref}: {count:,} 件")

    print()


def add_parser(subparsers):
    """Add stats subparser"""
    return subparsers.add_parser("stats", help="統計情報表示")
