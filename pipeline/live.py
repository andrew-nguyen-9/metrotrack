"""Live CTA feed — E11 sampler + endpoint smoke (e4a).

The *fetch + normalize* of the live CTA Bus/Train Tracker feed lives in the Astro
endpoint (`frontend/src/lib/live.ts`, served at `/api/live/<metro>`), so the API
keys stay server-side and there's ONE normalizer. This module is the small backend
half e4a still owns:

  • `append_sample` — persist one normalized `LiveFeed` payload as an append-only
    NDJSON log for E11 (delay/crowding time series). Idempotent: re-appending a
    payload with a `generated` timestamp already in the log is a no-op, so a retried
    cron run neither duplicates nor rewrites history.
  • `smoke` — hit the deployed/local endpoint, validate the schema, print counts, or
    log a credential/rate-limit blocker (never raises) — the e4a acceptance check.

# ponytail: E11 samples are an *append log*, deliberately NOT a content-hashed bronze
# snapshot — a live feed is a growing time series, and the brief says a lightweight
# append is enough (no warehouse this unit). E11 reads these NDJSON files directly.
Run:  python pipeline/live.py smoke [URL]      # default URL = local dev endpoint
      python pipeline/live.py sample <URL>     # fetch once + append for E11
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BRONZE_ROOT = REPO / "data" / "bronze"
DEFAULT_URL = "http://localhost:4321/api/live/chicago"
UA = "MetroTrackBot/0.1 (+https://transit.an9.dev; civic accountability data)"

# The keys every normalized LiveFeed payload must carry (mirrors src/lib/live.ts).
FEED_KEYS = ("metro", "generated", "vehicles", "arrivals", "errors")


def sample_path(feed: dict, *, root: Path = BRONZE_ROOT) -> Path:
    """Per-metro, per-UTC-day NDJSON log path for a payload's `generated` day."""
    metro = feed["metro"]
    day = str(feed["generated"])[:10] or "unknown"
    return root / metro / "cta_live" / f"{day}.ndjson"


def append_sample(feed: dict, *, root: Path = BRONZE_ROOT) -> tuple[Path, bool]:
    """Append one normalized LiveFeed to its day log. Idempotent on `generated`.

    Returns (path, appended). Skips the write when a line with the same `generated`
    timestamp is already present, so a re-run is safe.
    """
    missing = [k for k in FEED_KEYS if k not in feed]
    if missing:
        raise ValueError(f"payload missing keys {missing}: not a LiveFeed")

    out = sample_path(feed, root=root)
    out.parent.mkdir(parents=True, exist_ok=True)
    gen = feed["generated"]
    if out.exists():
        for line in out.read_text().splitlines():
            if line and json.loads(line).get("generated") == gen:
                return out, False  # already sampled this instant
    with out.open("a") as fh:
        fh.write(json.dumps(feed, separators=(",", ":"), sort_keys=True) + "\n")
    return out, True


def summarize(feed: dict) -> str:
    """One-line count of a normalized payload (for smoke output)."""
    v = len(feed.get("vehicles", []))
    a = len(feed.get("arrivals", []))
    errs = feed.get("errors", [])
    tail = f" — errors: {'; '.join(errs)}" if errs else ""
    return f"{feed.get('metro', '?')}: {v} vehicles, {a} arrivals{tail}"


def fetch_feed(url: str) -> dict:
    """GET the live endpoint → parsed LiveFeed dict. Raises on transport error."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 (trusted URL)
        return json.loads(resp.read().decode())


def smoke(url: str = DEFAULT_URL) -> int:
    """Hit the endpoint, validate schema, print counts. Never raises → CI-safe.

    A missing key or unreachable endpoint is logged as a blocker and returns 0
    (the brief accepts "logs a rate-limit/credential blocker"), not a hard failure.
    """
    print(f"  live smoke → {url}")
    try:
        feed = fetch_feed(url)
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        print(f"  BLOCKED (endpoint unreachable, expected off-Vercel): {e}")
        return 0
    missing = [k for k in FEED_KEYS if k not in feed]
    if missing:
        print(f"  FAIL: response missing keys {missing}")
        return 1
    print(f"  ok  schema valid — {summarize(feed)}")
    if any("credentials_missing" in e for e in feed.get("errors", [])):
        print("  note: CTA keys unset on the server (set CTA_BUS_TRACKER_API / "
              "CTA_TRAIN_TRACKER_API) — feed returns empty until then")
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "smoke"
    url = argv[2] if len(argv) > 2 else DEFAULT_URL
    if cmd == "smoke":
        return smoke(url)
    if cmd == "sample":
        feed = fetch_feed(url)
        path, appended = append_sample(feed)
        print(f"  {'appended' if appended else 'skipped (dup)'} → "
              f"{path.relative_to(REPO)} — {summarize(feed)}")
        return 0
    print(f"unknown command: {cmd} (use: smoke | sample)")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
