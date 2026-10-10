"""Send the newsletter via Resend, with a dry-run fallback."""
from __future__ import annotations

import resend

from . import config, newsletter
from .api_football import APIFootballClient


def _dry_run(payload: dict[str, str]) -> None:
    outbox = config.outbox_dir()
    (outbox / "newsletter.txt").write_text(payload["text"], encoding="utf-8")
    (outbox / "newsletter.html").write_text(payload["html"], encoding="utf-8")
    print("[DRY RUN] Newsletter written to:", flush=True)
    print(f"  - {outbox / 'newsletter.txt'}", flush=True)
    print(f"  - {outbox / 'newsletter.html'}", flush=True)
    print("\n--- TEXT PREVIEW ---\n", flush=True)
    print(payload["text"][:2000], flush=True)


def send(client: APIFootballClient | None = None) -> None:
    if client is None:
        client = APIFootballClient()
    payload = newsletter.build(client)
    to = config.resend_to()
    if not to:
        to = ["dev@example.com"]

    if config.dry_run() or config.mock_data() or not config.resend_api_key():
        _dry_run(payload)
        return

    print(f"[EMAIL] Sending newsletter to {to}", flush=True)
    resend.api_key = config.resend_api_key()
    params = {
        "from": config.resend_from(),
        "to": to,
        "subject": payload["subject"],
        "html": payload["html"],
        "text": payload["text"],
    }
    resend.Emails.send(params)
