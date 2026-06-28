# v1.4 — Job-Access Score + Isochrones — Implementation Plan

> Dependency-ordered segments off `v1.4`. Pure logic (isochrone parsing, score math)
> is TDD via `pipeline/selftest.py`. Follow [`../../../WORKFLOW.md`](../../../WORKFLOW.md)
> + [`../../../DEFINITION_OF_DONE.md`](../../../DEFINITION_OF_DONE.md).

**Goal:** The signature **job-access score** ([`ACCESS_SCORE.md`](../../../modeling/ACCESS_SCORE.md))
— how many jobs you can reach from where you are — surfaced as an ambient hex layer on
the map (reusing the v1.1 overlay machinery) with a legend (non-color signal) + table
fallback, plus an openrouteservice isochrone loader wired per [`ADR-003`](../../../decisions/ADR-003-routing-openrouteservice.md).

**Architecture:** Reuse the v1.1 hex jobs (`gold_hex_metrics`). A new gold model
`gold_hex_access` computes, per hex, the jobs reachable within a walk radius via a
great-circle spatial join (DuckDB spatial). A migration adds `public.hex_access` (RLS).
`tiles.py` adds an `access` property + breaks to the hex tiles/JSON; `TransitMap`
gains an "Access" overlay radio. An ORS isochrone loader (`pipeline/access.py`) is
built + unit-tested against a committed sample, gated on `ORS_API_KEY`.

## Locked modeling decisions (documented defaults)

`ORS_API_KEY` is **not** configured (checked `.env`), so per the phase prompt the ORS
loader is written + tested against a committed sample and the **published** ambient
metric uses a quota-free, fully-reproducible approximation. No synthetic figure ships.

| Decision | Default | Why |
|---|---|---|
| **Published ambient metric** | **Straight-line walkshed job access** — Σ jobs in hexes whose centroid is within **0.5 mi** (great-circle, `ST_Distance_Sphere`) of each hex centroid | Real, reproducible, no ORS quota. Honestly labeled "straight-line walk access," not transit. Reuses v1.1 `gold_hex_metrics` jobs. |
| **Walk radius** | **0.5 mi** (≈ 805 m, ACCESS_SCORE G5 ½-mi walk) | The standard access/egress radius; one ring for v1 (15/30/45-min transit rings need the deferred GTFS router). Override via `--vars`. |
| **ORS isochrones** | Loader **built + tested** (`parse_isochrone` pure + committed sample fixture); `fetch_isochrone` activates with `ORS_API_KEY`. Network isochrones **not published** until a key exists. | ADR-003 integration present + tested without faking figures. |
| **Schedule-aware transit routing** | **Deferred** (the ACCESS_SCORE "main spike": r5py/OTP) | Out of the free-tier/time budget; documented. Ambient is walk-access; transit rings land in a later phase. |
| **Surfacing** | Reuse the v1.1 hex overlay — add **"Access"** to the None/Jobs/Population radio; legend prints numeric ranges; click popup shows exact reachable-jobs (non-color signal) | Smallest honest diff; consistent UX. deck.gl not needed for a hex choropleth (DoD: deck.gl is for large *point* layers). |
| **Normalization** | Absolute `jobs_reachable_walk` for v1; per-capita deferred | Keeps the metric one clear thing; relative view is a later refinement (ACCESS_SCORE G10). |

## Segments

- **v1.4.1** — Plan + DATA_SOURCES (ORS row → verified-method note). *(this)*
- **v1.4.2** — ORS isochrone loader `pipeline/access.py` (`parse_isochrone` pure + tested;
  `fetch_isochrone` key-gated) + committed sample fixture `data/bronze/ors/isochrone_sample.geojson`.
  Acceptance: selftest green incl. isochrone-area/parse checks.
- **v1.4.3** — `gold_hex_access` (great-circle walkshed join over `gold_hex_metrics`) +
  `_gold.yml` + `assert_gold_hex_access_nonneg.sql`. Acceptance: `dbt build` green; one
  row per hex; `jobs_reachable_walk ≥ this hex's own jobs`.
- **v1.4.4** — Migration `public.hex_access` (RLS public-read) + `db/schema.sql` snapshot +
  `load.py` upsert. Acceptance: applied; `get_advisors` clean.
- **v1.4.5** — `tiles.py` emits `access` per hex + quantile breaks → `transit.json`;
  `lib/transit.ts` adds the `access` metric (ramp/label/breaks); `TransitMap.tsx` adds the
  "Access" overlay + legend + popup; `index.astro` extends the overlay table fallback.
  Acceptance: `npm run build` + `npm run check` green; overlay renders.
- **v1.4.6** — QA + `/code-review --fix` + gate. chrome-devtools 360/768/1280/1920,
  reduced-motion, local-prod Lighthouse a11y ≥ 90.

**Phase GATE (all pass, output pasted):** (1) selftest; (2) dbt build; (3) frontend
build + check 0 errors; (4) `get_advisors` clean — RLS on `hex_access`; (5) Access
overlay renders with legend + table fallback at 4 widths, Lighthouse a11y ≥ 90.
Then emit: **ACCESS SCORE GATE GREEN**.

## Deviations / notes

- **No ORS key → straight-line walkshed is the published ambient metric**; ORS network
  isochrones are loader-tested and activate with `ORS_API_KEY`. No synthetic figure ships.
- **Transit-leg routing deferred** (the documented ACCESS_SCORE spike).
- **MapLibre fill layer, not deck.gl** — a hex choropleth isn't a large point layer.

## File map

```
pipeline/access.py                            (new)  ORS isochrone loader + pure parser
pipeline/selftest.py                          (mod)  + isochrone parse checks
pipeline/load.py                              (mod)  + hex_access upsert
pipeline/tiles.py                             (mod)  + access property + breaks
transform/models/gold/gold_hex_access.sql     (new)  walkshed job-access join
transform/models/gold/_gold.yml               (mod)
transform/tests/assert_gold_hex_access_nonneg.sql (new)
db/migrations/<ts>_v1_4_4_hex_access.sql       (new)
db/schema.sql                                 (mod)  + hex_access snapshot
data/bronze/ors/isochrone_sample.geojson      (new)  ORS schema fixture (test only)
frontend/src/lib/transit.ts                   (mod)  + access metric
frontend/src/components/TransitMap.tsx        (mod)  + Access overlay
frontend/src/pages/index.astro                (mod)  + access table fallback
```
