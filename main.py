#!/usr/bin/env python3
"""
Flight Deals Finder
Searches Google Flights for cheap weekend trips.
- Logs all deals for the 5:30pm daily brief
- Only sends immediate Discord alerts for exceptional deals (20%+ below threshold)
"""

import sys
from dotenv import load_dotenv

load_dotenv()

from search import search_all
from notify import notify_deals
from deals_log import log_deals


def main():
    print("=" * 50)
    print("FLIGHT DEALS FINDER")
    print("=" * 50)

    deals = search_all()

    # Log ALL deals for the daily brief
    if deals:
        log_deals(deals)

    # Only send immediate alerts for exceptional deals — 20%+ below threshold
    great_deals = [d for d in deals if d.price <= d.threshold * 0.80]
    if great_deals:
        print(f"\n🔥 {len(great_deals)} exceptional deal(s) found — alerting now!")
        notify_deals(great_deals)
    else:
        print(f"\n{len(deals)} deals logged for daily brief, none exceptional enough for immediate alert.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
