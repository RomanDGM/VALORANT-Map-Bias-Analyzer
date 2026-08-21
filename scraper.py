# HenrikDev API scraper (v4)
# API docs: https://docs.henrikdev.xyz/valorant/api-reference

import requests
import time
import urllib.parse
from config import API_KEY, BASE_URL, REGION, PLATFORM, MATCH_COUNT, SEASON_SHORT
from database import insert_match, insert_team_result, match_exists

HEADERS = {
    "Authorization": API_KEY,
    "Accept": "application/json",
}

# Free-tier rate limit: 30 req/min → 1 request every 2s to stay safe
RATE_LIMIT_DELAY = 2.0


def _get(url, params=None):
    """GET request with automatic rate-limit handling and error reporting."""
    time.sleep(RATE_LIMIT_DELAY)
    response = requests.get(url, headers=HEADERS, params=params)

    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 15))
        print(f"[Rate limit] Waiting {retry_after}s...")
        time.sleep(retry_after)
        return _get(url, params)

    if response.status_code == 404:
        print(f"[404] Not found: {url}")
        return None

    if response.status_code != 200:
        print(f"[Error {response.status_code}] {url} — {response.text[:200]}")
        return None

    data = response.json()
    # HenrikDev wraps responses in {"status": 200, "data": {...}}
    return data.get("data", data)


# ─────────────────────────────────────────────
# LEADERBOARD
# ─────────────────────────────────────────────

def get_leaderboard(top_n=100):
    """
    GET /valorant/v3/leaderboard/{region}/{platform}
    Returns the top_n ranked players for the configured season.
    """
    url = f"{BASE_URL}/valorant/v3/leaderboard/{REGION}/{PLATFORM}"
    print(f"[Leaderboard] Fetching top {top_n} players — region: {REGION.upper()} | season: {SEASON_SHORT}...")

    raw = _get(url, params={"season_short": SEASON_SHORT})
    if not raw:
        print("[Leaderboard] Failed to fetch leaderboard.")
        return []

    players = raw.get("players", [])

    result = []
    for entry in players[:top_n]:
        name = entry.get("name", "")
        tag  = entry.get("tag", "")
        rank = entry.get("leaderboard_rank", "?")

        # Skip anonymous or nameless entries
        if not name or not tag or entry.get("is_anonymized"):
            continue

        result.append({"name": name, "tag": tag, "rank": rank})

    print(f"[Leaderboard] {len(result)} players found.")
    return result


# ─────────────────────────────────────────────
# MATCH HISTORY
# ─────────────────────────────────────────────

def get_match_history(game_name, tag_line, size=10, start=0):
    """
    GET /valorant/v4/matches/{region}/{platform}/{name}/{tag}
    Returns competitive match history for a player, filtered to SEASON_SHORT.
    """
    name_enc = urllib.parse.quote(game_name, safe="")
    tag_enc  = urllib.parse.quote(tag_line,  safe="")
    url = f"{BASE_URL}/valorant/v4/matches/{REGION}/{PLATFORM}/{name_enc}/{tag_enc}"
    params = {
        "mode":         "competitive",
        "size":         min(size, 10),
        "start":        start,
        "season_short": SEASON_SHORT,
    }
    data = _get(url, params=params)
    if data is None:
        return []
    return data if isinstance(data, list) else data.get("matches", [])


def get_match_detail(match_id):
    """
    GET /valorant/v4/match/{region}/{matchid}
    Returns full match details for a given match ID.
    """
    url = f"{BASE_URL}/valorant/v4/match/{REGION}/{match_id}"
    return _get(url)


# ─────────────────────────────────────────────
# PARSING & STORAGE
# ─────────────────────────────────────────────

