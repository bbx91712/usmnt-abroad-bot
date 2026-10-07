"""Configuration loader: JSON configs and environment variables."""
from __future__ import annotations

import functools
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"


def _env(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.lower() in ("1", "true", "yes", "on")


@functools.lru_cache(maxsize=1)
def _load_json(name: str) -> dict:
    with open(CONFIG_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


def players() -> list[dict]:
    return _load_json("players.json")["players"]


def competitions() -> dict:
    return _load_json("competitions.json")


def broadcasters() -> dict:
    return _load_json("broadcasters.json")


def uefa_rankings() -> dict:
    return _load_json("uefa_rankings.json")["rankings"]


def project_root() -> Path:
    return ROOT


def state_path() -> Path:
    return ROOT / "state" / "state.json"


def outbox_dir() -> Path:
    d = ROOT / "outbox"
    d.mkdir(exist_ok=True)
    return d


def rapidapi_key() -> str | None:
    return _env("RAPIDAPI_KEY")


def api_football_host() -> str:
    return _env("API_FOOTBALL_HOST", "v3.football.api-sports.io")


def api_football_base() -> str:
    return _env("API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io")


def dry_run() -> bool:
    return _truthy(_env("DRY_RUN", "1"))


def mock_data() -> bool:
    return _truthy(_env("MOCK_DATA", "1"))


def resend_api_key() -> str | None:
    return _env("RESEND_API_KEY")


def resend_from() -> str:
    return _env("RESEND_FROM", "newsletter@example.com")


def resend_to() -> list[str]:
    raw = _env("RESEND_TO", "")
    return [a.strip() for a in raw.split(",") if a.strip()]


def twitter_post_enabled() -> bool:
    return _truthy(_env("TWITTER_POST_ENABLED", "0"))


def twitter_credentials() -> dict[str, str | None]:
    return {
        "bearer_token": _env("TWITTER_BEARER_TOKEN"),
        "api_key": _env("TWITTER_API_KEY"),
        "api_secret": _env("TWITTER_API_SECRET"),
        "access_token": _env("TWITTER_ACCESS_TOKEN"),
        "access_secret": _env("TWITTER_ACCESS_SECRET"),
    }
