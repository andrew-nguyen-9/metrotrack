"""Ridership export — gold_ridership_* → frontend/src/data/<slug>/ridership.json.

Mirrors funding_export/tiles: reads the dbt-built DuckDB warehouse and dumps the
figures the page renders honestly. Aggregation lives here (not on the client) so the
served JSON is small: a monthly bus-vs-rail trend, plus latest-month rankings by line
(bus route) and by stop ('L' station). Every figure carries its source + as-of.

Run after `dbt build`:  python pipeline/ridership_export.py [--metro chicago]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb

try:  # dual-mode
    from . import cli
except ImportError:  # pragma: no cover
    import cli

REPO = Path(__file__).resolve().parent.parent
DUCKDB = REPO / "transform" / "metrotrack.duckdb"

# Source citations — the receipts behind every number (docs/architecture/DATA_SOURCES.md).
SOURCES = {
    "line": {
        "label": "CTA — Ridership, Bus Routes, Monthly Day-Type Averages & Totals (Chicago Data Portal)",
        "url": "https://data.cityofchicago.org/Transportation/CTA-Ridership-Bus-Routes-Monthly-Day-Type-Averages/bynn-gwxy",
        "note": "Monthly total boardings per bus route. A route is a line, so this is ridership by line.",
    },
    "stop": {
        "label": "CTA — Ridership, 'L' Station Entries, Monthly Day-Type Averages & Totals (Chicago Data Portal)",
        "url": "https://data.cityofchicago.org/Transportation/CTA-Ridership-L-Station-Entries-Monthly-Day-Type-A/t2rn-p8d7",
        "note": "Monthly total entries per rail station. A station is a stop, so this is ridership by stop.",
    },
}


def out_path(slug: str) -> Path:
    return REPO / "frontend" / "src" / "data" / slug / "ridership.json"


def export(slug: str) -> None:
    if not DUCKDB.exists():
        sys.exit(f"missing {DUCKDB} — run `cd transform && dbt build` first")

    con = duckdb.connect(str(DUCKDB), read_only=True)

    # Monthly bus-vs-rail totals (the trend chart). Union the two grains, sum per month.
    trend = con.execute("""
        with m as (
            select month, sum(rides) as rides from gold_ridership_line where metro_id = ? group by month
        ), r as (
            select month, sum(rides) as rides from gold_ridership_stop where metro_id = ? group by month
        )
        select cast(coalesce(m.month, r.month) as varchar) as month,
               coalesce(m.rides, 0) as bus, coalesce(r.rides, 0) as rail
        from m full outer join r using (month) order by month
    """, [slug, slug]).fetchall()

    latest_line = con.execute(
        "select max(month) from gold_ridership_line where metro_id = ?", [slug]).fetchone()[0]
    latest_stop = con.execute(
        "select max(month) from gold_ridership_stop where metro_id = ?", [slug]).fetchone()[0]

    # Latest-month rankings (by line, by stop). Rides > 0 only (drop discontinued).
    by_line = con.execute("""
        select route, any_value(route_name) as route_name, rides
        from gold_ridership_line where metro_id = ? and month = ? and rides > 0
        group by route, rides order by rides desc
    """, [slug, latest_line]).fetchall() if latest_line else []
    by_stop = con.execute("""
        select station_id, any_value(station_name) as station_name, rides
        from gold_ridership_stop where metro_id = ? and month = ? and rides > 0
        group by station_id, rides order by rides desc
    """, [slug, latest_stop]).fetchall() if latest_stop else []
    con.close()

    payload = {
        "sources": SOURCES,
        "latestMonth": {"line": str(latest_line) if latest_line else None,
                        "stop": str(latest_stop) if latest_stop else None},
        "trend": [{"month": m, "bus": b, "rail": r} for (m, b, r) in trend],
        "byLine": [{"route": rt, "route_name": rn, "rides": n} for (rt, rn, n) in by_line],
        "byStop": [{"station_id": s, "station_name": sn, "rides": n} for (s, sn, n) in by_stop],
    }

    out = out_path(slug)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"  ok  {out.relative_to(REPO)} "
          f"({len(payload['trend'])} months, {len(by_line)} routes, {len(by_stop)} stations)")


def main(argv: list[str] | None = None) -> int:
    ap = cli.add_metro_args(argparse.ArgumentParser(description=__doc__), dry_run=False)
    export(cli.resolve_metro(ap.parse_args(argv).metro).slug)
    return 0


if __name__ == "__main__":
    sys.exit(main())
