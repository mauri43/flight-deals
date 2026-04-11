#!/usr/bin/env python3
"""
Daily brief — sends the top 3 deals found today to Discord at 5:30pm EST.
Triggered by a separate cron schedule.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import httpx
from deals_log import get_top_deals, reset_log

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")

CATEGORY_EMOJI = {
    "domestic_cities": "🏙️",
    "central_america": "🌮",
    "south_america": "🌎",
    "beaches": "🏖️",
    "europe": "✈️",
}

CATEGORY_COLOR = {
    "domestic_cities": 0xFF6B35,
    "central_america": 0x2ECC71,
    "south_america": 0xE74C3C,
    "beaches": 0x00BFFF,
    "europe": 0x9B59B6,
}


def build_brief_embed(deals: list[dict]) -> list[dict]:
    """Build Discord embeds for the daily brief."""
    today = datetime.now().strftime("%A, %B %-d")

    # Header embed
    header = {
        "title": f"📬 Daily Flight Brief — {today}",
        "description": f"Top {len(deals)} deal{'s' if len(deals) != 1 else ''} found today across all searches.",
        "color": 0x5865F2,
    }

    embeds = [header]

    for i, deal in enumerate(deals, 1):
        emoji = CATEGORY_EMOJI.get(deal["category"], "✈️")
        color = CATEGORY_COLOR.get(deal["category"], 0x5865F2)
        cat_label = deal["category"].replace("_", " ").title()

        savings_pct = int((1 - deal["price"] / deal["threshold"]) * 100)
        savings_str = f"**{savings_pct}% below** your ${deal['threshold']} threshold" if savings_pct > 0 else ""

        stops_str = "Nonstop" if deal["stops"] == 0 else f"{deal['stops']} stop{'s' if deal['stops'] != 1 else ''}"

        fields = [
            {
                "name": "✈️ Flight",
                "value": (
                    f"**{deal['origin']} → {deal['destination_code']}** on {deal['airline']}\n"
                    f"📅 {deal['depart_date']} → {deal['return_date']}\n"
                    f"🔄 {stops_str}"
                ),
                "inline": False,
            },
        ]

        if savings_str:
            fields.append({
                "name": "📉 Savings",
                "value": savings_str,
                "inline": False,
            })

        embed = {
            "title": f"#{i} {emoji} ${deal['price']} RT — {deal['destination_name']}",
            "url": deal["flights_url"],
            "color": color,
            "fields": fields,
            "footer": {"text": cat_label},
        }
        embeds.append(embed)

    return embeds


def send_brief():
    """Send the daily brief to Discord."""
    deals = get_top_deals(3)

    if not deals:
        print("No deals found today — skipping brief.")
        # Still send a message so user knows it ran
        payload = {
            "username": "Flight Deals",
            "avatar_url": "https://em-content.zobj.net/source/apple/391/airplane_2708-fe0f.png",
            "embeds": [{
                "title": "📬 Daily Flight Brief",
                "description": "No deals found below your thresholds today. Prices were high across the board — I'll keep looking.",
                "color": 0x95A5A6,
            }],
        }
        if DISCORD_WEBHOOK:
            httpx.post(DISCORD_WEBHOOK, json=payload, timeout=10)
        return

    print(f"Sending daily brief with {len(deals)} deals...")

    embeds = build_brief_embed(deals)

    if DISCORD_WEBHOOK:
        # Discord max 10 embeds per message — we'll have at most 4 (header + 3 deals)
        payload = {
            "username": "Flight Deals",
            "avatar_url": "https://em-content.zobj.net/source/apple/391/airplane_2708-fe0f.png",
            "embeds": embeds,
        }
        try:
            resp = httpx.post(DISCORD_WEBHOOK, json=payload, timeout=10)
            resp.raise_for_status()
            print(f"  [discord] Daily brief sent ({len(deals)} deals)")
        except Exception as e:
            print(f"  [discord] Error: {e}")

    reset_log()


if __name__ == "__main__":
    send_brief()
