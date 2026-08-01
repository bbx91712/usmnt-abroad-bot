"""Build the weekly newsletter text and HTML."""
from __future__ import annotations

from jinja2 import Template

from . import broadcasters, config, fixtures, rankings, standings
from .api_football import APIFootballClient


def _season() -> int:
    return config.competitions()["season"]


def _player_stats(client: APIFootballClient, player_id: int, league_id: int) -> str:
    data = client.get("players", id=player_id, league=league_id, season=_season())
    if not data:
        return "n/a"
    stats_obj = data[0].get("statistics", [{}])[0]
    games = stats_obj.get("games", {})
    goals = stats_obj.get("goals", {})
    apps = games.get("appearences", 0) or 0
    minutes = games.get("minutes", 0) or 0
    g = goals.get("total", 0) or 0
    a = goals.get("assists", 0) or 0
    return f"{apps} apps, {g} goals, {a} assists, {minutes} minutes"


def _league_block(client: APIFootballClient, player, league_id: int, name: str) -> str:
    position = standings.get_team_position(client, player.club_id, league_id)
    last = fixtures.get_last(client, player.club_id, league_id)
    next_ = fixtures.get_next(client, player.club_id, league_id)
    watch = broadcasters.resolve(name)
    stats = _player_stats(client, player.player_id, league_id)

    pos_line = f"{position} in {name}" if position else f"{name} table not yet available"
    last_line = "No result yet"
    if last:
        opp = fixtures.opponent_name(last, player.club_id)
        result = fixtures.result_for_team(last, player.club_id)
        date = fixtures.format_date_et(last["fixture"]["date"])
        last_line = f"{date} vs {opp}: {result}"
    next_line = "No upcoming fixture"
    if next_:
        opp = fixtures.opponent_name(next_, player.club_id)
        date = fixtures.format_date_et(next_["fixture"]["date"])
        next_line = f"{date} vs {opp}; watch: {watch['name']} ({watch['link']})"

    return (
        f"  {name}:\n"
        f"    Current standing: {pos_line}\n"
        f"    Player stats: {stats}\n"
        f"    Last match: {last_line}\n"
        f"    Next match: {next_line}"
    )


def _cup_for_country(country: str, cup_type: str = "primary") -> tuple[int, str] | None:
    for key, comp in config.competitions()["competitions"].items():
        if (
            comp["type"] == "cup"
            and comp.get("cup_type", "primary") == cup_type
            and comp["country"] == country
        ):
            return comp["league_id"], comp["name"]
    return None


def _player_text(client: APIFootballClient, player) -> dict:
    # League block
    league_block = _league_block(client, player, player.league_id, player.league_name)

    # UCL status (best-guess from domestic position)
    position = standings.get_team_position(client, player.club_id, player.league_id)
    if position and position <= 4:
        ucl = f"{player.club} is currently in a Champions League qualification spot ({position} place)."
    else:
        ucl = f"{player.club} is outside the UCL qualification places in {player.league_name}."

    # Other Europe - mock static for now
    other = "No active UEFA Europa League or Conference League fixture this week."

    # Domestic cup
    cup_info = _cup_for_country(player.uefa_assoc, "primary")
    if cup_info:
        cup_id, cup_name = cup_info
        cup_block = _league_block(client, player, cup_id, cup_name)
    else:
        cup_block = "  Domestic cup: not tracked for this association."

    # Additional domestic cup (e.g., EFL Cup, Supercoppa Italiana)
    add_cup_info = _cup_for_country(player.uefa_assoc, "additional")
    if add_cup_info:
        add_cup_id, add_cup_name = add_cup_info
        additional_cup_block = _league_block(client, player, add_cup_id, add_cup_name)
    else:
        additional_cup_block = "  Additional domestic cup: none for this association."

    header = f"{player.name}, {player.club}, {player.league_name} ({player.country})"
    text = (
        f"{header}\n"
        f"  Champions League status: {ucl}\n"
        f"  Other European competition: {other}\n"
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
    players = rankings.sort_players(client)
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
  <p><strong>Champions League status:</strong> {{ p.ucl }}</p>
  <p><strong>Other Europe:</strong> {{ p.other_europe }}</p>
  <pre>{{ p.cup }}</pre>
  <pre>{{ p.additional_cup }}</pre>
  <pre>{{ p.league }}</pre>
  {% endfor %}
</body>
</html>
""")
    return template.render(players=player_data)
