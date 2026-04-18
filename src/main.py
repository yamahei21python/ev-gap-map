#!/usr/bin/env python3
"""EVCharge CLI - Main entry point"""

import argparse
import sys

from .core.logging import setup_logging
from .cli import scrape, stats, fetch_pop, geocode, gap_map, reset, update


def main():
    parser = argparse.ArgumentParser(
        description="EV charging station scraping & population analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape Tokyo (first page only)
  python main.py scrape --prefecture 13 --max-pages 1

  # Scrape all (resume)
  python main.py scrape --resume

  # Show stats
  python main.py stats

  # Fetch population data
  python main.py fetch-pop

  # Geocode addresses
  python main.py geocode

  # Generate gap map
  python main.py gap-map
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Register subparsers
    scrape.add_parser(subparsers)
    stats.add_parser(subparsers)
    fetch_pop.add_parser(subparsers)
    geocode.add_parser(subparsers)
    gap_map.add_parser(subparsers)
    reset.add_parser(subparsers)
    update.add_parser(subparsers)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Setup logging
    verbose = getattr(args, "verbose", False)
    setup_logging(verbose)

    # Dispatch
    if args.command == "scrape":
        scrape.cmd_scrape(args)
    elif args.command == "stats":
        stats.cmd_stats(args)
    elif args.command == "fetch-pop":
        fetch_pop.cmd_fetch_pop(args)
    elif args.command == "geocode":
        geocode.cmd_geocode(args)
    elif args.command == "gap-map":
        gap_map.cmd_gap_map(args)
    elif args.command == "reset":
        reset.cmd_reset(args)
    elif args.command == "update-stations":
        update.cmd_update(args)


if __name__ == "__main__":
    main()
