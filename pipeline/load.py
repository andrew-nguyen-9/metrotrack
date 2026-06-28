"""Load gold → the Supabase spine. Idempotent, per-metro.

Reads the dbt-built gold tables from transform/metrotrack.duckdb and upserts them
into Postgres (Project A). Every row is tagged with --metro=<slug> (default
'chicago') and keyed on (metro_id, <natural_key>), so a re-run never duplicates
and metros never collide. Geometry travels as WKT and is rebuilt with
ST_GeomFromText at SRID 4326. `as_of` records the load date (data-as-of); v2.0.4
will refine it to the source's own as_of and populate source_hash from gold.
Inserts go through the direct Postgres connection (the postgres role bypasses
RLS) — never the client bundle.

Env: SUPABASE_A_DB_URL (postgresql://...). Run after `dbt build`.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

import duckdb
import psycopg

try:  # dual-mode: `python -m pipeline.load` vs `python pipeline/load.py`
    from . import cli
    from . import metros as metros_mod
except ImportError:  # pragma: no cover
    import cli
    import metros as metros_mod

REPO = Path(__file__).resolve().parent.parent
DUCKDB = REPO / "transform" / "metrotrack.duckdb"

# Mirror the serving subset of every metros/<slug>.toml into public.metros. bbox
# becomes an envelope polygon. Upsert by metro_id → re-runs never duplicate. [B2c]
METRO_UPSERT = """
insert into public.metros (metro_id, name, slug, tz, status, bbox, as_of)
values (%s, %s, %s, %s, %s, extensions.ST_MakeEnvelope(%s, %s, %s, %s, 4326), %s)
on conflict (metro_id) do update set
  name   = excluded.name,
  slug   = excluded.slug,
  tz     = excluded.tz,
  status = excluded.status,
  bbox   = excluded.bbox,
  as_of  = excluded.as_of
"""

ROUTE_UPSERT = """
insert into public.routes
  (metro_id, authority_id, route_id, short_name, long_name, route_type,
   color, text_color, geom, as_of)
-- ST_Multi: a route with a single shape stitches to a LINESTRING, which the
-- MultiLineString column would reject; coerce it to MULTILINESTRING.
values (%s, %s, %s, %s, %s, %s, %s, %s,
        extensions.ST_Multi(extensions.ST_GeomFromText(%s, 4326)), %s)
on conflict (metro_id, authority_id, route_id) do update set
  short_name = excluded.short_name,
  long_name  = excluded.long_name,
  route_type = excluded.route_type,
  color      = excluded.color,
  text_color = excluded.text_color,
  geom       = excluded.geom,
  as_of      = excluded.as_of
"""

STOP_UPSERT = """
insert into public.stops (metro_id, authority_id, stop_id, name, geom, as_of)
values (%s, %s, %s, %s, extensions.ST_GeomFromText(%s, 4326), %s)
on conflict (metro_id, authority_id, stop_id) do update set
  name  = excluded.name,
  geom  = excluded.geom,
  as_of = excluded.as_of
"""

HEX_UPSERT = """
insert into public.hex_metrics
  (metro_id, h3, resolution, jobs, population, jobs_per_1k_pop, geom, as_of)
values (%s, %s, %s, %s, %s, %s, extensions.ST_GeomFromText(%s, 4326), %s)
on conflict (metro_id, h3) do update set
  resolution      = excluded.resolution,
  jobs            = excluded.jobs,
  population      = excluded.population,
  jobs_per_1k_pop = excluded.jobs_per_1k_pop,
  geom            = excluded.geom,
  as_of           = excluded.as_of
"""

FINANCE_UPSERT = """
insert into public.agency_finances
  (metro_id, authority_id, fiscal_year, actual_audited, fare_revenue, unlinked_trips,
   rta_kind, rta_amount, farebox_recovery, as_of)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
on conflict (metro_id, authority_id, fiscal_year) do update set
  actual_audited   = excluded.actual_audited,
  fare_revenue     = excluded.fare_revenue,
  unlinked_trips   = excluded.unlinked_trips,
  rta_kind         = excluded.rta_kind,
  rta_amount       = excluded.rta_amount,
  farebox_recovery = excluded.farebox_recovery,
  as_of            = excluded.as_of
"""

# vacancy as_of is the snapshot's own date (part of the key), not the load date.
VACANCY_UPSERT = """
insert into public.vacancy_postings
  (metro_id, authority_id, as_of, open_postings, source_url, method)
values (%s, %s, %s, %s, %s, %s)
on conflict (metro_id, authority_id, as_of) do update set
  open_postings = excluded.open_postings,
  source_url    = excluded.source_url,
  method        = excluded.method
"""

ACCESS_UPSERT = """
insert into public.hex_access (metro_id, h3, jobs_reachable_walk, walk_radius_m, as_of)
values (%s, %s, %s, %s, %s)
on conflict (metro_id, h3) do update set
  jobs_reachable_walk = excluded.jobs_reachable_walk,
  walk_radius_m       = excluded.walk_radius_m,
  as_of               = excluded.as_of
