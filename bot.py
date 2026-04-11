"""
Discord bot for managing flight deal destinations.
Slash commands:
  /add <code> [category] [name]  — add an airport to search
  /remove <code>                 — remove a custom airport
  /list                          — show all custom airports
  /categories                    — show available categories
"""

import os
import json
import discord
from discord import app_commands

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
CUSTOM_FILE = os.path.join(os.path.dirname(__file__), "custom_destinations.json")

CATEGORY_EMOJI = {
    "domestic_cities": "🏙️",
    "central_america": "🌮",
    "south_america": "🌎",
    "beaches": "🏖️",
    "europe": "✈️",
}

CATEGORY_CHOICES = [
    app_commands.Choice(name="🏙️ Domestic Cities ($200)", value="domestic_cities"),
    app_commands.Choice(name="🌮 Central America ($300)", value="central_america"),
    app_commands.Choice(name="🏖️ Beaches ($350)", value="beaches"),
    app_commands.Choice(name="🌎 South America ($450)", value="south_america"),
    app_commands.Choice(name="✈️ Europe ($500)", value="europe"),
]

# Known airport → (name, default category) for auto-detection
KNOWN_AIRPORTS = {
    # US
    "JFK": ("New York", "domestic_cities"), "LAX": ("Los Angeles", "domestic_cities"),
    "ORD": ("Chicago", "domestic_cities"), "SFO": ("San Francisco", "domestic_cities"),
    "MIA": ("Miami", "beaches"), "SEA": ("Seattle", "domestic_cities"),
    "DEN": ("Denver", "domestic_cities"), "ATL": ("Atlanta", "domestic_cities"),
    "BOS": ("Boston", "domestic_cities"), "MSY": ("New Orleans", "domestic_cities"),
    "AUS": ("Austin", "domestic_cities"), "SAN": ("San Diego", "domestic_cities"),
    "BNA": ("Nashville", "domestic_cities"), "PDX": ("Portland", "domestic_cities"),
    "SAV": ("Savannah", "domestic_cities"), "CHS": ("Charleston", "domestic_cities"),
    "HNL": ("Honolulu", "beaches"), "OGG": ("Maui", "beaches"),
    "LAS": ("Las Vegas", "domestic_cities"), "PHX": ("Phoenix", "domestic_cities"),
    "MSP": ("Minneapolis", "domestic_cities"), "DTW": ("Detroit", "domestic_cities"),
    "RDU": ("Raleigh", "domestic_cities"), "PIT": ("Pittsburgh", "domestic_cities"),
    "TPA": ("Tampa", "beaches"), "FLL": ("Fort Lauderdale", "beaches"),
    # Mexico / Central America
    "CUN": ("Cancun", "beaches"), "MEX": ("Mexico City", "central_america"),
    "SJO": ("San Jose, Costa Rica", "central_america"), "LIR": ("Liberia, Costa Rica", "central_america"),
    "BZE": ("Belize City", "central_america"), "GUA": ("Guatemala City", "central_america"),
    "PTY": ("Panama City", "central_america"), "PVR": ("Puerto Vallarta", "beaches"),
    "SJD": ("Cabo San Lucas", "beaches"), "GDL": ("Guadalajara", "central_america"),
    # Caribbean
    "SJU": ("San Juan", "beaches"), "PUJ": ("Punta Cana", "beaches"),
    "SDQ": ("Santo Domingo", "beaches"), "STI": ("Santiago, DR", "beaches"),
    "MBJ": ("Montego Bay", "beaches"), "NAS": ("Nassau", "beaches"),
    "AUA": ("Aruba", "beaches"), "STT": ("St. Thomas", "beaches"),
    "PLS": ("Turks & Caicos", "beaches"), "SXM": ("St. Maarten", "beaches"),
    "GCM": ("Grand Cayman", "beaches"),
    # South America
    "BOG": ("Bogota", "south_america"), "MDE": ("Medellin", "south_america"),
    "CTG": ("Cartagena", "south_america"), "LIM": ("Lima", "south_america"),
    "EZE": ("Buenos Aires", "south_america"), "SCL": ("Santiago", "south_america"),
    "GIG": ("Rio de Janeiro", "south_america"), "GRU": ("Sao Paulo", "south_america"),
    "UIO": ("Quito", "south_america"),
    # Europe
    "LHR": ("London", "europe"), "CDG": ("Paris", "europe"),
    "FCO": ("Rome", "europe"), "BCN": ("Barcelona", "europe"),
    "LIS": ("Lisbon", "europe"), "AMS": ("Amsterdam", "europe"),
    "DUB": ("Dublin", "europe"), "MAD": ("Madrid", "europe"),
    "ATH": ("Athens", "europe"), "KEF": ("Reykjavik", "europe"),
    "BER": ("Berlin", "europe"), "PRG": ("Prague", "europe"),
    "CPH": ("Copenhagen", "europe"), "VCE": ("Venice", "europe"),
    "EDI": ("Edinburgh", "europe"), "MUC": ("Munich", "europe"),
    "ZRH": ("Zurich", "europe"), "OSL": ("Oslo", "europe"),
    "HEL": ("Helsinki", "europe"), "BUD": ("Budapest", "europe"),
    "WAW": ("Warsaw", "europe"), "VIE": ("Vienna", "europe"),
    "MXP": ("Milan", "europe"), "FLR": ("Florence", "europe"),
    "NAP": ("Naples", "europe"), "OPO": ("Porto", "europe"),
    "DPS": ("Bali", "europe"), "NRT": ("Tokyo", "europe"),
    "HND": ("Tokyo Haneda", "europe"), "ICN": ("Seoul", "europe"),
}


