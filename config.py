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
        ("JFK", "New York"),
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
        ("MSP", "Minneapolis"),
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
