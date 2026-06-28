"""Hiring export — gold_vacancy → frontend/src/data/hiring.json.

Mirrors funding_export.py: reads the dbt-built warehouse and dumps the tidy weekly
open-postings rows + the source citation the page renders (every figure dated).

Run after `dbt build`:  python pipeline/hiring_export.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parent.parent
DUCKDB = REPO / "transform" / "metrotrack.duckdb"
JSON_OUT = REPO / "frontend" / "src" / "data" / "hiring.json"

SOURCE = {
    "label": "Each authority's public job listing — CTA (Taleo), Metra (Cadient), Pace (Oracle Recruiting)",
    "note": "Open postings listed, snapshotted weekly. This is hiring activity, not a vacancy rate or an understaffing measure.",
}


def export() -> None:
    if not DUCKDB.exists():
        sys.exit(f"missing {DUCKDB} — run `cd transform && dbt build` first")

    con = duckdb.connect(str(DUCKDB), read_only=True)
    rows = con.execute(
        "select authority_id, cast(as_of as varchar) as as_of, open_postings "
        "from gold_vacancy order by authority_id, as_of"
    ).fetchall()
    con.close()

    records = [{"authority_id": a, "as_of": d, "open_postings": n} for (a, d, n) in rows]
    as_of = max((r["as_of"] for r in records), default=None)

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps({
        "asOf": as_of,
        "source": SOURCE,
        "rows": records,
    }, indent=2) + "\n")
    print(f"  ok  {JSON_OUT.relative_to(REPO)} ({len(records)} vacancy rows)")


if __name__ == "__main__":
    export()
