"""Stop-pairs export — gold_stop_pairs → frontend/src/data/<slug>/stop_pairs.json. [v3.7]

Mirrors tod_export/funding_export: reads the dbt-built warehouse and dumps the
ranked cross-agency service-coordination candidates the recommendations page
renders — the top pairs by score, each with distance, per-agency representative
headway, expected transfer wait, and a one-line rationale. Every figure is
traceable (docs/architecture/DATA_SOURCES.md, SourceTag id `coordination`); no
geometry travels here (the table needs none), so the JSON stays small.

Run after `dbt build`:  python pipeline/stop_pairs_export.py --metro chicago
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import duckdb

try:  # dual-mode
    from . import cli
except ImportError:  # pragma: no cover
    import cli

REPO = Path(__file__).resolve().parent.parent
DUCKDB = REPO / "transform" / "metrotrack.duckdb"

# How many ranked candidates the page lists. The full set lives in gold; the page
# is a shortlist, so we serve the strongest N (score desc). ponytail: a constant,
# not a knob — bump it if the page ever wants more.
TOP_N = 40

AGENCY = {"cta": "CTA", "metra": "Metra", "pace": "Pace"}
MODE = {"bus": "bus", "rail": "rail", "commuter-rail": "commuter rail", "multi": "bus/rail"}


def json_out(slug: str) -> Path:
    return REPO / "frontend" / "src" / "data" / slug / "stop_pairs.json"


def _rationale(r: dict) -> str:
    a, b = AGENCY.get(r["authority_a"], r["authority_a"]), AGENCY.get(r["authority_b"], r["authority_b"])
    ma, mb = MODE.get(r["mode_a"], r["mode_a"]), MODE.get(r["mode_b"], r["mode_b"])
    return (
        f"{r['dist_m']} m apart — {a} {ma} (~{r['headway_a']} min) beside "
        f"{b} {mb} (~{r['headway_b']} min); ~{r['wait_min']:g} min typical transfer wait "
        f"if the timetables stay uncoordinated."
    )


def export(metro) -> None:
    slug = metro.slug
    if not DUCKDB.exists():
        sys.exit(f"missing {DUCKDB} — run `cd transform && dbt build` first")

    con = duckdb.connect(str(DUCKDB), read_only=True)
    total = con.execute(
        "select count(*) from gold_stop_pairs where metro_id = ?", [slug]
    ).fetchone()[0]

    cols = [
        "authority_a", "stop_a", "name_a", "mode_a",
        "authority_b", "stop_b", "name_b", "mode_b",
        "dist_m", "headway_a", "headway_b", "headway_gap_min", "wait_min", "score",
    ]
    rows = con.execute(
        f"select {', '.join(cols)} from gold_stop_pairs where metro_id = ? "
        f"order by score desc, dist_m asc limit ?",
        [slug, TOP_N],
    ).fetchall()
    pairs = [dict(zip(cols, r)) for r in rows]

    headways = [
        {"authority_id": r[0], "headwayMin": r[1], "service": r[2], "sourceUrl": r[3]}
        for r in con.execute(
            "select authority_id, headway_min, service, source_url from service_headways "
            "order by headway_min"
        ).fetchall()
    ]
    con.close()

    for p in pairs:
        p["rationale"] = _rationale(p)

    JSON_OUT = json_out(slug)
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps({
        "asOf": date.today().isoformat(),
        "radiusM": 400,  # matches dbt var pair_radius_m (transform/dbt_project.yml)
        "candidateCount": total,
        "shown": len(pairs),
        "headways": headways,
        "pairs": pairs,
    }, indent=2) + "\n")
    print(f"  ok  {JSON_OUT.relative_to(REPO)} "
          f"({total} candidate pair(s), top {len(pairs)} shown)")


def main(argv: list[str] | None = None) -> int:
    ap = cli.add_metro_args(argparse.ArgumentParser(description=__doc__), dry_run=False)
    args = ap.parse_args(argv)
    export(cli.resolve_metro(args.metro))
    return 0


if __name__ == "__main__":
    sys.exit(main())
