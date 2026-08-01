"""Order players by UEFA association rank, then domestic table position."""
from __future__ import annotations

from . import config, players as players_mod, standings
from .api_football import APIFootballClient
from .players import Player


def association_rank(association: str) -> int:
    data = config.uefa_rankings().get(association, {})
    return data.get("rank", 999)


def sort_players(client: APIFootballClient, player_list: list[Player] | None = None) -> list[Player]:
    if player_list is None:
        player_list = players_mod.load_players()
    for p in player_list:
        p.association_rank = association_rank(p.uefa_assoc)
        pos = standings.get_team_position(client, p.club_id, p.league_id)
        p.league_position = pos if pos is not None else 999
    return sorted(player_list, key=lambda p: (p.association_rank, p.league_position))
