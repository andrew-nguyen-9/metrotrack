"""Tile + table export — silver geometry → PMTiles (map) + JSON (table fallback).

Reads the dbt-built DuckDB warehouse (transform/metrotrack.duckdb), writes two
GeoJSON layers, and runs tippecanoe to a single vector-tile PMTiles archive that
Vercel serves statically (no tile server, ADR/CLAUDE.md). Also emits a small JSON
the Astro page renders as an accessible, no-JS data table and uses to frame the map.

Run after `dbt build`:  python pipeline/tiles.py
Requires tippecanoe on PATH (`brew install tippecanoe`).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parent.parent
DUCKDB = REPO / "transform" / "metrotrack.duckdb"
PMTILES_OUT = REPO / "frontend" / "public" / "transit.pmtiles"
JSON_OUT = REPO / "frontend" / "src" / "data" / "transit.json"


def _features(con: duckdb.DuckDBPyConnection, sql: str, props: list[str]) -> list[dict]:
    rows = con.execute(sql).fetchall()
    cols = [c[0] for c in con.description]
    gi = cols.index("g")
    out = []
    for r in rows:
        record = dict(zip(cols, r))
        out.append({
            "type": "Feature",
            "geometry": json.loads(r[gi]),
            "properties": {p: record[p] for p in props},
        })
    return out


def export() -> None:
    if not DUCKDB.exists():
        sys.exit(f"missing {DUCKDB} — run `cd transform && dbt build` first")

    con = duckdb.connect(str(DUCKDB), read_only=True)
    con.execute("install spatial; load spatial;")

    routes = _features(
        con,
        """
        select authority_id, route_id, short_name, long_name, route_type, color,
               ST_AsGeoJSON(geom) as g
        from silver_routes
        where geom is not null and not st_isempty(geom)
        order by authority_id, route_id
        """,
        ["authority_id", "route_id", "short_name", "long_name", "route_type", "color"],
    )
    stops = _features(
        con,
        """
        select authority_id, stop_id, name, ST_AsGeoJSON(geom) as g
        from silver_stops
        order by authority_id, stop_id
        """,
        ["authority_id", "stop_id", "name"],
    )
    # Bounding box across all stops, to frame the initial map view.
    bbox = con.execute(
        "select min(lon), min(lat), max(lon), max(lat) from silver_stops"
    ).fetchone()
    con.close()

    PMTILES_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as d:
        rp = Path(d) / "routes.geojson"
        sp = Path(d) / "stops.geojson"
        rp.write_text(json.dumps({"type": "FeatureCollection", "features": routes}))
        sp.write_text(json.dumps({"type": "FeatureCollection", "features": stops}))
        subprocess.run(
            [
                "tippecanoe", "-o", str(PMTILES_OUT), "-f",
                "-L", f"routes:{rp}", "-L", f"stops:{sp}",
                "-Z5", "-z14",
                "--drop-densest-as-needed", "--extend-zooms-if-still-dropping",
            ],
            check=True,
        )

    # Table fallback: full route list + per-authority stop counts (a 960-row stop
    # table would not be legible; the map is the primary surface for stops).
    stop_counts: dict[str, int] = {}
    for s in stops:
        a = s["properties"]["authority_id"]
        stop_counts[a] = stop_counts.get(a, 0) + 1

    JSON_OUT.write_text(json.dumps({
        "bbox": list(bbox),
        "routes": [r["properties"] for r in routes],
        "stopCounts": stop_counts,
        "stopTotal": len(stops),
    }, indent=2) + "\n")
    print(f"  ok  {PMTILES_OUT.relative_to(REPO)} ({PMTILES_OUT.stat().st_size // 1024} KB)")
    print(f"  ok  {JSON_OUT.relative_to(REPO)} ({len(routes)} routes, {len(stops)} stops)")


if __name__ == "__main__":
    if not shutil.which("tippecanoe"):
        sys.exit("tippecanoe not found on PATH — `brew install tippecanoe`")
    export()
