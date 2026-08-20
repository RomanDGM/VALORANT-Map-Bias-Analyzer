# main.py — CLI entry point for the VALORANT Map Bias Analyzer

import argparse
from database import init_db
from scraper import scrape_player, scrape_leaderboard
from analysis import run_full_analysis
from dashboard import generate_all


def main():
    parser = argparse.ArgumentParser(
        description="VALORANT Map Bias Analyzer",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "--leaderboard", action="store_true",
        help="Automatically scrape matches from the top N ranked players"
    )
    parser.add_argument(
        "--top", type=int, default=100, metavar="N",
        help="Number of leaderboard players to process (default: 100)"
    )
    parser.add_argument(
        "--matches", type=int, default=20, metavar="N",
        help="Matches to fetch per player (default: 20)"
    )
    parser.add_argument(
        "--scrape", nargs=2, metavar=("GAME_NAME", "TAG"),
        help="Scrape a specific player. Example: --scrape TenZ 1001"
    )
    parser.add_argument(
        "--analyze", action="store_true",
        help="Run statistical analysis on stored data"
    )
    parser.add_argument(
        "--dashboard", action="store_true",
        help="Generate visualization charts"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Run leaderboard scrape + analysis + dashboard in one go"
    )

    args = parser.parse_args()

    # Always initialize the DB on startup
    init_db()

    # ── Scraping ──────────────────────────────────────
    if args.leaderboard or args.all:
        scrape_leaderboard(top_n=args.top, matches_per_player=args.matches)

    elif args.scrape:
        game_name, tag = args.scrape
        print(f"\n[Scraper] Processing player: {game_name}#{tag}")
        stored = scrape_player(game_name, tag, count=args.matches)
        print(f"[Scraper] {stored} matches stored.")

    # ── Analysis + Dashboard ──────────────────────────
    if args.analyze or args.all:
        results = run_full_analysis()
        if args.dashboard or args.all:
            generate_all(results)

    elif args.dashboard:
        results = run_full_analysis()
        generate_all(results)

    # ── No arguments: show help ────────────────────────
    if not any([args.leaderboard, args.scrape, args.analyze, args.dashboard, args.all]):
        parser.print_help()


if __name__ == "__main__":
    main()
