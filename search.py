"""
Flight search logic using fast-flights v3.
Generates weekend date pairs and queries Google Flights.
"""

import random
import time
from datetime import datetime, timedelta
from dataclasses import dataclass

from fast_flights import FlightQuery, Passengers, create_query, get_flights

from config import (
    HOME_AIRPORTS,
    PRICE_THRESHOLDS,
    WEEKENDS_AHEAD,
    REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX,
    load_all_destinations,
)
from lodging import LodgingResult, search_airbnb, format_lodging_for_notification


@dataclass
class FlightLeg:
    from_code: str
    to_code: str
    depart_time: str  # "2:30pm"
    arrive_time: str  # "5:26pm"
    duration_min: int
    plane: str
    layover_after_min: int = 0  # layover time before next leg


@dataclass
class Deal:
    origin: str
    destination_code: str
    destination_name: str
    category: str
    depart_date: str
    return_date: str
    price: int
    threshold: int
    airline: str
    flights_url: str
    stops: int = 0
    legs: list[FlightLeg] | None = None
    lodging: LodgingResult | None = None


@dataclass
class WeekendTrip:
    depart_date: str
    return_date: str
    label: str  # e.g. "Fri->Sun", "Thu->Mon"
    min_depart_hour: int | None = None  # e.g. 17 for "after 5pm"


def get_upcoming_trips(weeks: int = WEEKENDS_AHEAD) -> list[WeekendTrip]:
    """Return weekend trip combos: Fri->Sun, Fri->Mon, Thu eve->Sun, Thu eve->Mon."""
    today = datetime.now()
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0 and today.hour >= 12:
        days_until_friday = 7
    next_friday = today + timedelta(days=max(days_until_friday, 1))

    trips = []
    for i in range(weeks):
        friday = next_friday + timedelta(weeks=i)
        thursday = friday - timedelta(days=1)
        sunday = friday + timedelta(days=2)
        monday = friday + timedelta(days=3)

        thu = thursday.strftime("%Y-%m-%d")
        fri = friday.strftime("%Y-%m-%d")
        sun = sunday.strftime("%Y-%m-%d")
        mon = monday.strftime("%Y-%m-%d")

        trips.append(WeekendTrip(fri, sun, "Fri->Sun"))
        trips.append(WeekendTrip(fri, mon, "Fri->Mon"))
        trips.append(WeekendTrip(thu, sun, "Thu->Sun", min_depart_hour=17))
        trips.append(WeekendTrip(thu, mon, "Thu->Mon", min_depart_hour=17))

    return trips


def build_google_flights_url(origin: str, dest: str, depart: str, ret: str) -> str:
    """Build a clickable Google Flights URL."""
    return (
        f"https://www.google.com/travel/flights?"
        f"q=Flights+from+{origin}+to+{dest}+on+{depart}+returning+{ret}"
    )


def _format_time(t) -> str:
    """Format a SimpleDatetime time list like [14, 30] to '2:30pm'."""
    if not t or len(t) < 2:
        return "?"
    h, m = t[0], t[1]
    suffix = "am" if h < 12 else "pm"
    display_h = h % 12 or 12
    return f"{display_h}:{m:02d}{suffix}"


def _to_minutes(dt) -> int | None:
    """Convert a SimpleDatetime to total minutes since midnight on its date."""
    if not dt or not dt.time or len(dt.time) < 2 or not dt.date or len(dt.date) < 3:
        return None
    day_offset = dt.date[2] * 24 * 60  # day-of-month as rough offset for overnight
    return day_offset + dt.time[0] * 60 + dt.time[1]


def _extract_legs(flight) -> list[FlightLeg]:
    """Extract leg info from a fast-flights result, including layover durations."""
    raw_legs = flight.flights or []
    legs = []
    for i, leg in enumerate(raw_legs):
        layover = 0
        if i < len(raw_legs) - 1:
            arr = _to_minutes(leg.arrival)
            dep_next = _to_minutes(raw_legs[i + 1].departure)
            if arr is not None and dep_next is not None:
                layover = max(dep_next - arr, 0)

        legs.append(FlightLeg(
            from_code=leg.from_airport.code if leg.from_airport else "?",
            to_code=leg.to_airport.code if leg.to_airport else "?",
            depart_time=_format_time(leg.departure.time) if leg.departure else "?",
            arrive_time=_format_time(leg.arrival.time) if leg.arrival else "?",
            duration_min=leg.duration or 0,
            plane=leg.plane_type or "",
            layover_after_min=layover,
        ))
    return legs


