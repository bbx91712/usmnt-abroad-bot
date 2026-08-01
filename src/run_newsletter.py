"""Entry point for the weekly newsletter."""
from __future__ import annotations

from .api_football import APIFootballClient
from .emailer import send


def main() -> None:
    client = APIFootballClient()
    send(client)


if __name__ == "__main__":
    main()