def parse_and_store_match(match_data):
    """
    Extracts relevant fields from a v4 match object and writes to the DB.
    Discards matches that do not belong to SEASON_SHORT.
    """
    if not match_data:
        return

    meta        = match_data.get("metadata", {})
    match_id    = meta.get("match_id") or meta.get("matchid")
    map_raw     = meta.get("map", {})
    map_name    = map_raw.get("name", "Unknown") if isinstance(map_raw, dict) else str(map_raw)
    game_start  = meta.get("started_at", 0)
    game_length = meta.get("game_length", 0)
    queue_raw   = meta.get("queue", {})
    queue_id    = queue_raw.get("id", "") if isinstance(queue_raw, dict) else str(queue_raw)

    # Season guard — discard matches from other seasons
    season_raw   = meta.get("season", {})
    season_short = season_raw.get("short", "") if isinstance(season_raw, dict) else ""
    if season_short and season_short != SEASON_SHORT:
        print(f"  [skip] {match_id} — season {season_short!r} (expected {SEASON_SHORT!r})")
        return

    if not match_id:
        return

    if match_exists(match_id):
        print(f"  [skip] {match_id} already in DB.")
        return

    insert_match(match_id, map_name, game_start, game_length, queue_id)

    teams_data = match_data.get("teams", {})
    team_map = {}

    if isinstance(teams_data, dict):
        for color, team_info in teams_data.items():
            if isinstance(team_info, dict):
                team_map[color] = team_info
    elif isinstance(teams_data, list):
        for team in teams_data:
            color = (team.get("team_id") or team.get("teamId", "")).lower()
            team_map[color] = team

    for team_id, team_info in team_map.items():
        won         = 1 if team_info.get("won", False) else 0
        rounds_info = team_info.get("rounds", {})
        if isinstance(rounds_info, dict):
            rounds_won  = rounds_info.get("won", 0)
            rounds_lost = rounds_info.get("lost", 0)
        else:
            rounds_won  = team_info.get("rounds_won", 0)
            rounds_lost = team_info.get("rounds_lost", 0)

        # VALORANT convention: "red" team always starts as attacker
        starting_side = "attacker" if team_id.lower() == "red" else "defender"

        insert_team_result(match_id, team_id, starting_side, rounds_won, rounds_lost, won)

    print(f"  [✓] {match_id} — {map_name}")


# ─────────────────────────────────────────────
# PLAYER PIPELINE
# ─────────────────────────────────────────────

def scrape_player(game_name, tag_line, count=MATCH_COUNT):
    """Fetches and stores competitive matches for a single player."""
    stored = 0
    start  = 0

    while stored < count:
        to_fetch = min(10, count - stored)
        matches  = get_match_history(game_name, tag_line, size=to_fetch, start=start)

        if not matches:
            break

        for match_summary in matches:
            mid = (
                match_summary.get("metadata", {}).get("match_id")
                or match_summary.get("metadata", {}).get("matchid")
                or match_summary.get("match_id")
            )
            if not mid:
                continue

            if "teams" in match_summary and "metadata" in match_summary:
                parse_and_store_match(match_summary)
            else:
                detail = get_match_detail(mid)
                parse_and_store_match(detail)

            stored += 1

        start += len(matches)
        if len(matches) < to_fetch:
            break

    return stored


# ─────────────────────────────────────────────
# FULL LEADERBOARD PIPELINE
# ─────────────────────────────────────────────

def scrape_leaderboard(top_n=100, matches_per_player=MATCH_COUNT):
    """
    Fetches the top_n leaderboard players and scrapes their matches
    sequentially, printing progress after each player.
    """
    players = get_leaderboard(top_n)
    if not players:
        print("[Error] Could not fetch leaderboard. Check your API key and region.")
        return

    total         = len(players)
    total_matches = 0

    print(f"\n{'='*55}")
    print(f"  Starting scrape: {total} players")
    print(f"  Matches per player: {matches_per_player}")
    print(f"{'='*55}\n")

    for i, player in enumerate(players, start=1):
        name = player["name"]
        tag  = player["tag"]
        rank = player["rank"]

        print(f"[{i:>3}/{total}] #{rank} — {name}#{tag}")

        stored = scrape_player(name, tag, count=matches_per_player)
        total_matches += stored

        print(f"        → {stored} matches stored | {total - i} players remaining\n")

    print(f"{'='*55}")
    print(f"  Scraping complete.")
    print(f"  Players processed : {total}")
    print(f"  Matches stored    : {total_matches}")
    print(f"{'='*55}\n")
