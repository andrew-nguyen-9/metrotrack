# v1.1 — Mapping Pillar — Implementation Plan

> **For workers:** dependency-ordered segments; each is a branch off `v1.1`,
> merged back when its acceptance criteria pass. Pure logic (parsing, binning,
> normalization math) is TDD via `pipeline/selftest.py`. Follow
> [`../../../WORKFLOW.md`](../../../WORKFLOW.md) and
> [`../../../DEFINITION_OF_DONE.md`](../../../DEFINITION_OF_DONE.md).

**Goal:** Add a population + jobs choropleth overlay (H3 hex bins) on top of the
v1.0 routes + stops map, end-to-end: Census loaders → dbt H3 binning → Supabase
hex table → PMTiles overlay → accessible MapLibre layer toggle.

**Architecture:** Same medallion path as v1.0. Census flat files (key-free) land
in content-hashed bronze parquet; dbt silver assigns each block-group centroid to
an H3 cell (DuckDB `h3` community ext) and aggregates jobs + population per cell;
gold emits hex polygons (WKT) for both the Supabase spine and the PMTiles export.
The MapLibre island gains a `hex` source-layer and a single-overlay radio toggle.

**Tech stack:** Python (urllib + DuckDB, no pandas — matches `pipeline/bronze.py`);
dbt-duckdb + `h3` community extension; PostGIS (Supabase Project A); tippecanoe →
PMTiles; MapLibre GL JS + React island (Astro).

## Global constraints (every segment)

- **Branch base:** v1.1 is branched off **`v1.0`**, not `main`. See *Deviations*.
- No new client-bundle secrets; RLS public-read on every new table; service-role
  key server-side only.
- Bronze is content-hashed + append-safe; loaders idempotent + re-runnable.
- Every published figure has a `DATA_SOURCES.md` row (already added: LODES, CenPop).
- Geometry SRID 4326; `ST_IsValid` before load.
- Commits: `<type>(scope): <summary>  [v1.1.s.t]`, no AI attribution.
- Do NOT rewrite v1.0 shared schema columns — ADD via migration. Do NOT start v1.2.

## Locked modeling decisions (ambiguities resolved with documented defaults)

| Decision | Default chosen | Why |
|---|---|---|
| **Jobs source** | Census **LEHD LODES8**, Illinois **WAC** `S000 JT00` (latest year), block-level, key-free `.csv.gz` | No API key; `w_geocode` block GEOID joins cleanly; `C000` = total jobs at workplace. |
| **Population + coordinates** | Census **2020 Centers of Population**, block-group file `CenPop2020_Mean_BG17.txt` (IL) | Key-free; one file carries `POPULATION` **and** centroid `LATITUDE`/`LONGITUDE` → no TIGER shapefile / ACS key needed for binning. |
| **ACS** | **Deferred.** v1.1 population baseline is decennial 2020; ACS demographic breakdowns land in a later phase. | ACS needs a key + TIGER geometry for block groups; out of scope for the overlay. DATA_SOURCES ACS row stays (☐ unverified). |
| **Geographic scope** | **Cook County** (state+county FIPS `17031`) | Densest, most legible; matches the v1.0 sample footprint. Statewide is a `--vars` swap later. |
| **Hex engine** | DuckDB **`h3` community extension** in dbt silver/gold | Already verified working locally; avoids requiring a PostGIS H3 build on Supabase. |
| **H3 resolution** | **res 8** (edge ≈461 m, area ≈0.74 km²) | Neighborhood-scale; ~2–3k cells over Cook County — legible + light. Override via `dbt --vars '{h3_res: N}'`. |
| **Normalization** | Per-hex **absolute counts** (uniform-area hex ≈ density) + derived `jobs_per_1k_pop` | H3 cells are equal-area, so raw count maps to density without distortion. |
| **Choropleth breaks** | **Quantile** (5 bins) computed at tile-build time, baked into the GeoJSON `legend` sidecar | Quantiles read better than linear on skewed jobs/pop; precomputed = no client compute. |
| **Non-color encoding** | Legend prints the **numeric range per bin**; click popup shows exact jobs/pop; only **one** overlay visible at a time (radio) | Satisfies DoD "color never the only signal" for map layers. |

---

## Segments (dependency-ordered)

### v1.1.2 — Census bronze loaders (jobs + population)