def load_custom() -> dict:
    try:
        with open(CUSTOM_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"custom": []}


def save_custom(data: dict):
    with open(CUSTOM_FILE, "w") as f:
        json.dump(data, f, indent=2)


class DealBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()


bot = DealBot()


# ── /add — add a single airport ──────────────────────────────────────────

@bot.tree.command(name="add", description="Add an airport to search for deals")
@app_commands.describe(
    code="3-letter airport code (e.g. CUN, BCN, MEX)",
    category="Price threshold category (auto-detected for known airports)",
    name="Display name (auto-detected for known airports)",
)
@app_commands.choices(category=CATEGORY_CHOICES)
async def add_destination(
    interaction: discord.Interaction,
    code: str,
    category: str | None = None,
    name: str | None = None,
):
    code = code.upper().strip()
    if len(code) != 3 or not code.isalpha():
        await interaction.response.send_message("❌ Airport code must be 3 letters (e.g. CUN)", ephemeral=True)
        return

    data = load_custom()

    for dest in data["custom"]:
        if dest["code"] == code:
            await interaction.response.send_message(
                f"⚠️ **{code}** ({dest['name']}) is already added",
                ephemeral=True,
            )
            return

    # Auto-detect from known airports
    known = KNOWN_AIRPORTS.get(code)

    if not name:
        name = known[0] if known else code

    if not category:
        if known:
            category = known[1]
        else:
            # Unknown airport with no category — ask them to pick one
            await interaction.response.send_message(
                f"❓ I don't recognize **{code}** — please re-run with a category selected so I know the price threshold.\n"
                f"Example: `/add {code} category:Beaches`",
                ephemeral=True,
            )
            return

    data["custom"].append({
        "code": code,
        "name": name.strip(),
        "category": category,
    })
    save_custom(data)

    emoji = CATEGORY_EMOJI.get(category, "📌")
    await interaction.response.send_message(
        f"✅ Added **{name}** ({code}) — {emoji} {category.replace('_', ' ').title()} threshold\n"
        f"It'll be included in the next search run."
    )


# ── /remove — remove a custom airport ────────────────────────────────────

@bot.tree.command(name="remove", description="Remove a custom destination")
@app_commands.describe(code="3-letter airport code to remove")
async def remove_destination(interaction: discord.Interaction, code: str):
    code = code.upper().strip()
    data = load_custom()

    removed = None
    new_custom = []
    for d in data["custom"]:
        if d["code"] == code:
            removed = d
        else:
            new_custom.append(d)

    if not removed:
        await interaction.response.send_message(
            f"❌ **{code}** not found in custom destinations", ephemeral=True
        )
        return

    data["custom"] = new_custom
    save_custom(data)
    await interaction.response.send_message(f"🗑️ Removed **{removed['name']}** ({code})")


# ── /list — show custom airports ─────────────────────────────────────────

@bot.tree.command(name="list", description="Show all custom destinations you've added")
async def list_destinations(interaction: discord.Interaction):
    data = load_custom()

    if not data["custom"]:
        await interaction.response.send_message(
            "No custom destinations added yet.\n\n"
            "**Add an airport:** `/add MEX` — adds Mexico City\n"
            "**Unknown airport?** `/add SDQ category:Beaches` — you pick the threshold",
            ephemeral=True,
        )
        return

    lines = ["**Your Custom Destinations:**\n"
             "*These are searched on top of the built-in lists.*\n"]
    by_cat: dict[str, list] = {}
    for d in data["custom"]:
        by_cat.setdefault(d["category"], []).append(d)

    for cat, dests in by_cat.items():
        emoji = CATEGORY_EMOJI.get(cat, "📌")
        lines.append(f"{emoji} **{cat.replace('_', ' ').title()}**")
        for d in dests:
            lines.append(f"  `{d['code']}` — {d['name']}")
        lines.append("")

    await interaction.response.send_message("\n".join(lines))


# ── /categories — show thresholds ────────────────────────────────────────

@bot.tree.command(name="categories", description="Show categories and their price thresholds")
async def show_categories(interaction: discord.Interaction):
    msg = (
        "**Categories & Price Thresholds (round trip):**\n\n"
        "🏙️ **Domestic Cities** — alert under $200\n"
        "🌮 **Central America** — alert under $300\n"
        "🏖️ **Beaches** — alert under $350\n"
        "🌎 **South America** — alert under $450\n"
        "✈️ **Europe** — alert under $500\n\n"
        "*The category just sets the price threshold. When you `/add` a known airport, "
        "the category is auto-picked. For unknown airports, you choose.*"
    )
    await interaction.response.send_message(msg, ephemeral=True)


@bot.event
async def on_ready():
    print(f"Bot ready as {bot.user}")


if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)
