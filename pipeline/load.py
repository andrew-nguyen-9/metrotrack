"""Load gold → the Supabase spine (public.authorities/routes/stops). Idempotent.

Reads the dbt-built gold tables from transform/metrotrack.duckdb and upserts them
into Postgres (Project A). Geometry travels as WKT and is rebuilt with
ST_GeomFromText at SRID 4326; rows are replaced by their natural key, so a
re-run never duplicates. Inserts go through the direct Postgres connection (the
postgres role bypasses RLS) — never the client bundle.

Env: SUPABASE_A_DB_URL (postgresql://...). Run after `dbt build`.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb
import psycopg

REPO = Path(__file__).resolve().parent.parent
DUCKDB = REPO / "transform" / "metrotrack.duckdb"

ROUTE_UPSERT = """
insert into public.routes
  (authority_id, route_id, short_name, long_name, route_type, color, text_color, geom)
-- ST_Multi: a route with a single shape stitches to a LINESTRING, which the
-- MultiLineString column would reject; coerce it to MULTILINESTRING.
values (%s, %s, %s, %s, %s, %s, %s, extensions.ST_Multi(extensions.ST_GeomFromText(%s, 4326)))
on conflict (authority_id, route_id) do update set
  short_name = excluded.short_name,
  long_name  = excluded.long_name,
  route_type = excluded.route_type,
  color      = excluded.color,
  text_color = excluded.text_color,
  geom       = excluded.geom
"""

STOP_UPSERT = """
insert into public.stops (authority_id, stop_id, name, geom)
values (%s, %s, %s, extensions.ST_GeomFromText(%s, 4326))
on conflict (authority_id, stop_id) do update set
  name = excluded.name,
  geom = excluded.geom
"""

HEX_UPSERT = """
insert into public.hex_metrics
  (h3, resolution, jobs, population, jobs_per_1k_pop, geom)
values (%s, %s, %s, %s, %s, extensions.ST_GeomFromText(%s, 4326))
on conflict (h3) do update set
  resolution      = excluded.resolution,
  jobs            = excluded.jobs,
  population      = excluded.population,
  jobs_per_1k_pop = excluded.jobs_per_1k_pop,
  geom            = excluded.geom
"""


def main() -> int:
    db_url = os.environ.get("SUPABASE_A_DB_URL", "")
    if not db_url or "[" in db_url:  # unset or still the .env placeholder
        sys.exit("SUPABASE_A_DB_URL not set (or still a placeholder) — cannot load")
    if not DUCKDB.exists():
        sys.exit(f"missing {DUCKDB} — run `cd transform && dbt build` first")

    con = duckdb.connect(str(DUCKDB), read_only=True)
    routes = con.execute(
        "select authority_id, route_id, short_name, long_name, route_type, "
        "color, text_color, geom_wkt from gold_routes"
    ).fetchall()
    stops = con.execute(
        "select authority_id, stop_id, name, geom_wkt from gold_stops"
    ).fetchall()
    hexes = con.execute(
        "select h3, resolution, jobs, population, jobs_per_1k_pop, geom_wkt "
        "from gold_hex_metrics"
    ).fetchall()
    con.close()

    with psycopg.connect(db_url) as pg:
        with pg.cursor() as cur:
            cur.executemany(ROUTE_UPSERT, routes)
            cur.executemany(STOP_UPSERT, stops)
            cur.executemany(HEX_UPSERT, hexes)
        pg.commit()

    print(f"  ok  loaded {len(routes)} routes, {len(stops)} stops, "
          f"{len(hexes)} hex cells → Project A")
    return 0


if __name__ == "__main__":
    sys.exit(main())
