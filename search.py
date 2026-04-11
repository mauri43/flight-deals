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
    DESTINATIONS,
    PRICE_THRESHOLDS,
    WEEKENDS_AHEAD,
    REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX,
)


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


def search_route(
    origin: str, dest: str, depart: str, ret: str, min_depart_hour: int | None = None
) -> tuple[int | None, str]:
    """Search a single round-trip route. Returns (cheapest_price, airline) or (None, '').
    If min_depart_hour is set, only considers flights departing at or after that hour."""
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
            best_price = None
            best_airline = ""
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
                        continue  # skip if no time info
                if best_price is None or flight.price < best_price:
                    best_price = flight.price
                    best_airline = ", ".join(flight.airlines) if flight.airlines else ""
            return best_price, best_airline
    except Exception as e:
        print(f"  Error searching {origin}->{dest} ({depart}): {e}")
    return None, ""


def search_all() -> list[Deal]:
    """Run all searches and return deals that beat the price threshold."""
    trips = get_upcoming_trips()
    deals: list[Deal] = []
    total_searches = 0
    errors = 0

    for category, destinations in DESTINATIONS.items():
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

                    price, airline = search_route(
                        origin, dest_code,
                        trip.depart_date, trip.return_date,
                        min_depart_hour=trip.min_depart_hour,
                    )

                    if price is None:
                        print("no results")
                        errors += 1
                    elif price <= threshold:
                        print(f"${price} ({airline}) *** DEAL ***")
                        deals.append(Deal(
                            origin=origin,
                            destination_code=dest_code,
                            destination_name=dest_name,
                            category=category,
                            depart_date=trip.depart_date,
                            return_date=trip.return_date,
                            price=price,
                            threshold=threshold,
                            airline=airline,
                            flights_url=build_google_flights_url(
                                origin, dest_code,
                                trip.depart_date, trip.return_date,
                            ),
                        ))
                    else:
                        print(f"${price}")

                    # Rate limiting
                    delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
                    time.sleep(delay)

    print(f"\n=== Done: {total_searches} searches, {len(deals)} deals, {errors} errors ===")
    return deals
