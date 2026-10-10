"""API-Football client with in-memory caching, retries, and a dry-run/mock mode."""
from __future__ import annotations

import json
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import config


class APIFootballClient:
    """Thin client for API-Football v3 via RapidAPI."""

    def __init__(self) -> None:
        self.api_key = config.rapidapi_key()
        self.host = config.api_football_host()
        self.base_url = config.api_football_base()
        self.dry_run = config.dry_run() or config.mock_data()
        self._cache: dict[str, Any] = {}
        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)

    def _cache_key(self, endpoint: str, params: dict[str, Any]) -> str:
        return f"{endpoint}:{json.dumps(params, sort_keys=True)}"

    def get(self, endpoint: str, **params: Any) -> list[dict[str, Any]]:
        """GET an API endpoint. Returns the 'response' list."""
        key = self._cache_key(endpoint, params)
        if key in self._cache:
            return self._cache[key]

        if self.dry_run:
            data = self._mock(endpoint, params)
            self._cache[key] = data
            return data

        if not self.api_key:
            raise RuntimeError("RAPIDAPI_KEY is not configured")

        url = f"{self.base_url}/{endpoint}"
        if "api-sports.io" in self.host:
            headers = {"x-apisports-key": self.api_key}
        else:
            headers = {
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": self.host,
            }
        for attempt in range(3):
            try:
                resp = self.session.get(url, headers=headers, params=params, timeout=30)
                if resp.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                payload = resp.json()
                if payload.get("errors"):
                    raise RuntimeError(f"API-Football error on {endpoint}: {payload['errors']}")
                data = payload.get("response", [])
                if not self.dry_run:
                    print(f"[API] {endpoint} {params} -> {len(data)} results", flush=True)
                self._cache[key] = data
                return data
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        return []

    def clear_cache(self) -> None:
        self._cache.clear()

    def _mock(self, endpoint: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if endpoint == "standings":
            return _mock_standings(params)
        if endpoint == "fixtures":
            return _mock_fixtures(params)
        if endpoint == "fixtures/events":
            return _mock_events(params)
        if endpoint == "fixtures/lineups":
            return _mock_lineups(params)
        if endpoint == "players":
            return _mock_players(params)
        return []


def _mock_standings(params: dict[str, Any]) -> list[dict[str, Any]]:
    league_id = params.get("league", 0)
    season = params.get("season", config.competitions()["season"])
    top = {
        39: [  # Premier League
            {"rank": 4, "team": {"id": 49, "name": "AFC Bournemouth"}},
            {"rank": 12, "team": {"id": 52, "name": "Crystal Palace"}},
        ],
        78: [  # Bundesliga
            {"rank": 2, "team": {"id": 165, "name": "Borussia Dortmund"}},
            {"rank": 9, "team": {"id": 176, "name": "Borussia Mönchengladbach"}},
        ],
        135: [  # Serie A
            {"rank": 1, "team": {"id": 489, "name": "AC Milan"}},
            {"rank": 3, "team": {"id": 496, "name": "Juventus"}},
        ],
        61: [  # Ligue 1
            {"rank": 5, "team": {"id": 1683, "name": "AS Monaco"}},
        ],
        88: [  # Eredivisie
            {"rank": 1, "team": {"id": 197, "name": "PSV Eindhoven"}},
        ],
    }
    table = top.get(league_id, [{"rank": 1, "team": {"id": 1, "name": "Sample FC"}}])
    return [
        {
            "league": {"id": league_id, "season": season, "standings": [table]},
            "note": "MOCK_DATA",
        }
    ]


def _mock_fixtures(params: dict[str, Any]) -> list[dict[str, Any]]:
    team = params.get("team", 0)
    last = params.get("last")
    next_ = params.get("next")
    live = params.get("live")

    base = _fixture(team)
    if live:
        base["fixture"]["status"] = {"short": "2H", "elapsed": 67}
        base["goals"] = {"home": 1, "away": 0}
        return [base]
    if last:
        base["fixture"]["status"] = {"short": "FT", "elapsed": 90}
        base["goals"] = {"home": 2, "away": 1}
        return [base]
    if next_:
        base["fixture"]["date"] = "2025-09-20T18:45:00+00:00"
        base["fixture"]["status"] = {"short": "NS"}
        base["goals"] = {"home": 0, "away": 0}
        return [base]
    return []


def _fixture(team_id: int) -> dict[str, Any]:
    opponents = {
        489: (496, "Juventus"),
        496: (489, "AC Milan"),
        165: (176, "Borussia Mönchengladbach"),
        176: (165, "Borussia Dortmund"),
        52: (49, "AFC Bournemouth"),
        49: (52, "Crystal Palace"),
        197: (201, "Ajax"),
        1683: (91, "Marseille"),
    }
    opp_id, opp_name = opponents.get(team_id, (1, "Opponent"))
    return {
        "fixture": {
            "id": 100000 + team_id,
            "date": "2025-08-25T18:45:00+00:00",
            "status": {"short": "FT", "elapsed": 90},
            "venue": {"name": "San Siro"},
        },
        "league": {"id": 135, "name": "Serie A"},
        "teams": {
            "home": {"id": team_id, "name": f"Team {team_id}"},
            "away": {"id": opp_id, "name": opp_name},
        },
        "goals": {"home": 1, "away": 1},
    }


def _mock_events(params: dict[str, Any]) -> list[dict[str, Any]]:
    fixture_id = params.get("fixture", 0)
    return [
        {
            "time": {"elapsed": 12},
            "team": {"id": fixture_id % 1000, "name": "Home"},
            "player": {"id": 474, "name": "Christian Pulisic"},
            "assist": {"id": None, "name": None},
            "type": "Goal",
            "detail": "Normal Goal",
        },
        {
            "time": {"elapsed": 68},
            "team": {"id": fixture_id % 1000, "name": "Home"},
            "player": {"id": 284, "name": "Yunus Musah"},
            "assist": {"id": None, "name": None},
            "type": "subst",
            "detail": "Substitution 1",
        },
    ]


def _mock_lineups(params: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "team": {"id": params.get("fixture", 0) % 1000, "name": "Home"},
            "startXI": [
                {"player": {"id": 474, "name": "Christian Pulisic", "number": 11}}
            ],
            "substitutes": [
                {"player": {"id": 284, "name": "Yunus Musah", "number": 80}}
            ],
        }
    ]


def _mock_players(params: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "player": {"id": 474, "name": "Christian Pulisic"},
            "statistics": [
                {
                    "games": {"appearences": 3, "minutes": 250},
                    "goals": {"total": 1, "assists": 1},
                }
            ],
        }
    ]
