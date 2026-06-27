# CLAUDE.md — MetroTrack (Chicagoland Transit Tracker)

Instructions for Claude Code working in this repo. Read this first, then the doc
that matches your task (`docs/README.md` is the router).

## What this is

**MetroTrack** — a public, neutral civic-accountability tracker for Chicagoland
transit: **(1)** funding for NITA / CTA / Pace / Metra, **(2)** a map of bus/rail
usage against population, jobs, and destinations, **(3)** hiring + understaffing,
plus the signature **job-access score**. Free/hobby tiers only.

## Stack

- **DB:** dedicated Supabase project, Postgres + **PostGIS** (spatial joins, RLS
  public-read). Live DB required for dev (not DB-less); bronze still committed as receipts.
- **ETL:** Python in `pipeline/` (Socrata, GTFS + GTFS-realtime, Census LODES/ACS,
  Overpass, openrouteservice isochrones, career-page scrape via Playwright).
- **Transform:** dbt + DuckDB in `transform/` — bronze → silver → gold.
- **Frontend:** **Astro** (Vercel adapter) — static pages + React islands for the
  map/charts/search ([`ADR-002`](docs/decisions/ADR-002-astro-frontend.md)). Tailwind +
  tokens, Radix in islands. **MapLibre GL JS + deck.gl** maps, **Apache ECharts** charts.
- **Maps served as PMTiles** (tippecanoe) — no tile server, no Mapbox bill.
- **Routing:** openrouteservice (free) for walk/isochrones ([`ADR-003`](docs/decisions/ADR-003-routing-openrouteservice.md)).
- **Schedules:** GitHub Actions cron for scrape + nightly transform → redeploy.
- **Domain:** `transit.an9.dev`. **Analytics:** privacy-friendly. **Errors:** Sentry.

## Non-negotiable rules

- **No code before the plan exists.** A phase needs `docs/phases/v{p}/` first.
- **`main` is always shippable.** Never commit to it directly; it receives
  reviewed, QA'd phase merges only.
- **Versioning is `v[phase].[segment].[task]`** — see `docs/VERSIONING.md`. It is
  *not* semver.
- **Data integrity first.** Every published number traces to a source row in
  `docs/architecture/DATA_SOURCES.md`. Never assert funding/governance figures
  without a primary source; current-events claims must be verified.
- **Pipeline scripts are idempotent + re-runnable.** Bronze is content-hashed.
- **No secrets in the client bundle.** Service-role key stays server-side; RLS on
  every new table.
- **Done means done** — see `docs/DEFINITION_OF_DONE.md`. "It builds" is not done.
- **No loop without a hard verification gate** — see `docs/TOOLING.md` for the
  plugin/skill stack and loop rules.
- **No AI attribution** in commits, PRs, or branch names.

## Skills this project exists to build

PostGIS spatial joins · H3 hex binning · isochrones · PMTiles/vector tiles ·
dbt+DuckDB medallion ETL · scheduled scrape → time series · MapLibre/deck.gl ·
time-series forecasting. Prefer the simplest tool on the ladder; reach for ML
only when a heuristic measurably falls short.
