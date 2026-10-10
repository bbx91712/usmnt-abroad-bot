"""Scrape yanks-abroad.co/players/ and discover USMNT-eligible players in configured top leagues."""
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from . import config
from .api_football import APIFootballClient


_URL = "https://yanks-abroad.co/players/"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _top_league_ids() -> dict[str, int]:
    return {
        c["name"]: c["league_id"]
        for c in config.competitions()["competitions"].values()
        if c.get("type") == "league"
    }


def _league_to_id(league_text: str) -> int | None:
    """Map a league name from the site to a configured top-league ID."""
    top = _top_league_ids()
    text = _norm(league_text)
    if "english premier league" in text or text == "premier league":
        return top.get("Premier League")
    if "bundesliga" in text and "austrian" not in text and "regionalliga" not in text:
        return top.get("Bundesliga")
    if "la liga" in text or "laliga" in text:
        return top.get("La Liga")
    if "serie a" in text:
        return top.get("Serie A")
    if "ligue 1" in text or "ligue1" in text or "ligue" in text and "1" in text:
        return top.get("Ligue 1")
    if "eredivisie" in text:
        return top.get("Eredivisie")
    return None


def _clean_name(name_text: str) -> str:
    return re.sub(r"[^A-Za-z\s,\-'.]", "", name_text).strip()


def _parse_name(name_text: str) -> tuple[str, str]:
    """Return (full_name, short_name) from a site name."""
    name_text = _clean_name(name_text)
    if "," in name_text:
        last, first = name_text.split(",", 1)
        last = last.strip()
        first = first.strip()
        return f"{first} {last}", last
    parts = name_text.split()
    if len(parts) > 1:
        return name_text, parts[-1]
    return name_text, name_text


def _scrape_candidates() -> list[dict]:
    resp = requests.get(_URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    candidates = []
    seen = set()
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            text = [" ".join(c.stripped_strings) for c in cells]
            if not text[0] or not text[1] or not text[2]:
                continue
            full, short = _parse_name(text[0])
            if not full:
                continue
            club = text[1].strip()
            league = text[2].strip()
            league_id = _league_to_id(league)
            if league_id is None:
                continue
            key = (short.lower(), club.lower(), league_id)
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                "full_name": full,
                "short_name": short,
                "club": club,
                "league_name": league,
                "league_id": league_id,
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
        short = candidate["short_name"].lower()
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
    print(f"Found {len(candidates)} USMNT-eligible players in tracked top leagues on yanks-abroad.co\n")
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
