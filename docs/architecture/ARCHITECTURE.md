# Architecture

Medallion data flow, free-tier throughout. Same shape as the trivia-generator /
music-festival-analyzer repos, plus a geospatial spine.

```
 EXTRACT (pipeline/)            TRANSFORM (transform/)        SERVE (frontend/)
 ────────────────────          ──────────────────────        ─────────────────
 Socrata (Chicago Data) ─┐
 GTFS static + realtime  ─┤      dbt + DuckDB                 Astro on Vercel (React islands)
 Census LODES / ACS      ─┼──►   bronze → silver → gold  ──►  MapLibre + deck.gl (map)
 Overpass / OSM POIs     ─┤        (parquet)                  Apache ECharts (funding/staff)
 openrouteservice (iso)  ─┤           │
 Career-page scrape      ─┘           ▼
 (Playwright)
                              Supabase Postgres + PostGIS  ◄── gold loaded here
                              (spatial joins, RLS public-read)
                                     │
                              tippecanoe → PMTiles (static, served from Vercel/R2)
```

## Layers

- **Bronze** (`data/`, committed parquet — K2): raw pulls, content-hashed,
  append-safe; the reproducibility receipt. Dev hits a **live (dedicated) Supabase
  project** (K1), not a DB-less local mode — bronze is for rebuild/audit, not the
  app's read path.
- **Silver** (dbt staging): typed, deduped, geometry-validated.
- **Gold** (dbt marts): the analytic tables the app reads — e.g. `stop_access`
  (jobs/residents within ½ mi of each stop), `funding_actuals`, `vacancy_trend`.
- **Serving:** gold loaded into **Supabase + PostGIS** for live spatial queries;
  large/static geometry baked to **PMTiles** so the map needs no tile server.

## Why this split

- **DuckDB** crunches Census LODES parquet locally for free; **PostGIS** does the
  live spatial joins the map's interactivity needs (`ST_DWithin`, `ST_Contains`).
- **PMTiles** keeps the map free and fast (mirrors the offline-map trick from
  trivia-generator's `world-atlas`).
- **H3 hex binning** normalizes population/jobs/ridership to compare against stop
  access without modifiable-areal-unit bias.

## Schedules (`.github/workflows/`)

- **Nightly:** extract → dbt build + test → load gold to Supabase → rebuild PMTiles.
- **Weekly:** career-page scrape → append a vacancy snapshot (the time series).

## Key decisions

- DB/geo backbone: **Supabase + PostGIS** — [`ADR-001`](../decisions/ADR-001-supabase-postgis.md).
- Frontend: **Astro + React islands** — [`ADR-002`](../decisions/ADR-002-astro-frontend.md).
- Routing/isochrones: **openrouteservice** — [`ADR-003`](../decisions/ADR-003-routing-openrouteservice.md).
- Tile strategy + scrape approach: ADRs to be written as those segments open.
