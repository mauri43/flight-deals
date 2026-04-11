"""
Discord webhook notifications with rich embeds.
"""

import os
import httpx
from search import Deal, FlightLeg
from lodging import format_lodging_for_notification


DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")

CATEGORY_EMOJI = {
    "domestic_cities": "🏙️",
    "central_america": "🌮",
    "south_america": "🌎",
    "beaches": "🏖️",
    "europe": "✈️",
}

CATEGORY_COLOR = {
    "domestic_cities": 0xFF6B35,  # orange
    "central_america": 0x2ECC71,  # green
    "south_america": 0xE74C3C,   # red
    "beaches": 0x00BFFF,         # sky blue
    "europe": 0x9B59B6,          # purple
}


def _format_layover(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    if h and m:
        return f"{h}h{m:02d}m layover"
    elif h:
        return f"{h}h layover"
    return f"{m}m layover"


def _format_flight_field(deal: Deal) -> str:
    """Format the flight details including stops/layovers."""
    lines = []
    lines.append(f"**{deal.origin} → {deal.destination_code}** on {deal.airline}")
    lines.append(f"📅 {deal.depart_date} → {deal.return_date}")

    if deal.stops == 0:
        lines.append("✅ **Nonstop**")
    elif deal.legs:
        # Build "1 stop via MIA (1h32m layover)"
        layover_parts = []
        for leg in deal.legs[:-1]:
            part = leg.to_code
            if leg.layover_after_min > 0:
                part += f" ({_format_layover(leg.layover_after_min)})"
            layover_parts.append(part)
        stop_word = "stop" if deal.stops == 1 else "stops"
        lines.append(f"🔄 **{deal.stops} {stop_word}** via {', '.join(layover_parts)}")

        for i, leg in enumerate(deal.legs):
            dur_h = leg.duration_min // 60
            dur_m = leg.duration_min % 60
            dur_str = f"{dur_h}h{dur_m:02d}m" if dur_h else f"{dur_m}m"
            lines.append(f"` {leg.from_code}→{leg.to_code} ` {leg.depart_time}–{leg.arrive_time} ({dur_str})")

    return "\n".join(lines)


def _format_airbnb_pick(pick) -> dict:
    """Format one Airbnb pick as a Discord embed field."""
    l = pick.listing
    rating_str = f" {l.rating}" if l.rating else ""
    name_line = f"**{l.name}**"
    price_line = f"${l.per_night}/night · ${l.total_price:.0f} total"
    reason_line = f"*{pick.reason}*"

    value = f"{name_line}\n{price_line}{rating_str}\n{reason_line}"
    if l.url:
        value += f"\n[View listing →]({l.url})"

    label_emoji = {"Top Rated": "⭐", "Best Value": "💎", "Budget Pick": "💰"}.get(pick.label, "🏠")

    return {
        "name": f"{label_emoji} {pick.label}",
        "value": value,
        "inline": False,
    }


def _format_hotel_field(hotel) -> dict:
    """Format hotel deal as a Discord embed field."""
    deal_tag = f" 🔥 **{hotel.deal_pct}% off**" if hotel.deal_pct else ""
    value = (
        f"**{hotel.name}**{deal_tag}\n"
        f"${hotel.per_night}/night · ${hotel.total_price:.0f} total\n"
        f"*{hotel.reason}*"
    )
    return {
        "name": "🏨 Hotel Deal",
        "value": value,
        "inline": False,
    }


def build_embed(deal: Deal) -> dict:
    """Build a Discord embed for a deal."""
    emoji = CATEGORY_EMOJI.get(deal.category, "✈️")
    color = CATEGORY_COLOR.get(deal.category, 0x5865F2)
    cat_label = deal.category.replace("_", " ").title()

    fields = []

    # Flight info
    fields.append({
        "name": "✈️ Flight",
        "value": _format_flight_field(deal),
        "inline": False,
    })

    # Airbnb picks (3 options with reasoning)
    if deal.lodging and deal.lodging.picks:
        fields.append({
            "name": "─────────────────────────",
            "value": f"🏠 **Airbnb Options** ({deal.lodging.nights} nights in {deal.lodging.destination_vibe} area)",
            "inline": False,
        })
        for pick in deal.lodging.picks[:3]:
            fields.append(_format_airbnb_pick(pick))

        # Hotel deal — only shown if it beats Airbnb
        if deal.lodging.hotel:
            fields.append({
                "name": "─────────────────────────",
                "value": "👀 **This hotel beats the Airbnbs:**",
                "inline": False,
            })
            fields.append(_format_hotel_field(deal.lodging.hotel))

        # Estimated trip total: flight + (best lodging / 2) since housing is split
        best_lodging = deal.lodging.picks[0].listing
        budget_lodging = deal.lodging.picks[-1].listing
        # Use cheapest overall (could be hotel)
        cheapest_stay = budget_lodging.total_price
        if deal.lodging.hotel and deal.lodging.hotel.total_price < cheapest_stay:
            cheapest_stay = deal.lodging.hotel.total_price

        total_best = deal.price + best_lodging.total_price / 2
        total_budget = deal.price + cheapest_stay / 2

        if total_budget < total_best * 0.85:
            total_str = f"${total_budget:.0f} – ${total_best:.0f}"
        else:
            total_str = f"~${total_best:.0f}"

        fields.append({
            "name": "💵 Your Cost",
            "value": f"**{total_str}** (flight + your half of lodging)",
            "inline": False,
        })

        # Link to full Airbnb search
        fields.append({
            "name": "",
            "value": f"[🔍 See all Airbnbs →]({deal.lodging.airbnb_search_url})",
            "inline": False,
        })

    embed = {
        "title": f"{emoji} ${deal.price} Round Trip — {deal.destination_name}",
        "url": deal.flights_url,
        "color": color,
        "fields": fields,
        "footer": {
            "text": f"{cat_label} · Tap title to search flights on Google",
        },
    }

    return embed


def send_discord(embeds: list[dict]) -> bool:
    """Send embeds to Discord webhook."""
    if not DISCORD_WEBHOOK:
        print("  [discord] DISCORD_WEBHOOK not set, skipping")
        return False

    payload = {
        "username": "Flight Deals",
        "avatar_url": "https://em-content.zobj.net/source/apple/391/airplane_2708-fe0f.png",
        "embeds": embeds[:10],  # Discord max 10 embeds per message
    }

    try:
        resp = httpx.post(DISCORD_WEBHOOK, json=payload, timeout=10)
        resp.raise_for_status()
        print(f"  [discord] Sent {len(embeds)} embed(s)")
        return True
    except Exception as e:
        print(f"  [discord] Error: {e}")
        return False


def notify_deals(deals: list[Deal]):
    """Send Discord notifications for all deals found."""
    if not deals:
        print("\nNo deals found this run.")
        return

    best = sorted(deals, key=lambda x: x.price)

    print(f"\n=== Sending {min(len(best), 5)} deal notifications to Discord ===")

    for deal in best[:5]:
        embed = build_embed(deal)
        send_discord([embed])

    if len(best) > 5:
        summary_lines = []
        for d in best[5:15]:
            emoji = CATEGORY_EMOJI.get(d.category, "✈️")
            stops = " (nonstop)" if d.stops == 0 else f" ({d.stops} stop{'s' if d.stops != 1 else ''})"
            summary_lines.append(f"{emoji} **${d.price}** {d.origin}→{d.destination_name}{stops} ({d.depart_date})")

        summary_embed = {
            "title": f"📋 {len(best) - 5} More Deal{'s' if len(best) - 5 > 1 else ''}",
            "description": "\n".join(summary_lines),
            "color": 0x5865F2,
        }
        send_discord([summary_embed])
