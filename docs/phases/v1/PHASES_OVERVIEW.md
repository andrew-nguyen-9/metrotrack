# v1 Phases — Overview

Dependency-ordered. Each phase opens a branch, runs its segments (sub-branches),
and finishes with the 8-step ritual ([`../../WORKFLOW.md`](../../WORKFLOW.md)).
Versioning: `v[phase].[segment].[task]` ([`../../VERSIONING.md`](../../VERSIONING.md)).

> Mapping-first: geospatial is the biggest new skill, the most visual, and the
> spine the funding and hiring pillars layer onto.

| Phase | Branch | Name | Status |
|-------|--------|------|--------|
| v1.0 | `v1.0` | Foundation: repo, ETL harness, PostGIS, GTFS loader, one PMTiles map | Planned |
| v1.1 | `v1.1` | **Mapping pillar** — routes + stops + population/jobs overlay | Planned |
| v1.2 | `v1.2` | **Funding pillar** — NITA/CTA/Pace/Metra budget vs actuals (ECharts) | Planned |
| v1.3 | `v1.3` | **Hiring pillar** — weekly scrape → vacancy time series | Planned |
| v1.4 | `v1.4` | **Job-access score + isochrones** (the signature feature; O6=C). Forecasting deferred to v2 (G8). | Planned |

## Why this order

- **Foundation (v1.0) first** — DB + PostGIS + the bronze→gold harness + a working
  map tile unblock and de-risk everything after. No pillar ships without it.
- **Mapping (v1.1) before Funding/Hiring** — it exercises the core new skill and
  produces the geometry + stop dimension the other pillars reference.
- **Funding (v1.2) before Hiring (v1.3)** — tabular and faster to a shippable page;
  hiring needs weeks of snapshots before its trend is interesting, so start its
  clock early but ship its page after.
- **Analysis (v1.4) last** — combines all three layers; isochrones + forecasting
  only make sense once the data exists.

## Cross-cutting (acceptance criteria in every segment)

Data-integrity checks · idempotent pipeline · RLS on new tables · design guideline
+ accessibility + reduced-motion + performance budgets. See
[`../../DEFINITION_OF_DONE.md`](../../DEFINITION_OF_DONE.md). Not separate phases.

## v1.0 — Foundation (segment sketch)

- **v1.0.1** — Repo scaffold: `pipeline/`, `transform/`, `db/`, `data/`,
  `frontend/` (**Astro** + Tailwind + Vercel adapter), `.github/workflows/`;
  `selftest.py` + dbt skeleton. Brand: extract `design/` logo assets (Chicago
  variant) into `frontend/public/`; favicon/OG.
- **v1.0.2** — Dedicated Supabase project + PostGIS; `db/schema.sql` (authorities,
  stops, routes; SRID 4326; GiST indexes; RLS public-read). `get_advisors` clean.
- **v1.0.3** — GTFS static loader (CTA/Pace/Metra) → bronze → silver stops/routes.
- **v1.0.4** — tippecanoe → PMTiles build; one MapLibre map (React island) renders
  routes/stops on Vercel at a preview URL.
- **v1.0.5** — Nightly workflow: extract → dbt build+test → load gold → rebuild
  tiles → trigger redeploy. Lighthouse CI gate (M4) wired.

Detailed per-segment plans land as each segment opens (see the v3 PLAN.md pattern
in the portfolio-website repo).

## Tags

Finishing v1 merges `v1` → `main` and tags `v1.0.0`. Patches bump the third digit.
