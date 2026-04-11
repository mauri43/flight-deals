"""
Persists deals across runs for daily briefing.
Each 4-hour run appends deals; the daily brief reads and resets.
"""

import json
import os
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), "deals_today.json")


def _load_log() -> list[dict]:
    try:
        with open(LOG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_log(entries: list[dict]):
    with open(LOG_FILE, "w") as f:
        json.dump(entries, f, indent=2)


def log_deals(deals) -> None:
    """Append deals from a search run to today's log."""
    existing = _load_log()

    # Deduplicate by origin+dest+dates — keep the cheapest price seen
    seen: dict[str, dict] = {}
    for entry in existing:
        key = f"{entry['origin']}|{entry['destination_code']}|{entry['depart_date']}|{entry['return_date']}"
        if key not in seen or entry["price"] < seen[key]["price"]:
            seen[key] = entry

    for deal in deals:
        key = f"{deal.origin}|{deal.destination_code}|{deal.depart_date}|{deal.return_date}"
        entry = {
            "origin": deal.origin,
            "destination_code": deal.destination_code,
            "destination_name": deal.destination_name,
            "category": deal.category,
            "depart_date": deal.depart_date,
            "return_date": deal.return_date,
            "price": deal.price,
            "threshold": deal.threshold,
            "airline": deal.airline,
            "stops": deal.stops,
            "flights_url": deal.flights_url,
            "found_at": datetime.utcnow().isoformat(),
        }
        # Keep if new or cheaper than what we've seen
        if key not in seen or deal.price < seen[key]["price"]:
            seen[key] = entry

    _save_log(list(seen.values()))
    print(f"  [log] {len(seen)} deals in today's log")


def get_top_deals(n: int = 3) -> list[dict]:
    """Get the top N deals from today's log, sorted by value (price vs threshold)."""
    entries = _load_log()
    if not entries:
        return []

    # Score by how far below threshold — biggest savings first
    def deal_score(e: dict) -> float:
        return e["price"] / max(e["threshold"], 1)

    entries.sort(key=deal_score)
    return entries[:n]


def reset_log() -> None:
    """Clear the daily log after sending the brief."""
    _save_log([])
    print("  [log] Reset daily log")
