"""One-off helper to look up a player ID and current team by name in a league."""
from __future__ import annotations

import sys

from . import config
from .api_football import APIFootballClient


def _matches(short: str, api_player: dict) -> bool:
    full = (api_player.get("name") or "").lower()
    last = (api_player.get("lastname") or "").lower()
    return short.lower() in full or short.lower() == last


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python -m src.lookup_player <short_name> <league_id>")
        sys.exit(1)
    short_name = sys.argv[1]
    league_id = int(sys.argv[2])
    season = config.competitions()["season"]
    client = APIFootballClient()
    results = client.get("players", search=short_name, league=league_id, season=season)
    matches = [r for r in results if _matches(short_name, r.get("player", {}))]
    if not matches:
        print("No matching results found.")
        return
    print(f"Matches for '{short_name}' in league {league_id}:")
    for r in matches[:5]:
        p = r["player"]
        stats = r.get("statistics", [{}])[0]
        team = stats.get("team", {})
        league = stats.get("league", {})
        print(
            f"  player_id={p['id']}  name={p.get('name')}  "
            f"team_id={team.get('id')}  team={team.get('name')}  "
            f"league_id={league.get('id')}  league={league.get('name')}"
        )


if __name__ == "__main__":
    main()