**Files:**
- Create: `pipeline/census.py` — pure parsers + `fetch_*` + `ingest_*`.
- Modify: `pipeline/selftest.py` — add pure-parser checks.
- Create (committed sample): `data/bronze/census/lodes_wac.parquet`,
  `data/bronze/census/cenpop_bg.parquet` (Cook County subset) + manifest rows.

**Approach (TDD on the pure parts):**
- `parse_lodes_wac(csv_bytes) -> rows` — keep `w_geocode`, `C000` (total jobs);
  derive `bg_geoid = w_geocode[:12]`; filter to Cook County (`w_geocode[:5]=="17031"`).
- `parse_cenpop_bg(text_bytes) -> rows` — build `bg_geoid` from
  `STATEFP+COUNTYFP+TRACTCE+BLKGRPCE`; keep `POPULATION`, `LATITUDE`, `LONGITUDE`;
  filter Cook County (`STATEFP=="17" and COUNTYFP=="031"`).
- `fetch_*` download via `urllib` (LODES8 `.csv.gz` → gunzip; CenPop `.txt`),
  with the source URLs documented in-module; both go through `bronze.ingest_csv`
  so they are content-hashed + idempotent.
- Cook County subset committed as the bronze sample (same pattern as the v1.0 GTFS
  subset). Full-state run is a flag.

**Acceptance:**
- `python pipeline/selftest.py` green, incl. new checks: LODES C000 cast + bg_geoid
  derivation + Cook filter; CenPop geoid assembly + Cook filter; both tolerant of
  header whitespace.
- Re-running the loader on identical bytes does **not** rewrite parquet (idempotent).
- `data/bronze/census/*.parquet` committed with manifest receipts; rows > 0.

### v1.1.3 — H3 binning in dbt (silver + gold)

**Files:**
- Create: `transform/models/silver/silver_hex_metrics.sql` — centroid → H3 cell,
  aggregate jobs + population per cell.
- Create: `transform/models/gold/gold_hex_metrics.sql` — hex polygon WKT + GeoJSON,
  `jobs_per_1k_pop`, for serving (Supabase loader + tile export).
- Modify: `transform/models/silver/_silver.yml`, `transform/models/gold/_gold.yml`
  — model docs + tests.
- Create: `transform/tests/assert_silver_hex_unique.sql` (one row per h3 cell),
  `transform/tests/assert_silver_hex_nonneg.sql` (jobs/pop ≥ 0, not null).
- Modify: `transform/profiles.yml` — add `h3` to extensions; `dbt_project.yml`
  — add `h3_res` var (default 8).

**Approach:**
- silver: read both bronze parquets; `h3_latlng_to_cell(lat, lon, {{ var('h3_res') }})`
  on the CenPop centroid; population summed per cell; jobs joined block-group→cell
  via the CenPop centroid's cell (LODES has no coords, so jobs ride the block group's
  centroid cell). `group by h3` → `jobs`, `population`.
- gold: `h3_cell_to_boundary_wkt(h3)` → polygon; `ST_AsGeoJSON`; compute
  `jobs_per_1k_pop = 1000.0 * jobs / nullif(population,0)`.

**Acceptance:**
- `cd transform && dbt build` green, including the two new schema tests
  (cell uniqueness, non-null/non-negative counts) and the existing geom-valid test
  extended to hex polygons.
- Cell count is in a sane range for Cook County at res 8 (hundreds–few thousand).

### v1.1.4 — Supabase hex table (migration to Project A)

**Files:**
- Create: `db/migrations/<ts>_v1_1_4_hex_metrics.sql`.
- Modify: `db/schema.sql` — append the `hex_metrics` snapshot.
- Modify: `pipeline/load.py` — upsert gold hex rows into `public.hex_metrics`.

**Approach:**
- Table `public.hex_metrics (h3 text primary key, resolution int, jobs int,
  population int, jobs_per_1k_pop double precision, geom extensions.geometry(Polygon,4326))`.
- GiST index on `geom`; btree on `h3` (PK); RLS enable + public-read SELECT policy
  for `anon, authenticated` (mirror the v1.0 pattern exactly).
- Apply via `supabase` MCP `apply_migration`; then `get_advisors` (security) clean.
- `load.py` gains a `HEX_UPSERT` (insert … on conflict (h3) do update) reading
  `gold_hex_metrics`, geom via `ST_GeomFromText(wkt,4326)`.

**Acceptance:**
- Migration applied; `list_tables` shows `hex_metrics` with RLS enabled.
- `get_advisors` (security) returns **no** new ERROR/WARN on `hex_metrics`.
- `load.py` upserts hex rows idempotently (re-run = no dupes; PK on h3).

