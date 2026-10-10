"""Fixture / result helpers."""
from __future__ import annotations

from datetime import datetime, timezone

import pytz

from . import config
from .api_football import APIFootballClient


def _season() -> int:
    return config.competitions()["season"]


def _fetch_all(client: APIFootballClient, team_id: int, league_id: int, season: int | None = None) -> list[dict]:
    season = season or _season()
    return client.get("fixtures", team=team_id, league=league_id, season=season)


def _status_short(fixture: dict) -> str:
    return fixture.get("fixture", {}).get("status", {}).get("short", "")


def get_last_next(
    client: APIFootballClient, team_id: int, league_id: int, season: int | None = None
) -> tuple[dict | None, dict | None]:
    """Return the most recent finished and the next scheduled fixture for a team in a competition."""
    fixtures = _fetch_all(client, team_id, league_id, season)
    finished = [f for f in fixtures if _status_short(f) in ("FT", "AET", "PEN")]
    finished.sort(key=lambda f: f["fixture"]["date"], reverse=True)
    last = finished[0] if finished else None
    upcoming = [
        f for f in fixtures
        if _status_short(f) in ("NS", "TBD") and f.get("fixture", {}).get("date")
    ]
    upcoming.sort(key=lambda f: f["fixture"]["date"])
    next_ = upcoming[0] if upcoming else None
    return last, next_


def get_last(client: APIFootballClient, team_id: int, league_id: int, season: int | None = None) -> dict | None:
    last, _ = get_last_next(client, team_id, league_id, season)
    return last


def get_next(client: APIFootballClient, team_id: int, league_id: int, season: int | None = None) -> dict | None:
    _, next_ = get_last_next(client, team_id, league_id, season)
    return next_


def get_live(client: APIFootballClient, **params) -> list[dict]:
    return client.get("fixtures", live="all", **params)


def get_events(client: APIFootballClient, fixture_id: int) -> list[dict]:
    return client.get("fixtures/events", fixture=fixture_id)


def get_lineups(client: APIFootballClient, fixture_id: int) -> list[dict]:
    return client.get("fixtures/lineups", fixture=fixture_id)


def player_fixture_stats(client: APIFootballClient, player_id: int, fixture_id: int, league_id: int | None = None, season: int | None = None) -> dict:
    data = client.get("fixtures/players", fixture=fixture_id)
    for entry in data:
        if entry.get("player", {}).get("id") == player_id:
            return entry
    return {}


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


def cup_status_from_fixtures(
    last: dict | None, next_: dict | None, team_id: int
) -> str | None:
    """Return a knockout/phase status from already-fetched fixtures."""
    if not last and not next_:
        return "No fixture scheduled"
    if last:
        last_round = last.get("league", {}).get("round", "this round")
        home_id = last["teams"]["home"]["id"]
        winner = last["teams"]["home"]["winner"] if home_id == team_id else last["teams"]["away"]["winner"]
        if winner is True:
            if next_:
                next_round = next_.get("league", {}).get("round", "the next round")
                if next_round == last_round:
                    return f"Competing in {last_round}"
                return f"Advanced to {next_round}"
            return f"Won {last_round}"
        if winner is False:
            return f"Eliminated in {last_round}"
        return f"Draw in {last_round}"
    if next_:
        next_round = next_.get("league", {}).get("round", "the next round")
        return f"Upcoming {next_round}"
    return None


def cup_status(
    client: APIFootballClient, team_id: int, league_id: int, season: int | None = None
) -> str | None:
    """Return a knockout-cup status (e.g., 'Advanced to Round 4') for a team."""
    season = season or _season()
    last, next_ = get_last_next(client, team_id, league_id, season)
    return cup_status_from_fixtures(last, next_, team_id)
