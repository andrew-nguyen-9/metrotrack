"""TOD export — gold_hex_tod + gold_cbds → frontend/src/data/<slug>/tod.json. [v3.10]

Mirrors funding_export/hiring_export: reads the dbt-built warehouse and dumps the
tidy figures the TOD page renders — density totals, real growth vs the prior
vintage, distance-to-CBD rings (the chart), and the data-driven CBD list. Every
figure is traceable (docs/architecture/DATA_SOURCES.md); no geometry travels here
(the map reads the PMTiles hex layer), so this JSON stays small.

Run after `dbt build`:  python pipeline/tod_export.py --metro chicago
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import duckdb

try:  # dual-mode
    from . import census, cli
except ImportError:  # pragma: no cover
    import census
    import cli

REPO = Path(__file__).resolve().parent.parent
DUCKDB = REPO / "transform" / "metrotrack.duckdb"


def json_out(slug: str) -> Path:
    return REPO / "frontend" / "src" / "data" / slug / "tod.json"


# Distance-to-nearest-CBD rings (km) for the concentration chart + table fallback.
RING_KM = [2, 5, 10, 20]


def export(metro) -> None:
    slug = metro.slug
    if not DUCKDB.exists():
        sys.exit(f"missing {DUCKDB} — run `cd transform && dbt build` first")

    con = duckdb.connect(str(DUCKDB), read_only=True)
    # Density = current-vintage totals. Growth compares each vintage's OWN regional
    # total (silver_hex_prior vs gold_hex_metrics), not the per-hex join — cell
    # membership can flip across decennial binning, so the independent totals are the
    # honest citywide change (per-hex growth lives in gold_hex_tod for the map).
    hex_count, jobs, pop = con.execute(
        "select count(*), sum(jobs), sum(population) from gold_hex_metrics where metro_id = ?",
        [slug],
    ).fetchone()
    jobs_prev, pop_prev = con.execute(
        "select sum(jobs_prev), sum(pop_prev) from silver_hex_prior where metro_id = ?",
        [slug],
    ).fetchone()

    cbds = [
        {"id": r[0], "name": r[1], "lat": r[2], "lon": r[3]}
        for r in con.execute(
            "select cbd_id, name, lat, lon from gold_cbds where metro_id = ? order by cbd_id",
            [slug],
        ).fetchall()
    ]

    # Distance rings: jobs + population + hex count within each band of the nearest CBD.
    edges = [0.0] + [k * 1000.0 for k in RING_KM] + [float("inf")]
    rings = []
    for lo, hi in zip(edges, edges[1:]):
        row = con.execute(
            "select count(*), coalesce(sum(jobs),0), coalesce(sum(population),0) "
            "from gold_hex_tod where metro_id = ? and dist_cbd_m >= ? and dist_cbd_m < ?",
            [slug, lo, hi],
        ).fetchone()
        label = f"≤{int(hi/1000)} km" if hi != float("inf") else f">{int(lo/1000)} km"
        rings.append({"label": label, "hexes": row[0], "jobs": row[1], "population": row[2]})
    con.close()

    c = metro.raw.get("census") or {}
    pct = lambda cur, prev: round(100.0 * (cur - prev) / prev, 1) if prev else None

    JSON_OUT = json_out(slug)
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps({
        "asOf": date.today().isoformat(),
        "cbds": cbds,
        "speedKmh": 24,  # matches dbt var cbd_speed_kmh (transform/dbt_project.yml)
        "density": {"hexCount": hex_count, "jobs": jobs, "population": pop},
        "growth": {
            "jobs": jobs, "jobsPrev": jobs_prev, "jobsGrowthPct": pct(jobs, jobs_prev),
            "population": pop, "popPrev": pop_prev, "popGrowthPct": pct(pop, pop_prev),
            "jobsYear": int(c.get("lodes_year", census.LODES_DEFAULT_YEAR)),
            "jobsPriorYear": int(c.get("lodes_prior_year")) if c.get("lodes_prior_year") else None,
            "popYear": 2020, "popPriorYear": census.CENPOP_PRIOR_YEAR,
        },
        "rings": rings,
    }, indent=2) + "\n")
    print(f"  ok  {JSON_OUT.relative_to(REPO)} "
          f"({hex_count} hexes, {len(cbds)} CBD(s), {len(rings)} rings)")


def main(argv: list[str] | None = None) -> int:
    ap = cli.add_metro_args(argparse.ArgumentParser(description=__doc__), dry_run=False)
    args = ap.parse_args(argv)
    export(cli.resolve_metro(args.metro))
    return 0


if __name__ == "__main__":
    sys.exit(main())