### v1.1.5 — Choropleth overlay (PMTiles + MapLibre island)

**Files:**
- Modify: `pipeline/tiles.py` — emit a `hex` GeoJSON layer + quantile `legend`
  sidecar into `transit.json`; add `-L hex:` to tippecanoe.
- Modify: `frontend/src/lib/transit.ts` — extend `TransitData` (hex legend, breaks).
- Modify: `frontend/src/components/TransitMap.tsx` — `hex` fill layers (jobs, pop),
  single-overlay radio toggle, legend, click popup, keyboard access, reduced-motion.
- Modify: `frontend/src/pages/index.astro` — overlay legend + extend table fallback
  (top-N hex cells by jobs and by population).

**Approach:**
- tiles.py: query `gold_hex_metrics`, write hex features; compute 5 quantile breaks
  for jobs and population; write `{ hex: { breaks: {...} } }` into `transit.json`.
- TransitMap: two fill layers (`hex-jobs`, `hex-pop`), `fill-color` a `step`
  expression over the precomputed breaks; visibility driven by a radio group
  (None / Jobs / Population). Controls are real `<input type="radio">` (keyboard +
  screen-reader native). Legend lists each bin's numeric range. Click a hex →
  popup with exact jobs/pop. Reduced-motion: no fill-opacity transition.
- Table fallback: a "Population & jobs by area (top cells)" table so the overlay's
  data exists with **zero** JS.

**Acceptance:**
- `cd frontend && npm run build` green, no type errors (`astro check`).
- Overlay renders over routes/stops at a Vercel preview; radio switches
  None/Jobs/Population; legend shows numeric ranges; popup shows exact values.
- Table fallback present with hex data.

### v1.1.6 — QA + performance

**Approach:**
- `chrome-devtools` at **360 / 768 / 1280 / 1920**: no overflow, legend legible,
  controls reachable by keyboard, focus visible.
- Reduced-motion verified (no animated camera/opacity).
- `lighthouse_audit` on the deployed preview: **a11y ≥ 90** (best-practices + SEO
  tracked; perf documented if the map page exceeds the JS budget per DoD).
- `/code-review --fix` on the full v1.1 diff; resolve real findings.
- `superpowers:verification-before-completion` before emitting the gate phrase.

**Acceptance (the phase GATE — all must pass, output pasted):**
1. `python pipeline/selftest.py` green.
2. `cd transform && dbt build` green (new hex models + tests).
3. `cd frontend && npm run build` green, no type errors.
4. `supabase get_advisors` (Project A, security) clean — RLS on `hex_metrics`.
5. Overlay renders at a Vercel preview, toggle works, verified via chrome-devtools
   at 4 widths, accessible table fallback present, Lighthouse a11y ≥ 90.

---

## Deviations from the segment prompt

- **Branch base = `v1.0`, not `main`.** The prompt's prereq assumed v1.0 was merged
  to `main` and tagged `v1.0.0`; in the actual repo `main` holds only the docs
  scaffold and there are no tags (PHASES_OVERVIEW: v1→main merge happens at the
  *end* of v1). Branching off `main` would discard the entire foundation, so v1.1
  branches off `v1.0`. Phase still does **not** merge to main.
- **Population from decennial 2020 Centers of Population, not ACS.** Key-free and
  carries centroids; ACS demographic detail is deferred (see modeling table).

## File map (new/changed)

```
pipeline/census.py                       (new)  loaders + pure parsers
pipeline/selftest.py                     (mod)  + census parser checks
pipeline/tiles.py                        (mod)  + hex layer + legend
pipeline/load.py                         (mod)  + hex upsert
transform/models/silver/silver_hex_metrics.sql  (new)
transform/models/gold/gold_hex_metrics.sql      (new)
transform/models/silver/_silver.yml      (mod)
transform/models/gold/_gold.yml          (mod)
transform/tests/assert_silver_hex_*.sql  (new)
transform/dbt_project.yml, profiles.yml  (mod)  h3 ext + h3_res var
db/migrations/<ts>_v1_1_4_hex_metrics.sql (new)
db/schema.sql                            (mod)  + hex_metrics snapshot
data/bronze/census/*.parquet             (new)  Cook County sample receipts
frontend/src/components/TransitMap.tsx   (mod)  hex layers + toggle + legend
frontend/src/lib/transit.ts              (mod)  hex types
frontend/src/pages/index.astro           (mod)  legend + table fallback
```
