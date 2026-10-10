"""Fixture / result helpers."""
from __future__ import annotations

from datetime import datetime, timezone

import pytz

from . import config
from .api_football import APIFootballClient


def _season() -> int:
    return config.competitions()["season"]


def _fetch(client: APIFootballClient, team_id: int, league_id: int, which: str, season: int | None) -> list[dict]:
    season = season or _season()
    kwargs = {which: 1}
    return client.get("fixtures", team=team_id, league=league_id, season=season, **kwargs)


def get_last(client: APIFootballClient, team_id: int, league_id: int, season: int | None = None) -> dict | None:
    fixtures = _fetch(client, team_id, league_id, "last", season)
    return fixtures[0] if fixtures else None


def get_next(client: APIFootballClient, team_id: int, league_id: int, season: int | None = None) -> dict | None:
    fixtures = _fetch(client, team_id, league_id, "next", season)
    return fixtures[0] if fixtures else None


def get_live(client: APIFootballClient, **params) -> list[dict]:
    return client.get("fixtures", live="all", **params)


def get_events(client: APIFootballClient, fixture_id: int) -> list[dict]:
    return client.get("fixtures/events", fixture=fixture_id)


def get_lineups(client: APIFootballClient, fixture_id: int) -> list[dict]:
    return client.get("fixtures/lineups", fixture=fixture_id)


def player_fixture_stats(client: APIFootballClient, player_id: int, fixture_id: int, league_id: int, season: int | None = None) -> dict:
    season = season or _season()
    data = client.get("players", id=player_id, fixture=fixture_id, league=league_id, season=season)
    return data[0] if data else {}


def opponent_name(fixture: dict, team_id: int) -> str:
    if fixture["teams"]["home"]["id"] == team_id:
        return fixture["teams"]["away"]["name"]
    return fixture["teams"]["home"]["name"]


def result_for_team(fixture: dict, team_id: int) -> str:
    goals = fixture.get("goals", {})
    home_goals = goals.get("home", 0)
    away_goals = goals.get("away", 0)
    home_id = fixture["teams"]["home"]["id"]
    if home_id == team_id:
        gf, ga = home_goals, away_goals
    else:
        gf, ga = away_goals, home_goals
    if gf > ga:
        outcome = "W"
    elif gf < ga:
        outcome = "L"
    else:
        outcome = "D"
    return f"{gf}-{ga} ({outcome})"


def format_date_utc(date_str: str) -> str:
    ts = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    return ts.strftime("%Y-%m-%d %H:%M UTC")


def format_date_et(date_str: str) -> str:
    ts = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    et = ts.astimezone(pytz.timezone("US/Eastern"))
    return et.strftime("%a %b %d, %I:%M %p ET")


def status_short(fixture: dict) -> str:
    return fixture.get("fixture", {}).get("status", {}).get("short", "?")


def cup_status(
    client: APIFootballClient, team_id: int, league_id: int, season: int | None = None
) -> str | None:
    """Return a knockout-cup status (e.g., 'Advanced to Round 4') for a team."""
    season = season or _season()
    last = get_last(client, team_id, league_id, season)
    next_ = get_next(client, team_id, league_id, season)
    if not last and not next_:
        return "No fixture scheduled"
    if last:
        last_round = last.get("league", {}).get("round", "this round")
        home_id = last["teams"]["home"]["id"]
        winner = last["teams"]["home"]["winner"] if home_id == team_id else last["teams"]["away"]["winner"]
        if winner is True:
            if next_:
                next_round = next_.get("league", {}).get("round", "the next round")
                return f"Advanced to {next_round}"
            return f"Won {last_round}"
        if winner is False:
            return f"Eliminated in {last_round}"
        return f"Draw in {last_round}"
    if next_:
        next_round = next_.get("league", {}).get("round", "the next round")
        return f"Upcoming {next_round}"
    return None
