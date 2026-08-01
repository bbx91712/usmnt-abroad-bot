"""Poll live fixtures and emit tweets for tracked players."""
from __future__ import annotations

import json

from . import broadcasters, config, fixtures, players as players_mod, tweet_formatter, twitter
from .api_football import APIFootballClient


def _season() -> int:
    return config.competitions()["season"]


def _load_state() -> dict:
    path = config.state_path()
    if not path.exists():
        return {"posted_event_ids": [], "known_lineups": {}, "known_results": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(state: dict) -> None:
    config.state_path().write_text(json.dumps(state, indent=2), encoding="utf-8")


def _event_id(fixture_id: int, event: dict) -> str:
    return f"{fixture_id}-{event['time']['elapsed']}-{event['type']}-{event.get('player', {}).get('id', '0')}"


def _process_fixture(client: APIFootballClient, player, fixture: dict, state: dict) -> None:
    fid = fixture["fixture"]["id"]
    status = fixtures.status_short(fixture)
    comp = fixture["league"]["name"]
    watch = broadcasters.resolve(comp)
    opp = fixtures.opponent_name(fixture, player.club_id)

    # Full-time result
    if status in ("FT", "AET", "PEN"):
        if fid not in state["known_results"]:
            state["known_results"].append(fid)
            goals = fixture.get("goals", {})
            score = f"{goals.get('home', 0)}-{goals.get('away', 0)}"
            result = fixtures.result_for_team(fixture, player.club_id)
            tweet = tweet_formatter.full_time(player.club, opp, score, result, comp)
            twitter.post(tweet)
        return

    if status not in ("1H", "2H", "HT"):
        return

    # Starting XI notification
    known = set(state["known_lineups"].get(str(fid), []))
    lineups = fixtures.get_lineups(client, fid)
    for lu in lineups:
        if lu["team"]["id"] == player.club_id:
            started = {pl["player"]["id"] for pl in lu.get("startXI", [])}
            if player.player_id in started and player.player_id not in known:
                state["known_lineups"].setdefault(str(fid), []).append(player.player_id)
                tweet = tweet_formatter.start(
                    player.name, player.club, opp, comp, watch
                )
                twitter.post(tweet)

    # Events
    for event in fixtures.get_events(client, fid):
        eid = _event_id(fid, event)
        if eid in state["posted_event_ids"]:
            continue

        minute = event["time"]["elapsed"]
        ev_player_id = event.get("player", {}).get("id")
        ev_assist_id = event.get("assist", {}).get("id")

        if ev_player_id == player.player_id:
            if event["type"] == "Goal":
                score = f"{fixture['goals']['home']}-{fixture['goals']['away']}"
                tweet = tweet_formatter.goal(
                    player.name, player.club, opp, minute, score, comp
                )
                twitter.post(tweet)
                state["posted_event_ids"].append(eid)
            elif event["type"] == "subst":
                tweet = tweet_formatter.sub_in(player.name, player.club, minute)
                twitter.post(tweet)
                state["posted_event_ids"].append(eid)

        if ev_assist_id == player.player_id:
            if event["type"] == "Goal":
                score = f"{fixture['goals']['home']}-{fixture['goals']['away']}"
                tweet = tweet_formatter.assist(
                    player.name, player.club, opp, minute, score, comp
                )
                twitter.post(tweet)
                state["posted_event_ids"].append(eid)
            elif event["type"] == "subst":
                tweet = tweet_formatter.sub_out(player.name, player.club, minute)
                twitter.post(tweet)
                state["posted_event_ids"].append(eid)


def poll(client: APIFootballClient | None = None) -> None:
    if client is None:
        client = APIFootballClient()
    state = _load_state()
    for player in players_mod.load_players():
        live = client.get(
            "fixtures", live="all", team=player.club_id, season=_season()
        )
        for fixture in live:
            _process_fixture(client, player, fixture, state)
    _save_state(state)
