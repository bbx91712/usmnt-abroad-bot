"""Player roster helpers."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import config


@dataclass
class Player:
    name: str
    short_name: str
    player_id: int
    club_id: int
    club: str
    league_id: int
    league_name: str
    country: str
    uefa_assoc: str
    association_rank: int = 999
    league_position: int = 999
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_config(cls, raw: dict) -> "Player":
        return cls(
            name=raw["name"],
            short_name=raw["short_name"],
            player_id=raw["player_id"],
            club_id=raw["club_id"],
            club=raw["club"],
            league_id=raw["league_id"],
            league_name=raw["league_name"],
            country=raw["country"],
            uefa_assoc=raw["uefa_assoc"],
            raw=raw,
        )


def load_players() -> list[Player]:
    return [Player.from_config(p) for p in config.players()]
