"""Tile + table export — silver geometry → PMTiles (map) + JSON (table fallback).

Reads the dbt-built DuckDB warehouse (transform/metrotrack.duckdb), writes two
GeoJSON layers, and runs tippecanoe to a single vector-tile PMTiles archive that
Vercel serves statically (no tile server, ADR/CLAUDE.md). Also emits a small JSON
the Astro page renders as an accessible, no-JS data table and uses to frame the map.

Run after `dbt build`:  python pipeline/tiles.py
Requires tippecanoe on PATH (`brew install tippecanoe`).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import duckdb

try:  # dual-mode: `python -m pipeline.tiles` vs `python pipeline/tiles.py`
    from . import cli
except ImportError:  # pragma: no cover
    import cli

REPO = Path(__file__).resolve().parent.parent
DUCKDB = REPO / "transform" / "metrotrack.duckdb"

# Per-metro outputs — the contract the frontend reads (frontend/src/lib/metros.ts):
# PMTiles at public/<slug>/transit.pmtiles, table JSON at src/data/<slug>/transit.json.
# One archive per metro, served static off Vercel — no tile server. [B11a, I3a]
def pmtiles_out(slug: str) -> Path:
    return REPO / "frontend" / "public" / slug / "transit.pmtiles"


def json_out(slug: str) -> Path:
    return REPO / "frontend" / "src" / "data" / slug / "transit.json"


# Size cap [I4]: fail loud if an archive blows the budget. Chicago is ~1.3 MB; this
# is a generous ceiling that keeps us well inside Vercel static limits + free tile
# bandwidth while leaving room for denser metros.
# ponytail: total-archive cap only; the dense-metro case (NYC) tightens per-feature
# drop flags when it actually exceeds this — that work is scheduled in v2.4 [I4].
MAX_PMTILES_MB = 50


def _features(con: duckdb.DuckDBPyConnection, sql: str, props: list[str],
              params: list | None = None) -> list[dict]:
    rows = con.execute(sql, params or []).fetchall()
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


def export(metro) -> None:
    """Build <slug>'s PMTiles + table JSON from the metro's gold rows only. [B5a, H2a]"""
    slug = metro.slug
    if not DUCKDB.exists():
        sys.exit(f"missing {DUCKDB} — run `cd transform && dbt build` first")

    con = duckdb.connect(str(DUCKDB), read_only=True)
    con.execute("install spatial; load spatial;")

    # Every query filters on metro_id so one warehouse serves N metros without bleed.
    routes = _features(
        con,
        """
        select authority_id, route_id, short_name, long_name, route_type, mode, color,
               ST_AsGeoJSON(geom) as g
        from silver_routes
        where metro_id = ? and geom is not null and not st_isempty(geom)
        order by authority_id, route_id
        """,
        ["authority_id", "route_id", "short_name", "long_name", "route_type", "mode", "color"],
        [slug],
    )
    stops = _features(
        con,
        """
        select authority_id, stop_id, name, mode, ST_AsGeoJSON(geom) as g
        from silver_stops
        where metro_id = ?
        order by authority_id, stop_id
        """,
        ["authority_id", "stop_id", "name", "mode"],
        [slug],
    )
    # Hex choropleth: jobs + population per H3 cell. Geometry is stored as WKT in
    # gold, so rebuild it for ST_AsGeoJSON (same path the Supabase loader uses).
    # Join on (metro_id, h3) so a cell only ever meets its own metro's access score.
    # cbd_min = straight-line best-case minutes to the nearest CBD (v3.10 TOD overlay).
    hexes = _features(
        con,
        """
        select m.h3, m.jobs, m.population,
               coalesce(a.jobs_reachable_walk, 0) as access,
               coalesce(t.min_to_cbd, 0) as cbd_min,
               ST_AsGeoJSON(ST_GeomFromText(m.geom_wkt)) as g
        from gold_hex_metrics m
        left join gold_hex_access a on a.metro_id = m.metro_id and a.h3 = m.h3
        left join gold_hex_tod    t on t.metro_id = m.metro_id and t.h3 = m.h3
        where m.metro_id = ?
        order by m.h3
        """,
        ["h3", "jobs", "population", "access", "cbd_min"],
        [slug],
    )
    # CBD anchors (v3.10) — the time-to-CBD map marker + the page's district list.
    cbds = _features(
        con,
        "select cbd_id, name, ST_AsGeoJSON(ST_GeomFromText(geom_wkt)) as g "
        "from gold_cbds where metro_id = ? order by cbd_id",
        ["cbd_id", "name"],
        [slug],
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
            f"select quantile_cont({m}, [0.2,0.4,0.6,0.8]) "
            "from gold_hex_metrics where metro_id = ?", [slug]
        ).fetchone()[0])
        for m in ("jobs", "population")
    }
    # Access score lives in gold_hex_access (walkshed reachable jobs); its breaks too.
    breaks["access"] = _ascending(con.execute(
        "select quantile_cont(jobs_reachable_walk, [0.2,0.4,0.6,0.8]) "
        "from gold_hex_access where metro_id = ?", [slug]
    ).fetchone()[0])
    # Time-to-CBD breaks (minutes) for the TOD overlay + legend (v3.10).
    breaks["cbd_time"] = _ascending(con.execute(
        "select quantile_cont(min_to_cbd, [0.2,0.4,0.6,0.8]) "
        "from gold_hex_tod where metro_id = ?", [slug]
    ).fetchone()[0])
    # Bounding box across this metro's stops, to frame the initial map view.
    bbox = con.execute(
        "select min(lon), min(lat), max(lon), max(lat) from silver_stops where metro_id = ?",
        [slug],
    ).fetchone()
    con.close()

    pmtiles, json_path = pmtiles_out(slug), json_out(slug)
    pmtiles.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as d:
        rp = Path(d) / "routes.geojson"
        sp = Path(d) / "stops.geojson"
        hp = Path(d) / "hex.geojson"
        cp = Path(d) / "cbds.geojson"
        rp.write_text(json.dumps({"type": "FeatureCollection", "features": routes}))
        sp.write_text(json.dumps({"type": "FeatureCollection", "features": stops}))
        hp.write_text(json.dumps({"type": "FeatureCollection", "features": hexes}))
        cp.write_text(json.dumps({"type": "FeatureCollection", "features": cbds}))
        subprocess.run(
            [
                "tippecanoe", "-o", str(pmtiles), "-f",
                "-L", f"routes:{rp}", "-L", f"stops:{sp}", "-L", f"hex:{hp}",
                "-L", f"cbds:{cp}",
                # -Z5..-z14 bounds zoom (the per-zoom limit, [B11a]); below z5 the
                # whole metro is a few pixels, above z14 adds bytes without detail.
                "-Z5", "-z14",
                # ponytail: keep every feature (no drops) — the hex choropleth must
                # stay gapless. A dense metro that exceeds MAX_PMTILES_MB tightens
                # these (drop-densest, lower z) in v2.4 [I4]; cap assert below is the
                # tripwire that forces that.
                "--no-feature-limit", "--no-tile-size-limit",
                "--extend-zooms-if-still-dropping",
            ],
            check=True,
        )

    size_mb = pmtiles.stat().st_size / 1_048_576
    if size_mb > MAX_PMTILES_MB:
        sys.exit(
            f"{pmtiles.relative_to(REPO)} is {size_mb:.1f} MB > {MAX_PMTILES_MB} MB cap "
            f"[I4] — drop densest features or lower max zoom for '{slug}'"
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

    json_path.write_text(json.dumps({
        "bbox": list(bbox),
        "routes": [r["properties"] for r in routes],
        "stopCounts": stop_counts,
        "stopTotal": len(stops),
        "hex": {
            "count": len(hexes),
            "breaks": breaks,                       # {jobs, population, access, cbd_time: [..4..]}
            "topJobs": _top("jobs"),
            "topPopulation": _top("population"),
            "topAccess": _top("access"),
        },
        # CBD anchors for the TOD time-to-CBD overlay marker + legend (v3.10).
        "cbds": [{**c["properties"],
                  "lon": c["geometry"]["coordinates"][0],
                  "lat": c["geometry"]["coordinates"][1]} for c in cbds],
    }, indent=2) + "\n")
    print(f"  ok  {pmtiles.relative_to(REPO)} ({size_mb * 1024:.0f} KB)")
    print(f"  ok  {json_path.relative_to(REPO)} "
          f"({len(routes)} routes, {len(stops)} stops, {len(hexes)} hexes)")


def dry_run(metro) -> "cli.DryRunReport":
    """Validate geo/FIPS + report whether the gold warehouse and tippecanoe are present."""
    report = cli.DryRunReport(metro.slug, "tiles")
    for c in cli.geo_checks(metro):
        report.checks.append(c)
    report.add("gold duckdb", "pass" if DUCKDB.exists() else "fail",
               DUCKDB.as_posix() if DUCKDB.exists() else f"missing {DUCKDB.as_posix()} (run dbt build)")
    tip = shutil.which("tippecanoe")
    report.add("tippecanoe", "pass" if tip else "fail",
               tip or "not on PATH (`brew install tippecanoe`)")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = cli.add_metro_args(argparse.ArgumentParser(description=__doc__))
    args = ap.parse_args(argv)
    metro = cli.resolve_metro(args.metro)
    if args.dry_run:
        report = dry_run(metro)
        print(report.render())
        return 0 if report.ok else 1
    if not shutil.which("tippecanoe"):
        sys.exit("tippecanoe not found on PATH — `brew install tippecanoe`")
    export(metro)
    return 0


if __name__ == "__main__":
    sys.exit(main())
