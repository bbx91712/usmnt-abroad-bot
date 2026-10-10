"""Discover current clubs for every tracked player across configured top leagues."""
from __future__ import annotations

from . import config
from .api_football import APIFootballClient


def _matches(short: str, api_player: dict) -> bool:
    full = (api_player.get("name") or "").lower()
    last = (api_player.get("lastname") or "").lower()
    return short.lower() in full or short.lower() == last


def _format_row(player_id: int, name: str, team_id: int | None, team: str, league_id: int | None, league: str, current: bool = False) -> str:
    current_mark = "  <-- current" if current else ""
    return (
        f"    player_id={player_id}  name={name}  "
        f"team_id={team_id or '?'}  team={team or '?'}  "
        f"league_id={league_id or '?'}  league={league or '?'}{current_mark}"
    )


def main() -> None:
    season = config.competitions()["season"]
    competitions = config.competitions()["competitions"].values()
    top_leagues = {c["league_id"]: c for c in competitions if c.get("type") == "league"}
    client = APIFootballClient()

    for p in config.players():
        print(f"\n{p['name']} (short: {p['short_name']})")
        print(f"  Stored: player_id={p['player_id']}  club={p['club']}  league={p['league_name']}")
        found = False

        # Try the stored player_id first.
        data = client.get("players", id=p["player_id"], season=season)
        if data:
            api_player = data[0].get("player", {})
            if _matches(p["short_name"], api_player):
                for s in data[0].get("statistics", []):
                    league = s.get("league", {})
                    team = s.get("team", {})
                    if league.get("id") not in top_leagues:
                        continue
                    is_current = league.get("id") == p["league_id"] and team.get("id") == p["club_id"]
                    print(_format_row(
                        api_player.get("id"),
                        api_player.get("name"),
                        team.get("id"),
                        team.get("name"),
                        league.get("id"),
                        league.get("name"),
                        current=is_current,
                    ))
                    found = True

        if found:
            continue

        # Fall back to searching by short name in each top league.
        print("  Stored player_id did not return a match. Searching by short name in top leagues:")
        for league_id in sorted(top_leagues):
            results = client.get("players", search=p["short_name"], league=league_id, season=season)
            for r in results[:3]:
                api_player = r.get("player", {})
                if not _matches(p["short_name"], api_player):
                    continue
                stats = r.get("statistics", [{}])[0]
                team = stats.get("team", {})
                league = stats.get("league", {})
                is_current = league.get("id") == p["league_id"] and team.get("id") == p["club_id"]
                print(_format_row(
                    api_player.get("id"),
                    api_player.get("name"),
                    team.get("id"),
                    team.get("name"),
                    league.get("id"),
                    league.get("name"),
                    current=is_current,
                ))
                found = True

        if not found:
            print("  No results found.")


if __name__ == "__main__":
    main()
