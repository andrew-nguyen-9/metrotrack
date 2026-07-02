"""Funding export — gold_funding → frontend/src/data/funding.json.

Mirrors tiles.py's JSON write: reads the dbt-built DuckDB warehouse and dumps the
tidy funding rows plus source citations the page renders honestly (every figure
shows its source + as-of). The ECharts island + the no-JS table both read this file.

Run after `dbt build`:  python pipeline/funding_export.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parent.parent
DUCKDB = REPO / "transform" / "metrotrack.duckdb"
JSON_OUT = REPO / "frontend" / "src" / "data" / "funding.json"

# Source citations — the receipts behind every number (data/bronze/rta/SOURCE.md,
# docs/architecture/DATA_SOURCES.md). Rendered on the page so figures are dated.
SOURCES = {
    "actual": {
        "label": "Audited operating expense — FTA National Transit Database",
        "asOf": "FY2024 (latest published)",
        "url": "https://data.transportation.gov/Public-Transit/NTD-Annual-Data-View-Metrics-by-Agency-/g27i-aq2u",
    },
    "rta": {
        "label": "RTA Adopted 2025 Operating Budget, Table 2 (in thousands)",
        "asOf": "Adopted Dec 2024; accessed 2026-06-27",
        "url": "https://www.rtachicago.org/uploads/files/general/Transit-Funding/2025Budget/2025_RegionalBudgetAdopted.pdf",
    },
}


def export() -> None:
    if not DUCKDB.exists():
        sys.exit(f"missing {DUCKDB} — run `cd transform && dbt build` first")

    con = duckdb.connect(str(DUCKDB), read_only=True)
    cols = ["authority_id", "fiscal_year", "actual_audited", "fare_revenue",
            "unlinked_trips", "rta_kind", "rta_amount", "farebox_recovery",
            "subsidy", "subsidy_per_rider", "cost_per_rider"]
    rows = con.execute(
        f"select {', '.join(cols)} from gold_funding order by authority_id, fiscal_year"
    ).fetchall()
    con.close()

    records = [dict(zip(cols, r)) for r in rows]

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps({
        "sources": SOURCES,
        "rows": records,
    }, indent=2) + "\n")
    print(f"  ok  {JSON_OUT.relative_to(REPO)} ({len(records)} funding rows)")


if __name__ == "__main__":
    export()
