"""Build the weekly newsletter text and HTML."""
from __future__ import annotations

from jinja2 import Template

from . import broadcasters, config, fixtures, players as players_mod, rankings, standings
from .api_football import APIFootballClient


def _season() -> int:
    return config.competitions()["season"]


def _ordinal(n: int) -> str:
    if 10 <= (n % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _round_prefix(fixture: dict | None) -> str:
    if not fixture:
        return ""
    round_ = fixture.get("league", {}).get("round")
    return f"({round_}) " if round_ else ""


def _match_stats(client: APIFootballClient, player, fixture: dict | None, league_id: int) -> str:
    if not fixture:
        return ""
    data = fixtures.player_fixture_stats(
        client, player.player_id, fixture["fixture"]["id"], league_id
    )
    if not data:
        return "(Did not feature)"
    stats = data.get("statistics", [{}])[0]
    minutes = stats.get("games", {}).get("minutes") or 0
    goals = stats.get("goals", {}).get("total") or 0
    assists = stats.get("goals", {}).get("assists") or 0
    if minutes or goals or assists:
        return f"(Goals: {goals}, Assists: {assists}, Minutes: {minutes})"
    return "(Did not feature)"


def _matches_name(api_player: dict, player) -> bool:
    target_first = (player.name.split()[0] or "").lower()
    target_last = player.name.split()[-1].lower()
    target_short = player.short_name.lower()
    first = (api_player.get("firstname") or "").lower()
    last = (api_player.get("lastname") or "").lower()
    full = (api_player.get("name") or "").lower()
    last_ok = target_last == last or target_short == last or target_last in full or target_short in full
    first_ok = (
        not first
        or first == target_first
        or first.startswith(target_first)
        or target_first.startswith(first)
        or target_first in full
    )
    return last_ok and first_ok


def _resolve_player(client: APIFootballClient, player) -> None:
    """Verify player ID and use stats for the stored league."""
    stats = None
    data = client.get("players", id=player.player_id, season=_season())
    if data and _matches_name(data[0].get("player", {}), player):
        stats = next(
            (s for s in data[0].get("statistics", []) if s.get("league", {}).get("id") == player.league_id),
            None,
        )
    if not stats:
        # Stored id may be stale; search by short name in the stored league only
        search = client.get("players", search=player.short_name, league=player.league_id, season=_season())
        for entry in search or []:
            if _matches_name(entry.get("player", {}), player):
                stats_list = entry.get("statistics", [])
                if stats_list:
                    stats = stats_list[0]
                    player.player_id = entry["player"]["id"]
                    break
    if not stats:
        return
    team = stats.get("team", {})
    league = stats.get("league", {})
    if team.get("id"):
        player.club_id = team["id"]
        player.club = team.get("name", player.club)
    if league.get("id"):
        player.league_id = league["id"]
        player.league_name = league.get("name", player.league_name)
        player.country = league.get("country", player.country)
        player.uefa_assoc = league.get("country", player.uefa_assoc)


def _player_stats(client: APIFootballClient, player, league_id: int) -> str:
    data = client.get("players", id=player.player_id, season=_season())
    if not data:
        # Stored player id may be stale; look up by name in the current squad
        squad = client.get("players/squads", team=player.club_id)
        if squad:
            for member in squad[0].get("players", []):
                member_name = member.get("name", "").lower()
                last_name = (member.get("lastname") or "").lower()
                target = player.short_name.lower()
                if target in member_name or target in last_name:
                    data = client.get("players", id=member["id"], season=_season())
                    if data:
                        break
    if not data:
        return "n/a"
    stats_list = data[0].get("statistics", [])
    stats_obj = next(
        (s for s in stats_list if s.get("league", {}).get("id") == league_id),
        {},
    )
    if not stats_obj or not stats_obj.get("games"):
        return "n/a"
    games = stats_obj.get("games", {})
    goals = stats_obj.get("goals", {})
    apps = games.get("appearences", 0) or 0
    minutes = games.get("minutes", 0) or 0
    g = goals.get("total", 0) or 0
    a = goals.get("assists", 0) or 0
    return f"{apps} apps, {g} goals, {a} assists, {minutes} minutes"


def _league_total_games(league_id: int) -> int | None:
    for comp in config.competitions()["competitions"].values():
        if comp.get("league_id") == league_id:
            return comp.get("games")
    return None


def _competition_type(league_id: int) -> str:
    for comp in config.competitions()["competitions"].values():
        if comp.get("league_id") == league_id:
            return comp.get("type", "league")
    return "league"


def _league_block(
    client: APIFootballClient,
    player,
    league_id: int,
    name: str,
    comp_format: str | None = None,
    comp_context: str | None = None,
    comp_no_fixture_text: str | None = None,
) -> str:
    last, next_ = fixtures.get_last_next(client, player.club_id, league_id)
    watch = broadcasters.resolve(name)
    stats = _player_stats(client, player, league_id)

    comp_type = _competition_type(league_id)
    if comp_type == "league":
        summary = standings.get_team_summary(client, player.club_id, league_id)
        total = _league_total_games(league_id)
        if summary:
            if total is not None:
                pos_line = f"{_ordinal(summary['rank'])} in {name}, {summary['points']} points through {summary['played']} of {total} matches"
            else:
                pos_line = f"{_ordinal(summary['rank'])} in {name}"
        else:
            pos_line = f"{name} table not yet available"
    elif not last and not next_ and comp_context:
        pos_line = "Did not qualify"
    else:
        status = fixtures.cup_status_from_fixtures(last, next_, player.club_id)
        pos_line = status or f"{name} table not yet available"
    round_for_lines = comp_type != "league"
    last_line = "No result yet"
    if last:
        opp = fixtures.opponent_name(last, player.club_id)
        result = fixtures.result_for_team(last, player.club_id)
        date = fixtures.format_date_et(last["fixture"]["date"])
        prefix = _round_prefix(last) if round_for_lines else ""
        match_stats = _match_stats(client, player, last, league_id)
        stats_suffix = f" {match_stats}" if match_stats else ""
        last_line = f"{prefix}{date} vs {opp}: {result}{stats_suffix}"
    next_line = "No upcoming fixture"
    if next_:
        opp = fixtures.opponent_name(next_, player.club_id)
        date = fixtures.format_date_et(next_["fixture"]["date"])
        prefix = _round_prefix(next_) if round_for_lines else ""
        next_line = f"{prefix}{date} vs {opp}; watch: {watch['name']} ({watch['link']})"

    if not last and not next_ and comp_no_fixture_text:
        return (
            f"  {name}:\n"
            f"    {comp_no_fixture_text}\n"
        )
    if not last and not next_ and comp_context:
        note_line = f"    {comp_context}\n" if comp_context else ""
        return (
            f"  {name}:\n"
            f"    Current standing: {pos_line}\n"
            f"{note_line}"
        )
    note_line = f"    ({comp_format})\n" if comp_format else ""
    return (
        f"  {name}:\n"
        f"    Current standing: {pos_line}\n"
        f"{note_line}"
        f"    Player stats: {stats}\n"
        f"    Last match: {last_line}\n"
        f"    Next match: {next_line}"
    )


def _cup_for_country(country: str, cup_type: str = "primary") -> tuple[int, str, str | None, str | None, str | None] | None:
    for key, comp in config.competitions()["competitions"].items():
        if (
            comp["type"] == "cup"
            and comp.get("cup_type", "primary") == cup_type
            and comp["country"] == country
        ):
            return (
                comp["league_id"],
                comp["name"],
                comp.get("format"),
                comp.get("context"),
                comp.get("no_fixture_text"),
            )
    return None


_UCL_SPOTS = {39: 4, 140: 4, 135: 4, 78: 4, 61: 4, 88: 2}


def _ucl_spots_for_league(league_id: int) -> int | None:
    return _UCL_SPOTS.get(league_id)


def _european_status(client: APIFootballClient, player) -> list[dict]:
    """Return UCL/UEL/UECL status entries for the player's club."""
    entries = []
    for key, comp in config.competitions()["competitions"].items():
        if comp.get("type") != "european":
            continue
        league_id = comp["league_id"]
        name = comp["name"]
        last, next_ = fixtures.get_last_next(client, player.club_id, league_id)
        active = bool(last or next_)
        entry = {
            "key": key,
            "name": name,
            "league_id": league_id,
            "format": comp.get("format"),
            "active": active,
            "last": last,
            "next": next_,
            "summary": None,
            "status": None,
        }
        if active:
            entry["summary"] = standings.get_team_summary(client, player.club_id, league_id)
            if not entry["summary"]:
                entry["status"] = fixtures.cup_status_from_fixtures(last, next_, player.club_id)
        entries.append(entry)
    return entries


def _other_europe_text(client: APIFootballClient, player, european: list[dict]) -> str:
    """Return a FA-Cup-style block for each active UCL/UEL/UECL competition."""
    blocks = []
    for e in european:
        if not e["active"]:
            continue
        if e["summary"]:
            pos_line = (
                f"{_ordinal(e['summary']['rank'])} in {e['name']}, "
                f"{e['summary']['points']} points through {e['summary']['played']} matches"
            )
        elif e["status"]:
            pos_line = e["status"]
        else:
            pos_line = f"{e['name']} table not yet available"
        last = e["last"]
        next_ = e["next"]
        last_line = "No result yet"
        if last:
            opp = fixtures.opponent_name(last, player.club_id)
            result = fixtures.result_for_team(last, player.club_id)
            date = fixtures.format_date_et(last["fixture"]["date"])
            match_stats = _match_stats(client, player, last, e["league_id"])
            stats_suffix = f" {match_stats}" if match_stats else ""
            last_line = f"{_round_prefix(last)}{date} vs {opp}: {result}{stats_suffix}"
        next_line = "No upcoming fixture"
        if next_:
            opp = fixtures.opponent_name(next_, player.club_id)
            date = fixtures.format_date_et(next_["fixture"]["date"])
            watch = broadcasters.resolve(e["key"])
            next_line = f"{_round_prefix(next_)}{date} vs {opp}; watch: {watch['name']} ({watch['link']})"
        stats = _player_stats(client, player, e["league_id"])
        format_line = f"    ({e['format']})\n" if e.get("format") else ""
        blocks.append(
            f"  {e['name']}:\n"
            f"    Current standing: {pos_line}\n"
            f"{format_line}"
            f"    Player stats: {stats}\n"
            f"    Last match: {last_line}\n"
            f"    Next match: {next_line}"
        )
    return "\n\n".join(blocks)


def _ucl_status(client: APIFootballClient, player, european: list[dict]) -> str:
    """Return the 2027-28 UCL qualification paths for the player's club."""
    spots = _ucl_spots_for_league(player.league_id)
    active = {e["key"] for e in european if e["active"]}
    paths = []
    if spots is not None:
        paths.append(f"a top-{spots} finish in {player.league_name}")
    else:
        paths.append(f"a strong domestic finish in {player.league_name}")
    if "UCL" in active:
        paths.append("winning the 2026-27 UEFA Champions League")
    elif "UEL" in active:
        paths.append("winning the 2026-27 UEFA Europa League")
    option_lines = []
    for i, p in enumerate(paths):
        if i > 0:
            option_lines.append("      - or -")
        option_lines.append(f"      {p[0].upper()}{p[1:]}")
    return (
        "  2027-28 Champions League status:\n"
        f"    {player.club} can qualify for the 2027-28 Champions League by:\n"
        + "\n".join(option_lines)
    )


def _player_text(client: APIFootballClient, player) -> dict:
    # League block
    league_block = _league_block(client, player, player.league_id, player.league_name)

    # European competition status and 2027-28 UCL qualification paths
    european = _european_status(client, player)
    ucl = _ucl_status(client, player, european)
    other = _other_europe_text(client, player, european)

    # Domestic cup
    cup_info = _cup_for_country(player.uefa_assoc, "primary")
    if cup_info:
        cup_id, cup_name, cup_format, cup_context, cup_no_fixture_text = cup_info
        cup_block = _league_block(client, player, cup_id, cup_name, cup_format, cup_context, cup_no_fixture_text)
    else:
        cup_block = "  Domestic cup: not tracked for this association."

    # Additional domestic cup (e.g., EFL Cup, Supercoppa Italiana)
    add_cup_info = _cup_for_country(player.uefa_assoc, "additional")
    if add_cup_info:
        add_cup_id, add_cup_name, add_cup_format, add_cup_context, add_cup_no_fixture_text = add_cup_info
        additional_cup_block = _league_block(client, player, add_cup_id, add_cup_name, add_cup_format, add_cup_context, add_cup_no_fixture_text)
    else:
        additional_cup_block = "  Additional domestic cup: none for this association."

    header = f"{player.name}, {player.club}, {player.league_name} ({player.country})"
    other_section = f"{other}\n" if other else ""
    text = (
        f"{header}\n"
        f"{ucl}\n"
        f"{other_section}"
        f"{cup_block}\n"
        f"{additional_cup_block}\n"
        f"{league_block}"
    )
    return {
        "name": player.name,
        "club": player.club,
        "league_name": player.league_name,
        "country": player.country,
        "ucl": ucl,
        "other_europe": other,
        "cup": cup_block,
        "additional_cup": additional_cup_block,
        "league": league_block,
        "text": text,
    }


def build(client: APIFootballClient) -> dict[str, str]:
    player_list = players_mod.load_players()
    for p in player_list:
        _resolve_player(client, p)
    players = rankings.sort_players(client, player_list)
    player_data = [_player_text(client, p) for p in players]

    text = "\n\n".join(p["text"] for p in player_data)
    html = _render_html(player_data)

    return {
        "subject": "USMNT Abroad Weekly Update",
        "text": text,
        "html": html,
    }


def _render_html(player_data: list[dict]) -> str:
    template = Template("""
<html>
<body>
  <h1>USMNT Abroad Weekly Update</h1>
  {% for p in players %}
  <h2>{{ p.name }} - {{ p.club }} ({{ p.league_name }})</h2>
  <pre>{{ p.ucl }}</pre>
  {% if p.other_europe %}<pre>{{ p.other_europe }}</pre>{% endif %}
  <pre>{{ p.cup }}</pre>
  <pre>{{ p.additional_cup }}</pre>
  <pre>{{ p.league }}</pre>
  {% endfor %}
</body>
</html>
""")
    return template.render(players=player_data)
