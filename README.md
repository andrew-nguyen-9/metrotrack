# MetroTrack

> *Transit you can see.*

A public, neutral civic-accountability tracker for Chicagoland transit, built on
free/hobby tiers. Live at `transit.an9.dev` (planned).

Three pillars:

1. **Funding** — budget vs. actuals for NITA, CTA, Pace, and Metra.
2. **Mapping** — bus/rail routes + stops mapped against population, jobs, and
   destinations (shopping, airports, attractions, venues, commercial).
3. **Hiring** — vacancy rates and understaffing tracked per authority over time.

## Stack

Supabase Postgres + PostGIS · Python ETL · dbt + DuckDB · **Astro** + MapLibre +
deck.gl + Apache ECharts on Vercel · PMTiles vector maps · openrouteservice
isochrones · GitHub Actions crons. See `docs/architecture/ARCHITECTURE.md`.

## Repository layout

| Path | Purpose |
|---|---|
| `docs/` | The project's brain — start at `docs/README.md`. |
| `pipeline/` | Python ETL (extract from public APIs, scrape career pages). |
| `transform/` | dbt + DuckDB project: bronze → silver → gold. |
| `db/` | Postgres/PostGIS schema + migrations. |
| `data/` | Committed bronze snapshots (parquet/jsonl). |
| `frontend/` | Astro app + React islands (the serving path). |
| `.github/workflows/` | CI gates + scheduled scrape/nightly transform. |

## Development

Python (pipeline + dbt) uses [uv](https://docs.astral.sh/uv/); the frontend uses npm.

```sh
uv sync                              # install pipeline + dbt deps
uv run python pipeline/selftest.py   # GATE 1: ETL harness
(cd transform && DBT_PROFILES_DIR=. uv run --project .. dbt build)  # GATE 2: transforms
(cd frontend && npm ci && npx astro check && npx astro build)       # GATE 3: frontend
```

## Status

Pre-`v1.0`. Foundation phase. See `docs/phases/v1/PHASES_OVERVIEW.md`.

## Data & sources

Every published figure traces to `docs/architecture/DATA_SOURCES.md`. Funding and
governance numbers are verified against primary sources before publishing.
