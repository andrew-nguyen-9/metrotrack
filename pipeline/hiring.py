"""Hiring bronze loader — weekly open-postings snapshot per service board.

The hiring pillar's product is the *time series*: how many jobs each authority has
posted, snapshotted weekly. Each authority exposes a different reliable signal
(docs/modeling/UNDERSTAFFING_METRIC.md, data/bronze/hiring/SOURCE.md):

  • CTA   — Taleo prints a total ("Job Openings 1 - 13 of 13").
  • Metra — Cadient lists requisitions (count distinct job-detail postings).
  • Pace  — Oracle Recruiting Cloud REST API returns `TotalJobsCount`.

The pure `parse_*`/`count_*`/`append_snapshot` functions carry all the logic and are
covered by the no-network selftest. `fetch_*` does the network I/O — plain HTTP for
the Oracle JSON API; Playwright (lazy-imported) renders the two JS applicant-tracking
systems. `snapshot()` is append-safe: re-running on the same day replaces that day's
rows, never duplicates. See docs/phases/v1/v1.3/PLAN.md.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from datetime import date
from pathlib import Path

import bronze

REPO_ROOT = Path(__file__).resolve().parent.parent
POSTINGS_CSV = REPO_ROOT / "data" / "bronze" / "hiring" / "postings.csv"

TALEO_URL = "https://chicagotransit.taleo.net/careersection/ex/jobsearch.ftl"
CADIENT_URL = (
    "https://cta.cadienttalent.com/index.jsp?seq=postingSearchResults"
    "&applicationName=MetraKTMDReqExt&locale=en_US"
    "&event=com.deploy.application.ca.plugin.PostingSearch.doSearch&source=alljobs"
)
ORACLE_URL = (
    "https://iaymqy.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/"
    "recruitingCEJobRequisitions?onlyData=true&finder=findReqs;siteNumber=CX_1,limit=200"
    "&expand=requisitionList"
)

# Generic link/labels that appear in a Cadient listing but are not a job posting.
CADIENT_NOISE = {"apply now", "apply", "view all jobs", "search", ""}


def parse_taleo_count(rendered_text: str | bytes) -> int:
    """CTA Taleo: read the printed total from "Job Openings 1 - 13 of 13"."""
    text = rendered_text.decode() if isinstance(rendered_text, (bytes, bytearray)) else rendered_text
    m = re.search(r"Job Openings\s+[\d,]+\s*-\s*[\d,]+\s+of\s+([\d,]+)", text, re.I)
    if not m:
        raise ValueError("Taleo total not found in rendered text")
    return int(m.group(1).replace(",", ""))


def count_cadient_titles(titles: list[str]) -> int:
    """Metra Cadient: count distinct job-detail postings, dropping generic links."""
    seen = []
    for t in titles:
        norm = (t or "").strip()
        if norm.lower() in CADIENT_NOISE:
            continue
        if norm not in seen:
            seen.append(norm)
    return len(seen)


def parse_oracle_count(raw_json: str | bytes) -> int:
    """Pace Oracle Recruiting: the REST API's `TotalJobsCount` (fallback list length)."""
    data = json.loads(raw_json)
    item = data["items"][0] if "items" in data else data
    total = item.get("TotalJobsCount")
    if total is None:
        total = len(item.get("requisitionList", []))
    return int(total)


def append_snapshot(existing_csv: bytes, rows: list[dict], today: str) -> bytes:
    """Append today's rows to the snapshot log; replace any same-(authority, date) row.

    Idempotent on (authority_id, as_of): re-running the same day overwrites that day's
    count rather than duplicating, so the bronze stays append-safe.
    """
    fields = ["authority_id", "as_of", "open_postings", "source_url", "method"]
    keep: dict[tuple[str, str], dict] = {}
    if existing_csv and existing_csv.strip():
        for r in csv.DictReader(io.StringIO(existing_csv.decode("utf-8-sig"))):
            keep[(r["authority_id"], r["as_of"])] = {k: r[k] for k in fields}
    for r in rows:
        rec = {**r, "as_of": today}
        keep[(rec["authority_id"], today)] = {k: str(rec[k]) for k in fields}

    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=fields)
    w.writeheader()
    for key in sorted(keep, key=lambda k: (k[1], k[0])):
        w.writerow(keep[key])
    return out.getvalue().encode()


def _fetch_url(url: str, accept: str) -> bytes:
    import urllib.request
    ua = "MetroTrackBot/0.1 (+https://transit.an9.dev; civic accountability data; polite weekly)"
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": accept})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch_oracle() -> bytes:
    return _fetch_url(ORACLE_URL, "application/json")


def _render_text(url: str, wait_selector: str | None = None) -> str:
    """Render a JS page headless and return body innerText (lazy Playwright import)."""
    from playwright.sync_api import sync_playwright  # lazy: keeps selftest no-dep
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent="MetroTrackBot/0.1 (+https://transit.an9.dev)")
        page.goto(url, timeout=60000, wait_until="networkidle")
        if wait_selector:
            page.wait_for_selector(wait_selector, timeout=20000)
        text = page.inner_text("body")
        browser.close()
    return text


def _render_links(url: str, href_pattern: str) -> list[str]:
    """Render a JS page and return the texts of anchors whose href matches a pattern."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent="MetroTrackBot/0.1 (+https://transit.an9.dev)")
        page.goto(url, timeout=60000, wait_until="networkidle")
        titles = page.eval_on_selector_all(
            "a",
            "(els, pat) => els.filter(a => new RegExp(pat,'i').test(a.href))"
            ".map(a => (a.innerText||'').trim())",
            href_pattern,
        )
        browser.close()
    return titles


def _gather() -> list[dict]:
    """Best-effort: a source that fails is skipped this run (logged), not fatal."""
    rows: list[dict] = []
    try:
        n = parse_taleo_count(_render_text(TALEO_URL, "text=Job Openings"))
        rows.append({"authority_id": "cta", "open_postings": n, "source_url": TALEO_URL, "method": "taleo"})
    except Exception as e:  # noqa: BLE001 — resilience is the point
        print(f"  skip cta: {e}", file=sys.stderr)
    try:
        titles = _render_links(CADIENT_URL, r"jobDetail|postingDetail|seq=postingView|viewPosting")
        rows.append({"authority_id": "metra", "open_postings": count_cadient_titles(titles),
                     "source_url": CADIENT_URL, "method": "cadient"})
    except Exception as e:  # noqa: BLE001
        print(f"  skip metra: {e}", file=sys.stderr)
    try:
        n = parse_oracle_count(fetch_oracle())
        rows.append({"authority_id": "pace", "open_postings": n, "source_url": ORACLE_URL, "method": "oracle"})
    except Exception as e:  # noqa: BLE001
        print(f"  skip pace: {e}", file=sys.stderr)
    return rows


def snapshot(today: str | None = None) -> int:
    today = today or date.today().isoformat()
    rows = _gather()
    if not rows:
        sys.exit("no sources reachable — nothing to snapshot")
    existing = POSTINGS_CSV.read_bytes() if POSTINGS_CSV.exists() else b""
    POSTINGS_CSV.parent.mkdir(parents=True, exist_ok=True)
    POSTINGS_CSV.write_bytes(append_snapshot(existing, rows, today))
    receipt = bronze.ingest_csv("hiring", "postings", POSTINGS_CSV.read_bytes())
    print(f"  ok  hiring/postings.parquet ({receipt.rows} snapshot rows; +{len(rows)} for {today})")
    return 0


if __name__ == "__main__":
    sys.exit(snapshot())
