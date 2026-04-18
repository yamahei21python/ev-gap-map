"""Reset command"""

from ..core.config import PREFECTURES
from ..db.models import init_db, delete_progress
from ..db.connection import get_connection


def cmd_reset(args):
    """Reset command handler"""
    init_db()
    conn = get_connection()

    if args.prefecture:
        code = args.prefecture.zfill(2)
        delete_progress(conn, code)
        print(
            f"都道府県 {code} ({PREFECTURES.get(code, '?')}) の進捗をリセットしました"
        )
    else:
        delete_progress(conn)
        print("全ての進捗をリセットしました")

    conn.commit()
    conn.close()


def add_parser(subparsers):
    """Add reset subparser"""
    parser = subparsers.add_parser("reset", help="進捗をリセット")
    parser.add_argument("-p", "--prefecture", type=str, help="都道府県コード")
    return parser
