"""
Notification via ntfy.sh (free push notifications).
Install the ntfy app on your phone and subscribe to your topic.

iOS: https://apps.apple.com/app/ntfy/id1625396347
Android: https://play.google.com/store/apps/details?id=io.heckel.ntfy
"""

import os
import httpx
from search import Deal
from lodging import format_lodging_for_notification


NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
NTFY_TOKEN = os.environ.get("NTFY_TOKEN", "")
NTFY_BASE = "https://ntfy.sh"

CATEGORY_EMOJI = {
    "domestic_cities": "🏙️",
    "central_america": "🌮",
    "south_america": "🌎",
    "beaches": "🏖️",
    "europe": "✈️",
}


def _estimate_total(deal: Deal) -> str:
    """Estimate total trip cost: flights + lodging."""
    if not deal.lodging or not deal.lodging.airbnb_listings:
        return ""
    best_lodging = deal.lodging.airbnb_listings[0]
    total_low = deal.price + best_lodging.total_price
    cheapest = min(deal.lodging.airbnb_listings, key=lambda l: l.total_price)
    total_budget = deal.price + cheapest.total_price
    if total_budget < total_low * 0.9:
        return f"\n\n💵 Est. trip total: ${total_budget:.0f}-${total_low:.0f}"
    return f"\n\n💵 Est. trip total: ~${total_low:.0f}"


def format_deal(deal: Deal) -> tuple[str, str]:
    """Return (title, body) for a deal notification."""
    emoji = CATEGORY_EMOJI.get(deal.category, "✈️")
    cat_label = deal.category.replace("_", " ").title()

    title = f"{emoji} ${deal.price} RT — {deal.destination_name}"

    body = (
        f"{deal.origin} → {deal.destination_code} ({cat_label})\n"
        f"{deal.depart_date} → {deal.return_date}\n"
        f"${deal.price} round trip on {deal.airline}"
    )

    # Add lodging info
    lodging_text = format_lodging_for_notification(deal.lodging)
    if lodging_text:
        body += f"\n{lodging_text}"

    # Add estimated trip total
    body += _estimate_total(deal)

    return title, body


def send_ntfy(title: str, body: str, url: str = "") -> bool:
    """Send a push notification via ntfy.sh."""
    if not NTFY_TOPIC:
        print("  [ntfy] NTFY_TOPIC not set, skipping")
        return False

    headers = {"Title": title, "Priority": "high", "Tags": "airplane"}
    if url:
        headers["Click"] = url
    if NTFY_TOKEN:
        headers["Authorization"] = f"Bearer {NTFY_TOKEN}"

    try:
        resp = httpx.post(
            f"{NTFY_BASE}/{NTFY_TOPIC}",
            content=body,
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        print(f"  [ntfy] Sent: {title}")
        return True
    except Exception as e:
        print(f"  [ntfy] Error: {e}")
        return False


def send_summary(deals: list[Deal]) -> bool:
    """Send a summary notification when multiple deals are found."""
    if not deals:
        return False

    title = f"🔥 {len(deals)} flight deal{'s' if len(deals) > 1 else ''} found!"
    lines = []
    for d in sorted(deals, key=lambda x: x.price):
        emoji = CATEGORY_EMOJI.get(d.category, "✈️")
        lodging_hint = ""
        if d.lodging and d.lodging.airbnb_listings:
            best = d.lodging.airbnb_listings[0]
            lodging_hint = f" + ~${best.per_night}/n Airbnb"
        lines.append(
            f"{emoji} ${d.price} {d.origin}→{d.destination_name} ({d.depart_date}){lodging_hint}"
        )

    body = "\n".join(lines[:15])
    if len(deals) > 15:
        body += f"\n...and {len(deals) - 15} more"

    return send_ntfy(title, body)


def notify_deals(deals: list[Deal]):
    """Send notifications for all deals found."""
    if not deals:
        print("\nNo deals found this run.")
        return

    print(f"\n=== Sending {len(deals)} notifications ===")

    # Send individual notifications for the best deals (top 5 by price)
    best = sorted(deals, key=lambda x: x.price)[:5]
    for deal in best:
        title, body = format_deal(deal)
        send_ntfy(title, body, url=deal.flights_url)

    # If there are more than 5, also send a summary
    if len(deals) > 5:
        send_summary(deals)
