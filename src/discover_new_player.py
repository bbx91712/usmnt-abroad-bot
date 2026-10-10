"""Search a player name across all configured top leagues to find candidates for tracking."""
from __future__ import annotations

import sys

from . import config
from .api_football import APIFootballClient


def _matches(short: str, api_player: dict) -> bool:
    full = (api_player.get("name") or "").lower()
    last = (api_player.get("lastname") or "").lower()
    return short.lower() in full or short.lower() == last


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m src.discover_new_player <short_name>")
        sys.exit(1)
    short_name = sys.argv[1]
    if len(short_name) < 3:
        print("Short name must be at least 3 characters.")
        sys.exit(1)

    season = config.competitions()["season"]
    competitions = config.competitions()["competitions"].values()
    top_leagues = {c["league_id"]: c for c in competitions if c.get("type") == "league"}
    client = APIFootballClient()

    found_any = False
    for league_id in sorted(top_leagues):
        league_name = top_leagues[league_id]["name"]
        results = client.get("players", search=short_name, league=league_id, season=season)
        league_matches = []
        for r in results:
            api_player = r.get("player", {})
            if not _matches(short_name, api_player):
                continue
            stats = r.get("statistics", [{}])[0]
            team = stats.get("team", {})
            league = stats.get("league", {})
            league_matches.append(
                f"  player_id={api_player.get('id')}  name={api_player.get('name')}  "
                f"team_id={team.get('id')}  team={team.get('name')}  "
                f"league_id={league.get('id')}  league={league.get('name')}"
            )

        if league_matches:
            found_any = True
            print(f"\n{league_name} (league {league_id}):")
            for row in league_matches[:5]:
                print(row)
            if len(league_matches) > 5:
                print(f"  ... and {len(league_matches) - 5} more")

    if not found_any:
        print(f"No matching players found for '{short_name}' in any tracked top league.")


if __name__ == "__main__":
    main()
