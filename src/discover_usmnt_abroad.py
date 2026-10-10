"""Scrape ussoccerplayers.com and discover USMNT-eligible players in configured top leagues."""
from __future__ import annotations

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from . import config
from .api_football import APIFootballClient


_URL = "https://ussoccerplayers.com/usmnt-players-abroad"


def _top_leagues() -> dict[str, int]:
    """Map normalized league name -> league_id for the configured domestic top leagues."""
    out = {}
    for c in config.competitions()["competitions"].values():
        if c.get("type") == "league":
            out[_norm(c["name"])] = c["league_id"]
    return out


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _parse_name(name_text: str) -> tuple[str, str]:
    """Return (full_name, short_name) from a site name."""
    name_text = re.sub(r"\[|\]", "", name_text).strip()
    # Site mostly uses "Last, First"
    if "," in name_text:
        last, first = name_text.split(",", 1)
        last = last.strip()
        first = first.strip()
        return f"{first} {last}", last
    # Fall back to "First Last"; use the final token as the last name.
    parts = name_text.split()
    if len(parts) > 1:
        return name_text, parts[-1]
    return name_text, name_text


def _scrape_candidates() -> list[dict]:
    resp = requests.get(_URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    top_leagues = _top_leagues()
    candidates = []
    seen = set()
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["td"])
            if len(cells) < 3:
                continue
            text = [" ".join(c.stripped_strings) for c in cells]
            if not text[0] or not text[1] or not text[2]:
                continue
            full, short = _parse_name(text[0])
            club = text[1]
            league = text[2]
            league_norm = _norm(league)
            if league_norm not in top_leagues:
                continue
            key = (short.lower(), club.lower(), top_leagues[league_norm])
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                "full_name": full,
                "short_name": short,
                "club": club,
                "league_name": league,
                "league_id": top_leagues[league_norm],
            })
    return candidates


def _api_matches(client: APIFootballClient, candidate: dict) -> list[dict]:
    season = config.competitions()["season"]
    results = client.get(
        "players",
        search=candidate["short_name"],
        league=candidate["league_id"],
        season=season,
    )
    matches = []
    for r in results:
        p = r.get("player", {})
        api_name = (p.get("name") or "").lower()
        api_first = (p.get("firstname") or "").lower()
        api_last = (p.get("lastname") or "").lower()
        full = candidate["full_name"].lower()
        short = candidate["short_name"].lower()
        # Require at least last name match; first name optional because it may be abbreviated.
        if short not in api_name and short != api_last:
            continue
        if "," in candidate["full_name"].lower():
            first = candidate["full_name"].split(",", 1)[1].strip().lower()
            if first and first not in api_name and first not in api_first:
                continue
        stats = r.get("statistics", [{}])[0]
        team = stats.get("team", {})
        league = stats.get("league", {})
        matches.append({
            "player_id": p.get("id"),
            "name": p.get("name"),
            "team_id": team.get("id"),
            "team": team.get("name"),
            "league_id": league.get("id"),
            "league": league.get("name"),
        })
    return matches


def main() -> None:
    client = APIFootballClient()
    candidates = _scrape_candidates()
    print(f"Found {len(candidates)} USMNT-eligible players in tracked top leagues on ussoccerplayers.com\n")
    for c in candidates:
        print(f"{c['full_name']} ({c['club']}, {c['league_name']})")
        matches = _api_matches(client, c)
        if not matches:
            print("  No API match found.")
            continue
        if len(matches) == 1:
            m = matches[0]
            print(
                f"  -> player_id={m['player_id']}  name={m['name']}  "
                f"team_id={m['team_id']}  team={m['team']}  "
                f"league_id={m['league_id']}  league={m['league']}"
            )
        else:
            print("  Multiple API matches; verify the correct one:")
            for m in matches[:5]:
                print(
                    f"    player_id={m['player_id']}  name={m['name']}  "
                    f"team_id={m['team_id']}  team={m['team']}  "
                    f"league_id={m['league_id']}  league={m['league']}"
                )


if __name__ == "__main__":
    main()
