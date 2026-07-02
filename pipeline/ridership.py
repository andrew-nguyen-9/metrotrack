"""Ridership bronze loaders — CTA monthly ridership by bus route + by 'L' station.

Two key-free Chicago Data Portal (Socrata) datasets feed the ridership pillar
(docs/architecture/DATA_SOURCES.md), both structured + multi-year → fully
reproducible:

  • **By line** — CTA "Ridership — Bus Routes — Monthly Day-Type Averages & Totals"
    (`bynn-gwxy`). One row per bus route × month; `monthtotal` is the month's total
    boardings. A CTA bus route *is* a line, so this is ridership by line.
  • **By stop** — CTA "Ridership — 'L' Station Entries — Monthly Day-Type Averages &
    Totals" (`t2rn-p8d7`). One row per rail station × month; `monthtotal` is the
    month's total entries. A station is a stop, so this is ridership by stop.

Windowed to WINDOW_START forward (recent, rider-relevant, and keeps the committed
bronze receipt small) — the full series back to 2001 is available at the same URL.

Metra + Pace have **no free per-line/per-stop ridership feed** (their granular
numbers live in PDF monthly reports); the UI renders an honest "data coming" state
rather than a fabricated number. NTD annual system totals for all three boards are
already served on the funding pillar.

The pure `parse_*` functions trim each source to the columns silver needs, returning
clean CSV bytes; `bronze.ingest_csv` content-hashes them to parquet (idempotent, the
receipt). `fetch_*` does the network I/O and stays out of the no-network selftest.
"""
from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import os
import sys
import urllib.parse
import urllib.request

try:  # dual-mode: `python -m pipeline.ridership` vs `python pipeline/ridership.py`
    from . import bronze, cli
except ImportError:  # pragma: no cover
    import bronze
    import cli

# CTA-scoped Socrata datasets (Chicago Data Portal). A future metro adds its own
# dataset ids; only Chicago is live, and ridership ingests only for a metro that
# runs CTA. Anonymous works; SOCATRA_API_KEY (app token) only raises rate limits.
SOCRATA_HOST = "data.cityofchicago.org"
BUS_DATASET = "bynn-gwxy"   # bus routes, monthly day-type averages & totals
RAIL_DATASET = "t2rn-p8d7"  # 'L' station entries, monthly day-type averages & totals
WINDOW_START = "2021-01-01"  # recent window; full series back to 2001 at the same URL


def dataset_url(dataset: str) -> str:
    return f"https://{SOCRATA_HOST}/resource/{dataset}.json"


def _int(v) -> int:
    """Socrata sends numbers as strings; tolerate blanks/None/decimals."""
    if v is None or v == "":
        return 0
    return round(float(v))


def _month(v) -> str:
    """Socrata floating-timestamp (e.g. '2026-04-01T00:00:00.000') → 'YYYY-MM-DD'."""
    return str(v or "")[:10]


def parse_bus(raw_json: bytes) -> bytes:
    """Bus-route records → `authority_id,route,route_name,month,rides` (one row per route×month)."""
    rows = json.loads(raw_json)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["authority_id", "route", "route_name", "month", "rides"])
    for r in rows:
        route = str(r.get("route", "")).strip()
        if not route:
            continue
        w.writerow(["cta", route, str(r.get("routename", "")).strip(),
                    _month(r.get("month_beginning")), _int(r.get("monthtotal"))])
    return out.getvalue().encode()


def parse_rail(raw_json: bytes) -> bytes:
    """Station records → `authority_id,station_id,station_name,month,rides` (one row per station×month)."""
    rows = json.loads(raw_json)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["authority_id", "station_id", "station_name", "month", "rides"])
    for r in rows:
        sid = str(r.get("station_id", "")).strip()
        if not sid:
            continue
        w.writerow(["cta", sid, str(r.get("stationame", "")).strip(),
                    _month(r.get("month_beginning")), _int(r.get("monthtotal"))])
    return out.getvalue().encode()


def fetch(dataset: str) -> bytes:
    """Pull a dataset's recent window (SoQL). Key-free by default; the SOCATRA key +
    secret (new-style Socrata) raise rate limits via HTTP Basic Auth when both set."""
    query = urllib.parse.urlencode({
        "$where": f"month_beginning >= '{WINDOW_START}'",
        "$order": "month_beginning",
        "$limit": "50000",
    })
    headers = {"User-Agent": cli.UA}
    key, secret = os.environ.get("SOCATRA_API_KEY"), os.environ.get("SOCATRA_SECRET_KEY")
    if key and secret:
        token = base64.b64encode(f"{key}:{secret}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    req = urllib.request.Request(f"{dataset_url(dataset)}?{query}", headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _has_cta(metro) -> bool:
    return any(a.id == "cta" for a in metro.agencies)


def dry_run(metro, *, check_network: bool = True) -> "cli.DryRunReport":
    """Validate geo/FIPS + probe the two CTA ridership dataset URLs."""
    report = cli.DryRunReport(metro.slug, "ridership")
    for c in cli.geo_checks(metro):
        report.checks.append(c)
    if not _has_cta(metro):
        report.add("cta agency", "blocked", "no CTA agency configured — ridership skipped")
        return report
    for name, ds in (("bus_routes", BUS_DATASET), ("rail_stations", RAIL_DATASET)):
        report.checks.append(cli.reach(name, dataset_url(ds)) if check_network
                             else cli.Check(name, "pass", dataset_url(ds)))
    return report


def ingest(metro) -> int:
    """Fetch both CTA ridership datasets → per-metro content-hashed bronze."""
    if not _has_cta(metro):
        print(f"  --  {metro.slug}: no CTA agency — ridership skipped")
        return 0
    bus = bronze.ingest_csv("cta", "ridership_bus", parse_bus(fetch(BUS_DATASET)), metro=metro.slug)
    rail = bronze.ingest_csv("cta", "ridership_rail", parse_rail(fetch(RAIL_DATASET)), metro=metro.slug)
    print(f"  ok  {metro.slug}/cta/ridership_bus.parquet ({bus.rows} route-months)")
    print(f"  ok  {metro.slug}/cta/ridership_rail.parquet ({rail.rows} station-months)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = cli.add_metro_args(argparse.ArgumentParser(description=__doc__))
    args = ap.parse_args(argv)
    metro = cli.resolve_metro(args.metro)
    if args.dry_run:
        report = dry_run(metro)
        print(report.render())
        return 0 if report.ok else 1
    return ingest(metro)


if __name__ == "__main__":
    sys.exit(main())
