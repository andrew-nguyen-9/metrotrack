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

FINANCE_UPSERT = """
insert into public.agency_finances
  (authority_id, fiscal_year, actual_audited, fare_revenue, unlinked_trips,
   rta_kind, rta_amount, farebox_recovery)
values (%s, %s, %s, %s, %s, %s, %s, %s)
on conflict (authority_id, fiscal_year) do update set
  actual_audited   = excluded.actual_audited,
  fare_revenue     = excluded.fare_revenue,
  unlinked_trips   = excluded.unlinked_trips,
  rta_kind         = excluded.rta_kind,
  rta_amount       = excluded.rta_amount,
  farebox_recovery = excluded.farebox_recovery
"""

VACANCY_UPSERT = """
insert into public.vacancy_postings
  (authority_id, as_of, open_postings, source_url, method)
values (%s, %s, %s, %s, %s)
on conflict (authority_id, as_of) do update set
  open_postings = excluded.open_postings,
  source_url    = excluded.source_url,
  method        = excluded.method
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
    finances = con.execute(
        "select authority_id, fiscal_year, actual_audited, fare_revenue, "
        "unlinked_trips, rta_kind, rta_amount, farebox_recovery from gold_funding"
    ).fetchall()
    vacancy = con.execute(
        "select authority_id, as_of, open_postings, source_url, method from gold_vacancy"
    ).fetchall()
    con.close()

    with psycopg.connect(db_url) as pg:
        with pg.cursor() as cur:
            cur.executemany(ROUTE_UPSERT, routes)
            cur.executemany(STOP_UPSERT, stops)
            cur.executemany(HEX_UPSERT, hexes)
            cur.executemany(FINANCE_UPSERT, finances)
            cur.executemany(VACANCY_UPSERT, vacancy)
        pg.commit()

    print(f"  ok  loaded {len(routes)} routes, {len(stops)} stops, "
          f"{len(hexes)} hex cells, {len(finances)} finance rows, "
          f"{len(vacancy)} vacancy rows → Project A")
    return 0


if __name__ == "__main__":
    sys.exit(main())
