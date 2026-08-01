# USMNT Abroad Newsletter + Live Match Twitter Bot

A Python 3.11+ service that:

1. Sends a weekly email newsletter summarizing USMNT-eligible players in UCL-qualifying European leagues.
2. Polls live fixtures and posts (or queues) Twitter/X updates for starts, subs, goals, assists, and full-time results.

Data comes from [API-Football via RapidAPI](https://www.api-football.com/). Emails are sent via [Resend](https://resend.com/).

## Quick start

```bash
cd /Users/bboone/usmnt-abroad-bot
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy the example environment file and fill in your keys when ready:

```bash
cp .env.example .env
```

## Running dry / mock mode

No API key is needed for a local dry run. Both scripts default to `DRY_RUN=1` and `MOCK_DATA=1`, which use synthetic fixtures and write outputs to `outbox/` instead of sending emails or tweets.

```bash
# Newsletter (writes outbox/newsletter.txt and outbox/newsletter.html)
DRY_RUN=1 MOCK_DATA=1 python -m src.run_newsletter

# Live tweets (writes outbox/tweets.txt and updates state/state.json)
DRY_RUN=1 MOCK_DATA=1 python -m src.run_live_tweets
```

## Configuration

- `config/players.json` — tracked USMNT-eligible players and their club/league IDs.
- `config/competitions.json` — competition name → API-Football league/season IDs.
- `config/broadcasters.json` — how-to-watch info for US broadcasters.
- `config/uefa_rankings.json` — UEFA association coefficients used for ordering.

## Environment variables

See `.env.example` for the full list. The main ones are:

- `RAPIDAPI_KEY` — RapidAPI key for API-Football.
- `RESEND_API_KEY`, `RESEND_FROM`, `RESEND_TO` — Resend email config.
- `TWITTER_POST_ENABLED` — set to `1` when you are ready to post to X.
- `TWITTER_*` — X API v2 credentials.
- `DRY_RUN` / `MOCK_DATA` — safe local testing.

## Tests

```bash
PYTHONPATH=. python -m pytest tests/
```

Or just compile the main scripts:

```bash
python -m py_compile src/*.py
```

## Deployment

1. Push to a GitHub repo.
2. Add the secrets/vars from `.env.example` under **Settings → Secrets and variables → Actions**.
3. Enable the two Actions workflows:
   - `newsletter.yml` runs weekly on Mondays at ~8am ET.
   - `live_tweets.yml` polls every 15 minutes and commits state to the repo.

## Project layout

```
.
├── .env.example
├── pyproject.toml
├── requirements.txt
├── config/
│   ├── players.json
│   ├── competitions.json
│   ├── broadcasters.json
│   └── uefa_rankings.json
├── src/
│   ├── api_football.py
│   ├── broadcasters.py
│   ├── config.py
│   ├── emailer.py
│   ├── fixtures.py
│   ├── live_tweets.py
│   ├── newsletter.py
│   ├── players.py
│   ├── rankings.py
│   ├── run_live_tweets.py
│   ├── run_newsletter.py
│   ├── standings.py
│   ├── tweet_formatter.py
│   └── twitter.py
├── state/
│   └── state.json
├── tests/
│   └── test_bot.py
└── .github/workflows/
    ├── newsletter.yml
    └── live_tweets.yml
```

## Notes

- The project defaults to **mock data** and **dry run** so it is safe to run without any credentials.
- Real API calls require a RapidAPI `RAPIDAPI_KEY` and `DRY_RUN=0` / `MOCK_DATA=0`.
- Live tweet posting is gated behind `TWITTER_POST_ENABLED=1`; otherwise generated tweets are written to `outbox/tweets.txt`.
