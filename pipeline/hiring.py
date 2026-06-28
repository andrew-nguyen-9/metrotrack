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

import argparse
import csv
import io
import json
import re
import sys
from datetime import date

try:  # dual-mode: `python -m pipeline.hiring` vs `python pipeline/hiring.py`
    from . import bronze, cli
except ImportError:  # pragma: no cover
    import bronze
    import cli


def postings_csv(metro):
    """The per-metro append-safe snapshot log under this metro's bronze."""
    return cli.bronze_dir(metro.slug, "hiring") / "postings.csv"


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


def _count_for(method: str, url: str) -> int:
    """Dispatch one agency's hiring signal by its applicant-tracking-system method."""
    if method == "taleo":
        return parse_taleo_count(_render_text(url, "text=Job Openings"))
    if method == "cadient":
        return count_cadient_titles(
            _render_links(url, r"jobDetail|postingDetail|seq=postingView|viewPosting"))
    if method == "oracle":
        return parse_oracle_count(_fetch_url(url, "application/json"))
    raise ValueError(f"unknown hiring method {method!r}")


def _agency_hiring(metro):
    """Yield (agency_id, method, url) for every agency that configures a hiring source."""
    for a in metro.agencies:
        h = a.raw.get("hiring") or {}
        method, url = h.get("method"), h.get("url")
        if method and url:
            yield a.id, method, url


def _gather(metro) -> list[dict]:
    """Best-effort: a source that fails is skipped this run (logged), not fatal."""
    rows: list[dict] = []
    for agency_id, method, url in _agency_hiring(metro):
        try:
            n = _count_for(method, url)
            rows.append({"authority_id": agency_id, "open_postings": n,
                         "source_url": url, "method": method})
        except Exception as e:  # noqa: BLE001 — resilience is the point
            print(f"  skip {agency_id}: {e}", file=sys.stderr)
    return rows


def dry_run(metro, *, check_network: bool = True) -> "cli.DryRunReport":
    """Validate geo/FIPS and probe each agency's hiring source. [H20a]"""
    report = cli.DryRunReport(metro.slug, "hiring")
    for c in cli.geo_checks(metro):
        report.checks.append(c)
    for agency_id, method, url in _agency_hiring(metro):
        name = f"hiring:{agency_id} ({method})"
        report.checks.append(cli.reach(name, url) if check_network
                             else cli.Check(name, "pass", url))
    return report


def snapshot(metro, today: str | None = None) -> int:
    today = today or date.today().isoformat()
    rows = _gather(metro)
    if not rows:
        sys.exit("no sources reachable — nothing to snapshot")
    csv_path = postings_csv(metro)
    existing = csv_path.read_bytes() if csv_path.exists() else b""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_bytes(append_snapshot(existing, rows, today))
    receipt = bronze.ingest_csv("hiring", "postings", csv_path.read_bytes(), metro=metro.slug)
    print(f"  ok  {metro.slug}/hiring/postings.parquet "
          f"({receipt.rows} snapshot rows; +{len(rows)} for {today})")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = cli.add_metro_args(argparse.ArgumentParser(description=__doc__))
    args = ap.parse_args(argv)
    metro = cli.resolve_metro(args.metro)
    if args.dry_run:
        report = dry_run(metro)
        print(report.render())
        return 0 if report.ok else 1
    return snapshot(metro)


if __name__ == "__main__":
    sys.exit(main())
