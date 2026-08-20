# config.py — Global project configuration
# !! Never commit your real API key. Use a .env file or environment variable instead.

import os

# HenrikDev API Key — get one at https://api.henrikdev.xyz/dashboard/api-keys
API_KEY = os.environ.get("HENRIKDEV_API_KEY", "HDEV-your-key-here")

# HenrikDev base URL
BASE_URL = "https://api.henrikdev.xyz"

# Region for API endpoints — options: eu, na, latam, br, ap, kr
REGION = "latam"

# Platform — options: pc, console
PLATFORM = "pc"

# Season filter
# e11a4 = Episode 11 Act 4 = V26 Act I (Season 2026 Act 1)
SEASON_SHORT = "e11a4"

# Scraping parameters
MATCH_COUNT = 20   # Matches to fetch per player (max 10 per API call, paginated)
MAX_PLAYERS = 100  # Max players to process from the leaderboard

# Database path
DB_PATH = "data/valorant.db"

# Active VALORANT maps
MAPS = [
    "Ascent", "Bind", "Breeze", "Fracture",
    "Haven", "Icebox", "Lotus", "Pearl",
    "Split", "Sunset", "Abyss"
]
