"""Domestic table / standing helpers."""
from __future__ import annotations

from . import config
from .api_football import APIFootballClient


def _season() -> int:
    return config.competitions()["season"]


def get_table(client: APIFootballClient, league_id: int, season: int | None = None) -> list[dict]:
    season = season or _season()
    response = client.get("standings", league=league_id, season=season)
    if not response:
        return []
    league = response[0].get("league", {})
    groups = league.get("standings", [[]])
    return groups[0] if groups else []


def get_team_position(
    client: APIFootballClient, team_id: int, league_id: int, season: int | None = None
) -> int | None:
    table = get_table(client, league_id, season)
    for row in table:
        if row.get("team", {}).get("id") == team_id:
            return row.get("rank")
    return None
