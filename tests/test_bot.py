"""A few quick unit tests for ordering, broadcasters, and tweet formatting."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("MOCK_DATA", "1")

from src import broadcasters
from src import tweet_formatter
from src.api_football import APIFootballClient
from src.players import Player
from src.rankings import sort_players


def test_broadcasters_resolve():
    info = broadcasters.resolve("UCL")
    assert info["name"] == "Paramount+"
    assert info["paid"] is True


def test_tweet_formatter_goal():
    tweet = tweet_formatter.goal(
        player="Pulisic",
        club="AC Milan",
        opponent="Juventus",
        minute=23,
        score="1-0",
        competition="Serie A",
    )
    assert "GOAL!" in tweet
    assert "Pulisic" in tweet
    assert "AC Milan" in tweet


def test_player_ordering():
    client = APIFootballClient()
    players = [
        Player(
            name="Gio Reyna",
            short_name="Reyna",
            player_id=2,
            club_id=165,
            club="Borussia Dortmund",
            league_id=78,
            league_name="Bundesliga",
            country="Germany",
            uefa_assoc="Germany",
        ),
        Player(
            name="Chris Richards",
            short_name="Richards",
            player_id=3,
            club_id=52,
            club="Crystal Palace",
            league_id=39,
            league_name="Premier League",
            country="England",
            uefa_assoc="England",
        ),
        Player(
            name="Tyler Adams",
            short_name="Adams",
            player_id=4,
            club_id=49,
            club="AFC Bournemouth",
            league_id=39,
            league_name="Premier League",
            country="England",
            uefa_assoc="England",
        ),
    ]
    sorted_players = sort_players(client, players)
    assert sorted_players[0].uefa_assoc == "England"
    assert sorted_players[0].league_position < sorted_players[1].league_position
    assert sorted_players[2].uefa_assoc == "Germany"
