"""Demographics export — gold_demographic_change → frontend/src/data/<slug>/demographics.json.

Mirrors tiles.py / funding_export.py: reads the dbt-built warehouse and dumps the
tidy demographic-change figures the page renders honestly (every figure dated +
sourced). Ships the county headline, the per-tract population-change distribution
(the chart), and the biggest movers — not all ~1,300 tract rows (bundle size).

Run after `dbt build`:  python pipeline/demographics_export.py --metro chicago
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb

try:  # dual-mode: `python -m pipeline.demographics_export` vs direct script
    from . import cli
except ImportError:  # pragma: no cover
    import cli

REPO = Path(__file__).resolve().parent.parent
DUCKDB = REPO / "transform" / "metrotrack.duckdb"


def json_out(slug: str) -> Path:
    return REPO / "frontend" / "src" / "data" / slug / "demographics.json"


# Source citations — the receipts behind every number (docs/architecture/DATA_SOURCES.md).
SOURCE = {
    "label": "US Census Bureau — American Community Survey (ACS) 5-year estimates, table-based Summary File",
    "note": "Tables B01003 (total population) and B19013 (median household income), tract + county rollup for Cook County, IL. Median income is nominal (not inflation-adjusted).",
    "url": "https://www.census.gov/programs-surveys/acs/data/summary-file.html",
}

# Tract population-change buckets (the distribution the page charts). Ascending;
# each row is (label, lower %, upper %) — lower/upper null = open-ended.
BUCKETS = [
    ("Strong decline (≤ -10%)", None, -10.0),
    ("Decline (-10% to -3%)", -10.0, -3.0),
    ("Roughly stable (±3%)", -3.0, 3.0),
    ("Growth (+3% to +10%)", 3.0, 10.0),
    ("Strong growth (≥ +10%)", 10.0, None),
]


def export(metro) -> None:
    if not DUCKDB.exists():
        sys.exit(f"missing {DUCKDB} — run `cd transform && dbt build` first")
    slug = metro.slug
    con = duckdb.connect(str(DUCKDB), read_only=True)

    row = con.execute(
        "select year_prior, year_latest, pop_prior, pop_latest, pop_change, pop_change_pct, "
        "income_prior, income_latest, income_change from gold_demographic_change "
        "where metro_id = ? and geo_level = 'county'", [slug],
    ).fetchone()
    if row is None:
        con.close()
        sys.exit(f"no county row in gold_demographic_change for metro '{slug}'")
    cols = ["year_prior", "year_latest", "pop_prior", "pop_latest", "pop_change",
            "pop_change_pct", "income_prior", "income_latest", "income_change"]
    county = dict(zip(cols, row))

    buckets = []
    for label, lo, hi in BUCKETS:
        conds = ["geo_level = 'tract'", "metro_id = ?", "pop_change_pct is not null"]
        params: list = [slug]
        if lo is not None:
            conds.append("pop_change_pct >= ?"); params.append(lo)
        if hi is not None:
            conds.append("pop_change_pct < ?"); params.append(hi)
        n = con.execute(
            f"select count(*) from gold_demographic_change where {' and '.join(conds)}", params,
        ).fetchone()[0]
        buckets.append({"label": label, "count": n})

    # Biggest movers by absolute population change (5 up, 5 down) — a human-readable
    # anchor for the table fallback without shipping every tract.
    movers = con.execute(
        "select geoid, pop_prior, pop_latest, pop_change, pop_change_pct from "
        "gold_demographic_change where metro_id = ? and geo_level = 'tract' "
        "order by pop_change desc limit 5", [slug],
    ).fetchall()
    movers += con.execute(
        "select geoid, pop_prior, pop_latest, pop_change, pop_change_pct from "
        "gold_demographic_change where metro_id = ? and geo_level = 'tract' "
        "order by pop_change asc limit 5", [slug],
    ).fetchall()
    tract_total = con.execute(
        "select count(*) from gold_demographic_change where metro_id = ? and geo_level = 'tract'",
        [slug],
    ).fetchone()[0]
    con.close()

    mcols = ["geoid", "pop_prior", "pop_latest", "pop_change", "pop_change_pct"]
    movers = [dict(zip(mcols, m)) for m in movers]

    out = json_out(slug)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "vintages": {"prior": county["year_prior"], "latest": county["year_latest"]},
        "source": SOURCE,
        "county": county,
        "tractTotal": tract_total,
        "buckets": buckets,
        "movers": movers,
    }, indent=2) + "\n")
    print(f"  ok  {out.relative_to(REPO)} (county + {len(buckets)} buckets, {tract_total} tracts)")


def main(argv: list[str] | None = None) -> int:
    ap = cli.add_metro_args(argparse.ArgumentParser(description=__doc__), dry_run=False)
    args = ap.parse_args(argv)
    export(cli.resolve_metro(args.metro))
    return 0


if __name__ == "__main__":
    sys.exit(main())