@dataclass
class SearchResult:
    price: int
    airline: str
    stops: int
    legs: list[FlightLeg]


def search_route(
    origin: str, dest: str, depart: str, ret: str, min_depart_hour: int | None = None
) -> SearchResult | None:
    """Search a single round-trip route. Returns best result or None."""
    try:
        query = create_query(
            flights=[
                FlightQuery(date=depart, from_airport=origin, to_airport=dest),
                FlightQuery(date=ret, from_airport=dest, to_airport=origin),
            ],
            trip="round-trip",
            seat="economy",
            passengers=Passengers(adults=1),
            currency="USD",
        )
        results = get_flights(query)

        if results:
            best: SearchResult | None = None
            for flight in results:
                if not (flight.price and flight.price > 0):
                    continue
                # Filter by departure hour if required
                if min_depart_hour is not None and flight.flights:
                    outbound = flight.flights[0]
                    if outbound.departure and outbound.departure.time:
                        if outbound.departure.time[0] < min_depart_hour:
                            continue
                    else:
                        continue
                if best is None or flight.price < best.price:
                    legs = _extract_legs(flight)
                    best = SearchResult(
                        price=flight.price,
                        airline=", ".join(flight.airlines) if flight.airlines else "",
                        stops=max(len(legs) - 1, 0),
                        legs=legs,
                    )
            return best
    except Exception as e:
        print(f"  Error searching {origin}->{dest} ({depart}): {e}")
    return None


def search_all() -> list[Deal]:
    """Run all searches and return deals that beat the price threshold."""
    trips = get_upcoming_trips()
    deals: list[Deal] = []
    total_searches = 0
    errors = 0

    all_destinations = load_all_destinations()

    for category, destinations in all_destinations.items():
        threshold = PRICE_THRESHOLDS.get(category, 400)
        print(f"\n--- {category.upper()} (threshold: ${threshold}) ---")

        for dest_code, dest_name in destinations:
            for origin in HOME_AIRPORTS:
                if origin == dest_code:
                    continue

                for trip in trips:
                    total_searches += 1
                    print(
                        f"  {origin}->{dest_code} {trip.label} {trip.depart_date}...",
                        end=" ", flush=True,
                    )

                    result = search_route(
                        origin, dest_code,
                        trip.depart_date, trip.return_date,
                        min_depart_hour=trip.min_depart_hour,
                    )

                    if result is None:
                        print("no results")
                        errors += 1
                    elif result.price <= threshold:
                        stops_str = f" ({result.stops} stop{'s' if result.stops != 1 else ''})" if result.stops else " (nonstop)"
                        print(f"${result.price} ({result.airline}){stops_str} *** DEAL ***")
                        deals.append(Deal(
                            origin=origin,
                            destination_code=dest_code,
                            destination_name=dest_name,
                            category=category,
                            depart_date=trip.depart_date,
                            return_date=trip.return_date,
                            price=result.price,
                            threshold=threshold,
                            airline=result.airline,
                            stops=result.stops,
                            legs=result.legs,
                            flights_url=build_google_flights_url(
                                origin, dest_code,
                                trip.depart_date, trip.return_date,
                            ),
                        ))
                    else:
                        print(f"${result.price}")

                    # Rate limiting
                    delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
                    time.sleep(delay)

    print(f"\n=== Done: {total_searches} searches, {len(deals)} deals, {errors} errors ===")

    # Enrich deals with lodging data — deduplicate by destination+dates
    if deals:
        print(f"\n=== Fetching Airbnb data for {len(deals)} deals ===")
        lodging_cache: dict[str, LodgingResult | None] = {}
        for deal in deals:
            cache_key = f"{deal.destination_code}|{deal.depart_date}|{deal.return_date}"
            if cache_key not in lodging_cache:
                print(f"  Airbnb: {deal.destination_name} ({deal.depart_date} to {deal.return_date})...", flush=True)
                lodging_cache[cache_key] = search_airbnb(
                    deal.destination_code, deal.depart_date, deal.return_date,
                )
                time.sleep(random.uniform(2.0, 4.0))
            deal.lodging = lodging_cache[cache_key]

    return deals
