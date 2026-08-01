"""Twitter/X poster; falls back to an outbox file when disabled or no credentials."""
from __future__ import annotations

import tweepy

from . import config


def _queue(tweet: str) -> bool:
    outbox = config.outbox_dir()
    with open(outbox / "tweets.txt", "a", encoding="utf-8") as f:
        f.write(tweet + "\n---\n")
    print("[DRY RUN] Tweet queued in outbox:")
    print(tweet)
    return False


def post(tweet: str) -> bool:
    if not config.twitter_post_enabled():
        return _queue(tweet)

    creds = config.twitter_credentials()
    required = [creds["bearer_token"], creds["api_key"], creds["api_secret"], creds["access_token"], creds["access_secret"]]
    if not all(required):
        print("[TWITTER] Missing credentials; falling back to outbox.")
        return _queue(tweet)

    client = tweepy.Client(
        bearer_token=creds["bearer_token"],
        consumer_key=creds["api_key"],
        consumer_secret=creds["api_secret"],
        access_token=creds["access_token"],
        access_token_secret=creds["access_secret"],
    )
    try:
        client.create_tweet(text=tweet)
        print("[TWITTER] Posted tweet:")
        print(tweet)
        return True
    except Exception as exc:  # pragma: no cover
        print(f"[TWITTER ERROR] {exc}")
        return _queue(tweet)
