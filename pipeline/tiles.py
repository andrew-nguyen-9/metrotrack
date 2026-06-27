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
    # Hex choropleth: jobs + population per H3 cell. Geometry is stored as WKT in
    # gold, so rebuild it for ST_AsGeoJSON (same path the Supabase loader uses).
    hexes = _features(
        con,
        """
        select h3, jobs, population,
               ST_AsGeoJSON(ST_GeomFromText(geom_wkt)) as g
        from gold_hex_metrics
        order by h3
        """,
        ["h3", "jobs", "population"],
    )
    # Quintile break points (4 thresholds → 5 bins) for the choropleth + legend.
    # Computed here so the client ships no break math and the legend is exact.
    # MapLibre's `step` expression requires strictly-ascending stops, so force
    # that here — on sparse data (or a coarser geography) quantiles can tie, which
    # would otherwise throw and blank the whole map.
    def _ascending(vals: list[float]) -> list[int]:
        out: list[int] = []
        for v in vals:
            n = round(v)
            out.append(max(n, out[-1] + 1) if out else n)
        return out

    breaks = {
        m: _ascending(con.execute(
            f"select quantile_cont({m}, [0.2,0.4,0.6,0.8]) from gold_hex_metrics"
        ).fetchone()[0])
        for m in ("jobs", "population")
    }
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
        hp = Path(d) / "hex.geojson"
        rp.write_text(json.dumps({"type": "FeatureCollection", "features": routes}))
        sp.write_text(json.dumps({"type": "FeatureCollection", "features": stops}))
        hp.write_text(json.dumps({"type": "FeatureCollection", "features": hexes}))
        subprocess.run(
            [
                "tippecanoe", "-o", str(PMTILES_OUT), "-f",
                "-L", f"routes:{rp}", "-L", f"stops:{sp}", "-L", f"hex:{hp}",
                "-Z5", "-z14",
                # ponytail: sample data is small, so keep every feature (no drops) —
                # the hex choropleth must stay gapless. Revisit drop flags if the
                # full-network export blows past tile-size limits.
                "--no-feature-limit", "--no-tile-size-limit",
                "--extend-zooms-if-still-dropping",
            ],
            check=True,
        )

    # Table fallback: full route list + per-authority stop counts (a 960-row stop
    # table would not be legible; the map is the primary surface for stops).
    stop_counts: dict[str, int] = {}
    for s in stops:
        a = s["properties"]["authority_id"]
        stop_counts[a] = stop_counts.get(a, 0) + 1

    # Table fallback for the overlay: top cells by jobs + by population, so the
    # choropleth's data exists with zero JS.
    def _top(metric: str) -> list[dict]:
        return sorted(
            (h["properties"] for h in hexes),
            key=lambda p: p[metric], reverse=True,
        )[:10]

    JSON_OUT.write_text(json.dumps({
        "bbox": list(bbox),
        "routes": [r["properties"] for r in routes],
        "stopCounts": stop_counts,
        "stopTotal": len(stops),
        "hex": {
            "count": len(hexes),
            "breaks": breaks,                       # {jobs:[..4..], population:[..4..]}
            "topJobs": _top("jobs"),
            "topPopulation": _top("population"),
        },
    }, indent=2) + "\n")
    print(f"  ok  {PMTILES_OUT.relative_to(REPO)} ({PMTILES_OUT.stat().st_size // 1024} KB)")
    print(f"  ok  {JSON_OUT.relative_to(REPO)} "
          f"({len(routes)} routes, {len(stops)} stops, {len(hexes)} hexes)")


if __name__ == "__main__":
    if not shutil.which("tippecanoe"):
        sys.exit("tippecanoe not found on PATH — `brew install tippecanoe`")
    export()
