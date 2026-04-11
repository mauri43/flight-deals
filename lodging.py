"""
Lodging search: Airbnb (direct scrape) + Amadeus hotels.
Searches for accommodation near destinations when a flight deal is found.
"""

import base64
import json
import os
import re
from dataclasses import dataclass

from curl_cffi import requests as cffi_requests

# Destination search configs: where to search for lodging near each airport
# Tuned for the best neighborhoods — walkable, safe, tourist-friendly
DESTINATION_SEARCH = {
    # Domestic cities
    "JFK": {"query": "Manhattan, New York", "vibe": "city"},
    "ORD": {"query": "River North, Chicago", "vibe": "city"},
    "MSY": {"query": "French Quarter, New Orleans", "vibe": "city"},
    "BNA": {"query": "Downtown Nashville, Tennessee", "vibe": "city"},
    "AUS": {"query": "Downtown Austin, Texas", "vibe": "city"},
    "DEN": {"query": "LoDo, Denver, Colorado", "vibe": "city"},
    "SFO": {"query": "Mission District, San Francisco", "vibe": "city"},
    "LAX": {"query": "Santa Monica, Los Angeles", "vibe": "beach"},
    "MIA": {"query": "South Beach, Miami", "vibe": "beach"},
    "SAN": {"query": "Gaslamp Quarter, San Diego", "vibe": "city"},
    "PDX": {"query": "Pearl District, Portland, Oregon", "vibe": "city"},
    "SEA": {"query": "Capitol Hill, Seattle", "vibe": "city"},
    "SAV": {"query": "Historic District, Savannah, Georgia", "vibe": "city"},
    "CHS": {"query": "Downtown Charleston, South Carolina", "vibe": "city"},
    "SNA": {"query": "Huntington Beach, California", "vibe": "beach"},
    "ATL": {"query": "Midtown Atlanta, Georgia", "vibe": "city"},
    "DTW": {"query": "Downtown Detroit, Michigan", "vibe": "city"},
    "MSP": {"query": "North Loop, Minneapolis", "vibe": "city"},
    # Central America
    "CUN": {"query": "Zona Hotelera, Cancun, Mexico", "vibe": "beach"},
    "MEX": {"query": "Roma Norte, Mexico City", "vibe": "city"},
    "SJO": {"query": "Manuel Antonio, Costa Rica", "vibe": "beach"},
    "LIR": {"query": "Tamarindo, Costa Rica", "vibe": "beach"},
    "BZE": {"query": "San Pedro, Ambergris Caye, Belize", "vibe": "beach"},
    "GUA": {"query": "Antigua Guatemala", "vibe": "city"},
    "PTY": {"query": "Casco Viejo, Panama City", "vibe": "city"},
    "PVR": {"query": "Zona Romantica, Puerto Vallarta", "vibe": "beach"},
    "SJD": {"query": "Medano Beach, Cabo San Lucas", "vibe": "beach"},
    "GDL": {"query": "Centro Historico, Guadalajara", "vibe": "city"},
    # South America
    "BOG": {"query": "Chapinero, Bogota, Colombia", "vibe": "city"},
    "MDE": {"query": "El Poblado, Medellin, Colombia", "vibe": "city"},
    "CTG": {"query": "Old Town, Cartagena, Colombia", "vibe": "beach"},
    "LIM": {"query": "Miraflores, Lima, Peru", "vibe": "city"},
    "EZE": {"query": "Palermo Soho, Buenos Aires", "vibe": "city"},
    "SCL": {"query": "Providencia, Santiago, Chile", "vibe": "city"},
    "GIG": {"query": "Copacabana, Rio de Janeiro", "vibe": "beach"},
    "GRU": {"query": "Vila Madalena, Sao Paulo", "vibe": "city"},
    "UIO": {"query": "La Mariscal, Quito, Ecuador", "vibe": "city"},
    # Beaches
    "PUJ": {"query": "Bavaro, Punta Cana, Dominican Republic", "vibe": "beach"},
    "SJU": {"query": "Condado, San Juan, Puerto Rico", "vibe": "beach"},
    "HNL": {"query": "Waikiki, Honolulu, Hawaii", "vibe": "beach"},
    "PLS": {"query": "Grace Bay, Turks and Caicos", "vibe": "beach"},
    "AUA": {"query": "Palm Beach, Aruba", "vibe": "beach"},
    "STT": {"query": "Red Hook, St Thomas, US Virgin Islands", "vibe": "beach"},
    "NAS": {"query": "Cable Beach, Nassau, Bahamas", "vibe": "beach"},
    "MBJ": {"query": "Montego Bay, Jamaica", "vibe": "beach"},
    "SXM": {"query": "Philipsburg, St Maarten", "vibe": "beach"},
    "GCM": {"query": "Seven Mile Beach, Grand Cayman", "vibe": "beach"},
    # Europe
    "LHR": {"query": "Shoreditch, London", "vibe": "city"},
    "CDG": {"query": "Le Marais, Paris", "vibe": "city"},
    "FCO": {"query": "Trastevere, Rome", "vibe": "city"},
    "BCN": {"query": "El Born, Barcelona", "vibe": "city"},
    "LIS": {"query": "Alfama, Lisbon", "vibe": "city"},
    "AMS": {"query": "Jordaan, Amsterdam", "vibe": "city"},
    "DUB": {"query": "Temple Bar, Dublin", "vibe": "city"},
    "MAD": {"query": "Malasana, Madrid", "vibe": "city"},
    "ATH": {"query": "Plaka, Athens", "vibe": "city"},
    "KEF": {"query": "Downtown Reykjavik, Iceland", "vibe": "city"},
    "BER": {"query": "Mitte, Berlin", "vibe": "city"},
    "PRG": {"query": "Old Town, Prague", "vibe": "city"},
    "CPH": {"query": "Norrebro, Copenhagen", "vibe": "city"},
    "VCE": {"query": "Dorsoduro, Venice", "vibe": "city"},
    "EDI": {"query": "Old Town, Edinburgh", "vibe": "city"},
}


