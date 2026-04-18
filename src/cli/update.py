"""Update stations command"""

import logging
from typing import Optional

from ..core.logging import get_logger
from .scrape import EVScraper


logger = get_logger(__name__)


def cmd_update(args):
    """Update stations command handler"""
    scraper = EVScraper(delay=2.0)
    logging.info(
        f"=== 差分アップデート開始 (各都道府県上位 {args.pages} ページをチェック) ==="
    )
    scraper.scrape_all(
        max_pages_per_pref=args.pages, resume_only=False, force_update=True
    )
    logging.info("=== 差分アップデート完了 ===")


def add_parser(subparsers):
    """Add update-stations subparser"""
    parser = subparsers.add_parser("update-stations", help="DBの差分アップデート")
    parser.add_argument(
        "--pages", type=int, default=3, help="各都道府県でチェックするページ数"
    )
    return parser
