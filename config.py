"""
Flight deals configuration.
Edit destinations, thresholds, and preferences here.
"""

# Your home airports, in order of preference
HOME_AIRPORTS = ["DCA", "IAD", "BWI"]

# How many upcoming weekends to search (Fri→Sun and Fri→Mon combos)
WEEKENDS_AHEAD = 6

# Max price (round trip USD) to trigger a notification per category
PRICE_THRESHOLDS = {
    "domestic_cities": 200,
    "central_america": 300,
    "south_america": 450,
    "beaches": 350,
    "europe": 500,
}

# Destinations by category: (IATA code, display name)
DESTINATIONS = {
    "domestic_cities": [
        ("ORD", "Chicago"),
        ("MSY", "New Orleans"),
        ("BNA", "Nashville"),
        ("AUS", "Austin"),
        ("DEN", "Denver"),
        ("SFO", "San Francisco"),
        ("LAX", "Los Angeles"),
        ("MIA", "Miami"),
        ("SAN", "San Diego"),
        ("PDX", "Portland"),
        ("SEA", "Seattle"),
        ("SAV", "Savannah"),
        ("CHS", "Charleston"),
        ("SNA", "Orange County"),
        ("ATL", "Atlanta"),
        ("DTW", "Detroit"),
        ("FLL", "Fort Lauderdale"),
    ],
    "central_america": [
        ("CUN", "Cancun"),
        ("MEX", "Mexico City"),
        ("SJO", "San Jose, Costa Rica"),
        ("LIR", "Liberia, Costa Rica"),
        ("BZE", "Belize City"),
        ("GUA", "Guatemala City"),
        ("PTY", "Panama City"),
        ("PVR", "Puerto Vallarta"),
        ("SJD", "Cabo San Lucas"),
        ("GDL", "Guadalajara"),
    ],
    "south_america": [
        ("BOG", "Bogota"),
        ("MDE", "Medellin"),
        ("CTG", "Cartagena"),
        ("LIM", "Lima"),
        ("EZE", "Buenos Aires"),
        ("SCL", "Santiago"),
        ("GIG", "Rio de Janeiro"),
        ("GRU", "Sao Paulo"),
        ("UIO", "Quito"),
    ],
    "beaches": [
        ("CUN", "Cancun"),
        ("PUJ", "Punta Cana"),
        ("SJU", "San Juan"),
        ("HNL", "Honolulu"),
        ("PLS", "Turks & Caicos"),
        ("AUA", "Aruba"),
        ("STT", "St. Thomas"),
        ("NAS", "Nassau"),
        ("MBJ", "Montego Bay"),
        ("SXM", "St. Maarten"),
        ("GCM", "Grand Cayman"),
        ("SDQ", "Santo Domingo"),
    ],
    "europe": [
        ("LHR", "London"),
        ("CDG", "Paris"),
        ("FCO", "Rome"),
        ("BCN", "Barcelona"),
        ("LIS", "Lisbon"),
        ("AMS", "Amsterdam"),
        ("DUB", "Dublin"),
        ("MAD", "Madrid"),
        ("ATH", "Athens"),
        ("KEF", "Reykjavik"),
        ("BER", "Berlin"),
        ("PRG", "Prague"),
        ("CPH", "Copenhagen"),
        ("VCE", "Venice"),
        ("EDI", "Edinburgh"),
    ],
}

# Delay between API requests (seconds) to avoid rate limiting
REQUEST_DELAY_MIN = 2.0
REQUEST_DELAY_MAX = 5.0


def load_all_destinations() -> dict[str, list[tuple[str, str]]]:
    """Load hardcoded + custom destinations from custom_destinations.json."""
    import json
    import os

    merged = {cat: list(dests) for cat, dests in DESTINATIONS.items()}

    custom_file = os.path.join(os.path.dirname(__file__), "custom_destinations.json")
    try:
        with open(custom_file) as f:
            custom = json.load(f)
        for entry in custom.get("custom", []):
            code = entry["code"]
            name = entry["name"]
            cat = entry["category"]
            if cat not in merged:
                merged[cat] = []
            # Don't add duplicates
            if not any(c == code for c, _ in merged[cat]):
                merged[cat].append((code, name))
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass

    return merged