@dataclass
class AirbnbListing:
    name: str
    total_price: float
    per_night: float
    nights: int
    rating: str
    url: str
    badge: str  # e.g. "Guest favorite"


@dataclass
class AirbnbPick:
    listing: AirbnbListing
    label: str     # "Top Rated", "Best Value", "Budget Pick"
    reason: str    # why this one


@dataclass
class LodgingResult:
    airbnb_listings: list[AirbnbListing]
    picks: list[AirbnbPick]  # 3 curated picks with reasoning
    airbnb_search_url: str
    nights: int
    destination_vibe: str


def _parse_price(price_str: str) -> float | None:
    """Extract numeric price from '$746.00' or '$1,200'."""
    match = re.search(r"[\d,]+(?:\.\d+)?", price_str.replace(",", ""))
    return float(match.group()) if match else None


def search_airbnb(
    dest_code: str,
    checkin: str,
    checkout: str,
    adults: int = 2,
    price_max: int = 250,
) -> LodgingResult | None:
    """Search Airbnb for listings near a destination. Returns top options sorted by value."""
    dest_info = DESTINATION_SEARCH.get(dest_code)
    if not dest_info:
        return None

    query = dest_info["query"]
    vibe = dest_info["vibe"]

    # Build Airbnb search URL
    search_url = f"https://www.airbnb.com/s/{query.replace(' ', '-').replace(',', '')}/homes"
    params = {
        "checkin": checkin,
        "checkout": checkout,
        "adults": str(adults),
        "price_max": str(price_max),
    }

    try:
        r = cffi_requests.get(
            search_url,
            params=params,
            headers={},
            impersonate="chrome124",
            timeout=15,
        )
        if r.status_code != 200:
            print(f"  [airbnb] HTTP {r.status_code} for {dest_code}")
            return None

        # Extract deferred state JSON
        deferred = re.search(
            r'<script[^>]*id="data-deferred-state-0"[^>]*>(.*?)</script>',
            r.text,
            re.DOTALL,
        )
        if not deferred:
            print(f"  [airbnb] No deferred state for {dest_code}")
            return None

        data = json.loads(deferred.group(1))

        # Navigate to searchResults
        search_results = _find_nested(data, "searchResults")
        if not search_results:
            print(f"  [airbnb] No searchResults for {dest_code}")
            return None

        # Calculate nights
        from datetime import datetime
        d1 = datetime.strptime(checkin, "%Y-%m-%d")
        d2 = datetime.strptime(checkout, "%Y-%m-%d")
        nights = (d2 - d1).days

        listings = []
        for item in search_results:
            if not isinstance(item, dict):
                continue

            name = item.get("title", "") or item.get("nameLocalized", "")
            rating = item.get("avgRatingLocalized", "")

            # Extract listing ID from base64-encoded demandStayListing.id
            property_id = ""
            dsl = item.get("demandStayListing") or {}
            encoded_id = dsl.get("id", "")
            if encoded_id:
                try:
                    decoded = base64.b64decode(encoded_id).decode()
                    property_id = decoded.split(":")[-1]
                except Exception:
                    pass

            # Parse price
            price_data = item.get("structuredDisplayPrice") or {}
            primary = price_data.get("primaryLine") or {}
            total_str = (
                primary.get("discountedPrice")
                or primary.get("price")
                or ""
            )
            total_price = _parse_price(total_str) if total_str else None

            # Fallback: parse from accessibilityLabel
            if total_price is None:
                label = primary.get("accessibilityLabel", "")
                price_match = re.search(r"\$[\d,]+(?:\.\d+)?", label)
                if price_match:
                    total_price = _parse_price(price_match.group())

            if total_price is None or total_price <= 0:
                continue

            per_night = total_price / max(nights, 1)

            # Check for badges
            badge = ""
            for b in item.get("badges") or []:
                if isinstance(b, dict):
                    badge = b.get("text", "")
                    break

            listing_url = f"https://www.airbnb.com/rooms/{property_id}?checkin={checkin}&checkout={checkout}&adults={adults}" if property_id else ""

            listings.append(AirbnbListing(
                name=name[:80],
                total_price=total_price,
                per_night=round(per_night),
                nights=nights,
                rating=rating,
                url=listing_url,
                badge=badge,
            ))

        # Sort by value: prioritize high-rated listings, then cheapest
        # Rating >= 4.8 with Guest Favorite badge > high rating > cheap
        def value_score(l: AirbnbListing) -> float:
            score = l.total_price
            if l.badge:
                score *= 0.85  # boost badged listings
            if l.rating:
                try:
                    r = float(l.rating.split("(")[0].strip())
                    if r >= 4.9:
                        score *= 0.80
                    elif r >= 4.7:
                        score *= 0.90
                except ValueError:
                    pass
            return score

        listings.sort(key=value_score)

        # Build the full search URL for the notification link
        full_url = search_url + "?" + "&".join(f"{k}={v}" for k, v in params.items())

        # Select 3 curated picks with reasoning
        picks = _select_picks(listings, vibe)

        return LodgingResult(
            airbnb_listings=listings[:10],
            picks=picks,
            airbnb_search_url=full_url,
            nights=nights,
            destination_vibe=vibe,
        )

    except Exception as e:
        print(f"  [airbnb] Error for {dest_code}: {e}")
        return None