"""


def _db_url() -> str:
    db_url = os.environ.get("SUPABASE_A_DB_URL", "")
    if not db_url or "[" in db_url:  # unset or still the .env placeholder
        sys.exit("SUPABASE_A_DB_URL not set (or still a placeholder) — cannot load")
    return db_url


def sync_metros(db_url: str | None = None) -> int:
    """Mirror every metros/<slug>.toml into public.metros. Idempotent (upsert by id)."""
    db_url = db_url or _db_url()
    today = date.today().isoformat()
    rows = []
    for slug in metros_mod.list_metros():
        m = metros_mod.load_metro(slug)  # validates; a bad config fails here, loudly
        rows.append((m.metro_id, m.name, m.slug, m.tz, m.status, *m.bbox, today))
    with psycopg.connect(db_url) as pg:
        with pg.cursor() as cur:
            cur.executemany(METRO_UPSERT, rows)
        pg.commit()
    print(f"  ok  synced {len(rows)} metro(s) → public.metros ({', '.join(r[0] for r in rows)})")
    return 0


def dry_run(metro) -> "cli.DryRunReport":
    """Validate geo/FIPS + report whether the gold warehouse + DB URL are present.

    No connection, no writes — this is the smoke check the loop reuses before a load.
    """
    report = cli.DryRunReport(metro.slug, "load")
    for c in cli.geo_checks(metro):
        report.checks.append(c)
    report.add("gold duckdb", "pass" if DUCKDB.exists() else "fail",
               DUCKDB.as_posix() if DUCKDB.exists() else f"missing {DUCKDB.as_posix()} (run dbt build)")
    db = os.environ.get("SUPABASE_A_DB_URL", "")
    db_ok = bool(db) and "[" not in db
    report.add("SUPABASE_A_DB_URL", "pass" if db_ok else "blocked",
               "set" if db_ok else "unset or placeholder (no DB write attempted)")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    cli.add_metro_args(ap)
    ap.add_argument("--metros", action="store_true",
                    help="Only sync the metros registry (no gold load); skips DuckDB.")
    args = ap.parse_args()

    metro_cfg = cli.resolve_metro(args.metro)  # validates slug; fails loudly on a typo
    if args.dry_run:
        report = dry_run(metro_cfg)
        print(report.render())
        return 0 if report.ok else 1

    db_url = _db_url()
    if args.metros:
        return sync_metros(db_url)

    metro = metro_cfg.metro_id
    today = date.today().isoformat()

    sync_metros(db_url)  # keep the registry current on every full load
    if not DUCKDB.exists():
        sys.exit(f"missing {DUCKDB} — run `cd transform && dbt build` first")

    # metro_id is carried by the gold tables themselves (v2.0.4, = dbt var 'metro'),
    # so gold is the single source of truth for which metro a row belongs to — it is
    # selected first and flows straight into the (metro_id, …) upsert key. The --metro
    # arg still drives sync_metros + logging; assert they agree to catch a stale build.
    con = duckdb.connect(str(DUCKDB), read_only=True)
    routes = con.execute(
        "select metro_id, authority_id, route_id, short_name, long_name, route_type, "
        "color, text_color, geom_wkt from gold_routes"
    ).fetchall()
    stops = con.execute(
        "select metro_id, authority_id, stop_id, name, geom_wkt from gold_stops"
    ).fetchall()
    hexes = con.execute(
        "select metro_id, h3, resolution, jobs, population, jobs_per_1k_pop, geom_wkt "
        "from gold_hex_metrics"
    ).fetchall()
    finances = con.execute(
        "select metro_id, authority_id, fiscal_year, actual_audited, fare_revenue, "
        "unlinked_trips, rta_kind, rta_amount, farebox_recovery from gold_funding"
    ).fetchall()
    vacancy = con.execute(
        "select metro_id, authority_id, as_of, open_postings, source_url, method "
        "from gold_vacancy"
    ).fetchall()
    access = con.execute(
        "select metro_id, h3, jobs_reachable_walk, walk_radius_m from gold_hex_access"
    ).fetchall()
    con.close()

    built = {r[0] for r in routes + stops + hexes + finances + vacancy + access}
    if built and built != {metro}:
        sys.exit(f"gold metro_id {sorted(built)} != --metro={metro} — rebuild dbt "
                 f"with --vars '{{metro: {metro}}}' before loading")

    # gold rows already lead with metro_id; append as_of=today (the load date) at the
    # back. vacancy carries its own as_of in the natural key, so it gets metro_id only.
    with psycopg.connect(db_url) as pg:
        with pg.cursor() as cur:
            cur.executemany(ROUTE_UPSERT,   [(*r, today) for r in routes])
            cur.executemany(STOP_UPSERT,    [(*r, today) for r in stops])
            cur.executemany(HEX_UPSERT,     [(*r, today) for r in hexes])
            cur.executemany(FINANCE_UPSERT, [(*r, today) for r in finances])
            cur.executemany(VACANCY_UPSERT, list(vacancy))
            cur.executemany(ACCESS_UPSERT,  [(*r, today) for r in access])
        pg.commit()

    print(f"  ok  loaded {len(routes)} routes, {len(stops)} stops, "
          f"{len(hexes)} hex cells, {len(finances)} finance rows, "
          f"{len(vacancy)} vacancy rows, {len(access)} access rows → Project A "
          f"(metro={metro})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
