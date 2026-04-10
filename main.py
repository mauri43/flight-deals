#!/usr/bin/env python3
"""
Flight Deals Finder
Searches Google Flights for cheap weekend trips and sends push notifications.
"""

import sys
from dotenv import load_dotenv

load_dotenv()

from search import search_all
from notify import notify_deals


def main():
    print("=" * 50)
    print("FLIGHT DEALS FINDER")
    print("=" * 50)

    deals = search_all()
    notify_deals(deals)

    # Exit with code 0 even if no deals — that's normal
    # Exit with code 1 only on unrecoverable errors
    return 0


if __name__ == "__main__":
    sys.exit(main())