def _rating_num(listing: AirbnbListing) -> float:
    """Extract numeric rating from '4.96 (50)' format."""
    if not listing.rating:
        return 0.0
    try:
        return float(listing.rating.split("(")[0].strip())
    except ValueError:
        return 0.0


def _review_count(listing: AirbnbListing) -> int:
    """Extract review count from '4.96 (50)' format."""
    match = re.search(r"\((\d+)\)", listing.rating or "")
    return int(match.group(1)) if match else 0


def _select_picks(listings: list[AirbnbListing], vibe: str) -> list[AirbnbPick]:
    """Select 3 picks: Top Rated, Best Value, Budget Pick — each with reasoning."""
    if not listings:
        return []

    picks: list[AirbnbPick] = []
    used: set[int] = set()  # track by index to avoid dedup issues with empty URLs

    # 1. TOP RATED — highest rating with meaningful review count
    rated = [
        (i, l) for i, l in enumerate(listings) if _review_count(l) >= 10
    ]
    rated.sort(key=lambda x: (-_rating_num(x[1]), -_review_count(x[1])))
    if not rated:
        rated = [(i, l) for i, l in enumerate(listings)]
        rated.sort(key=lambda x: -_rating_num(x[1]))

    if rated:
        idx, top = rated[0]
        r = _rating_num(top)
        reviews = _review_count(top)
        badge_note = f", {top.badge}" if top.badge else ""
        reason = f"{r}★ across {reviews} reviews{badge_note} — highest rated in the area"
        picks.append(AirbnbPick(listing=top, label="Top Rated", reason=reason))
        used.add(idx)

    # 2. BEST VALUE — best rating-to-price ratio (not already picked)
    def value_ratio(l: AirbnbListing) -> float:
        r = _rating_num(l)
        if r == 0 or l.total_price <= 0:
            return 0
        return (r * _review_count(l) ** 0.3) / l.total_price

    remaining = [(i, l) for i, l in enumerate(listings) if i not in used]
    remaining.sort(key=lambda x: -value_ratio(x[1]))

    if remaining:
        idx, val = remaining[0]
        r = _rating_num(val)
        reason = f"{r}★ at ${val.per_night}/night — strong reviews at a great price"
        if val.badge:
            reason += f" ({val.badge})"
        picks.append(AirbnbPick(listing=val, label="Best Value", reason=reason))
        used.add(idx)

    # 3. BUDGET PICK — cheapest remaining with decent rating (>= 4.0)
    budget = [(i, l) for i, l in enumerate(listings) if i not in used and _rating_num(l) >= 4.0]
    budget.sort(key=lambda x: x[1].total_price)
    if not budget:
        budget = [(i, l) for i, l in enumerate(listings) if i not in used]
        budget.sort(key=lambda x: x[1].total_price)

    if budget:
        idx, bud = budget[0]
        r = _rating_num(bud)
        savings = ""
        if picks and picks[0].listing.total_price > 0:
            pct = int((1 - bud.total_price / picks[0].listing.total_price) * 100)
            if pct > 10:
                savings = f", {pct}% less than top pick"
        reason = f"Cheapest at ${bud.per_night}/night"
        if r >= 4.5:
            reason += f", still a solid {r}★"
        elif r > 0:
            reason += f" ({r}★)"
        reason += savings
        picks.append(AirbnbPick(listing=bud, label="Budget Pick", reason=reason))

    return picks


