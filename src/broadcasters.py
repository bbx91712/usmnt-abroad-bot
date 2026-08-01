"""Broadcaster / how-to-watch resolution."""
from __future__ import annotations

from . import config


def resolve(competition_name: str) -> dict[str, str | bool]:
    """Return broadcaster info for a competition, or a generic fallback."""
    mapping = config.broadcasters().get("broadcasters", {})
    info = mapping.get(competition_name)
    if info:
        return {
            "name": info["primary"],
            "link": info.get("link", ""),
            "paid": info.get("paid", False),
        }
    return {"name": "TBD", "link": "", "paid": False}
