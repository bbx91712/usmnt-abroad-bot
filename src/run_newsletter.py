"""Entry point for the weekly newsletter."""
from __future__ import annotations

from .api_football import APIFootballClient
from .emailer import send


def main() -> None:
    print("Starting newsletter generation", flush=True)
    client = APIFootballClient()
    send(client)
    print("Finished newsletter generation", flush=True)


if __name__ == "__main__":
    main()