def _find_nested(d, target, depth=0):
    """Recursively find a key in nested dict/list."""
    if depth > 10:
        return None
    if isinstance(d, dict):
        if target in d:
            return d[target]
        for v in d.values():
            result = _find_nested(v, target, depth + 1)
            if result is not None:
                return result
    elif isinstance(d, list):
        for item in d:
            result = _find_nested(item, target, depth + 1)
            if result is not None:
                return result
    return None


def format_lodging_for_notification(lodging: LodgingResult | None) -> str:
    """Format lodging results as a compact string for push notifications."""
    if not lodging or not lodging.airbnb_listings:
        return ""

    lines = []
    best = lodging.airbnb_listings[0]
    cheapest = min(lodging.airbnb_listings, key=lambda l: l.total_price)

    # Show the best value pick
    badge_str = f" [{best.badge}]" if best.badge else ""
    rating_str = f" {best.rating}" if best.rating else ""
    lines.append(
        f"\n🏠 Top Airbnb: ${best.per_night}/night (${best.total_price:.0f} total)"
        f"{rating_str}{badge_str}"
    )
    lines.append(f"   {best.name}")

    # If cheapest is different from best, show it too
    if cheapest.total_price < best.total_price * 0.85:
        lines.append(
            f"💰 Budget: ${cheapest.per_night}/night (${cheapest.total_price:.0f} total)"
        )

    # Price range summary
    prices = [l.total_price for l in lodging.airbnb_listings]
    if len(prices) >= 3:
        lines.append(f"   Range: ${min(prices):.0f}-${max(prices):.0f} for {lodging.nights} nights")

    return "\n".join(lines)
