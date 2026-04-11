"""
Discord bot for managing flight deal destinations.
Slash commands:
  /add <code> <category> <name>  — add a destination
  /remove <code>                 — remove a destination
  /list                          — show all custom destinations
  /categories                    — show available categories
"""

import os
import json
import discord
from discord import app_commands

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
CUSTOM_FILE = os.path.join(os.path.dirname(__file__), "custom_destinations.json")

VALID_CATEGORIES = [
    "domestic_cities",
    "central_america",
    "south_america",
    "beaches",
    "europe",
]

CATEGORY_EMOJI = {
    "domestic_cities": "🏙️",
    "central_america": "🌮",
    "south_america": "🌎",
    "beaches": "🏖️",
    "europe": "✈️",
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


@bot.tree.command(name="add", description="Add a destination to search for deals")
@app_commands.describe(
    code="3-letter airport code (e.g. CUN, BCN, JFK)",
    category="Category for price thresholds",
    name="Display name (e.g. Cancun, Barcelona)",
)
@app_commands.choices(
    category=[
        app_commands.Choice(name="🏙️ Domestic Cities ($200 threshold)", value="domestic_cities"),
        app_commands.Choice(name="🌮 Central America ($300 threshold)", value="central_america"),
        app_commands.Choice(name="🌎 South America ($450 threshold)", value="south_america"),
        app_commands.Choice(name="🏖️ Beaches ($350 threshold)", value="beaches"),
        app_commands.Choice(name="✈️ Europe ($500 threshold)", value="europe"),
    ]
)
async def add_destination(interaction: discord.Interaction, code: str, category: str, name: str):
    code = code.upper().strip()
    if len(code) != 3 or not code.isalpha():
        await interaction.response.send_message("❌ Airport code must be 3 letters (e.g. CUN)", ephemeral=True)
        return

    data = load_custom()

    # Check if already exists
    for dest in data["custom"]:
        if dest["code"] == code:
            await interaction.response.send_message(
                f"⚠️ **{code}** ({dest['name']}) is already in your destinations under {dest['category']}",
                ephemeral=True,
            )
            return

    data["custom"].append({
        "code": code,
        "name": name.strip(),
        "category": category,
    })
    save_custom(data)

    emoji = CATEGORY_EMOJI.get(category, "✈️")
    await interaction.response.send_message(
        f"✅ Added **{name}** ({code}) to {emoji} {category.replace('_', ' ').title()}\n"
        f"It'll be included in the next search run."
    )


@bot.tree.command(name="remove", description="Remove a custom destination")
@app_commands.describe(code="3-letter airport code to remove")
async def remove_destination(interaction: discord.Interaction, code: str):
    code = code.upper().strip()
    data = load_custom()

    original_len = len(data["custom"])
    data["custom"] = [d for d in data["custom"] if d["code"] != code]

    if len(data["custom"]) == original_len:
        await interaction.response.send_message(
            f"❌ **{code}** not found in custom destinations", ephemeral=True
        )
        return

    save_custom(data)
    await interaction.response.send_message(f"🗑️ Removed **{code}** from custom destinations")


@bot.tree.command(name="list", description="Show all custom destinations")
async def list_destinations(interaction: discord.Interaction):
    data = load_custom()

    if not data["custom"]:
        await interaction.response.send_message(
            "No custom destinations added yet. Use `/add` to add some!",
            ephemeral=True,
        )
        return

    lines = ["**Custom Destinations:**\n"]
    by_cat: dict[str, list] = {}
    for d in data["custom"]:
        by_cat.setdefault(d["category"], []).append(d)

    for cat, dests in by_cat.items():
        emoji = CATEGORY_EMOJI.get(cat, "✈️")
        lines.append(f"{emoji} **{cat.replace('_', ' ').title()}**")
        for d in dests:
            lines.append(f"  `{d['code']}` — {d['name']}")
        lines.append("")

    await interaction.response.send_message("\n".join(lines))


@bot.tree.command(name="categories", description="Show available categories and their price thresholds")
async def show_categories(interaction: discord.Interaction):
    msg = (
        "**Categories & Thresholds (round trip):**\n\n"
        "🏙️ **Domestic Cities** — under $200\n"
        "🌮 **Central America** — under $300\n"
        "🏖️ **Beaches** — under $350\n"
        "🌎 **South America** — under $450\n"
        "✈️ **Europe** — under $500"
    )
    await interaction.response.send_message(msg, ephemeral=True)


@bot.event
async def on_ready():
    print(f"Bot ready as {bot.user}")


if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)
