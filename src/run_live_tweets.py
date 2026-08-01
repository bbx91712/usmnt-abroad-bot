"""Entry point for the live-match Twitter bot."""
from __future__ import annotations

from .api_football import APIFootballClient
from .live_tweets import poll


def main() -> None:
    client = APIFootballClient()
    poll(client)


if __name__ == "__main__":
    main()
