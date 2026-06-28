# v2.0 — Multi-tenant Foundation — Implementation Plan

> **For workers:** dependency-ordered segments; each is a branch off `v2.0`,
> merged back when its acceptance criteria pass. Pure logic (config parsing, geo
> derivation, key composition) is TDD via `pipeline/selftest.py`. Follow
> [`../../../WORKFLOW.md`](../../../WORKFLOW.md) and
> [`../../../DEFINITION_OF_DONE.md`](../../../DEFINITION_OF_DONE.md).

**Goal:** Turn the single-metro (Chicago-implicit) app into a multi-tenant one
where **adding a metro = one config file + one `--metro` pipeline run** `[B13a]`,
*without losing v1*. Chicago migrates to `/chicago` and stays green as the **golden
reference** `[A6a]`. No new metro is onboarded here — that's v2.3+.

**Architecture:** Single Postgres DB, a `metro_id` column on every spine table
`[B1a]`, composite `(metro_id, natural_key)` keys `[B18a]`. A `metros/<slug>.toml`
file is the **authored source of truth** (slug, name, bbox, tz, agencies, GTFS feed
urls + license, census FIPS, source ids); a `metros` table **mirrors** it for
serving/joins `[B2c, B6a, B9a]`. Pipeline scripts gain `--metro=<slug>` reading that
config `[H1a]`; dbt models gain a `metro_id` and run per-metro via vars `[H5a]`.
Astro routing becomes `[metro]/...` via `getStaticPaths` `[B5a]`. Gold reload upserts
by `(metro_id, key)` with `as_of` + `source_hash` provenance `[H14a, H15a]`.

**Tech stack:** unchanged — Python (urllib + DuckDB, no pandas), dbt-duckdb,
PostGIS (Supabase Project A), tippecanoe → PMTiles, MapLibre + React island (Astro).

## Global constraints (every segment)

- **Branch base:** `v2.0` is branched off **`main`** (v1 is merged + tagged
  `v1.0.0`). Phase does **not** merge to `main` until v2 closes.
- No new client-bundle secrets; RLS public-read on every new/altered table;
  service-role key server-side only.
- **Do not rewrite v1 data** — migrate via additive `metro_id` (nullable → backfill
  `'chicago'` → NOT NULL) `[B17a]`. Never `DROP` a v1 column.
- Bronze content-hashed + idempotent; loaders re-runnable; hash per `(metro, source)`
  `[H4a]`.
- Every published figure keeps its `DATA_SOURCES.md` row `[H16a]`.
- Commits: `<type>(scope): <summary>  [v2.0.s.t]`, no AI attribution.
- **Chicago must stay green at every step** — its pages, tiles, and figures are the
  regression oracle.

## Locked decisions (this segment)

| Decision | Choice | Why / Q |
|---|---|---|
| Tenancy | Single DB, `metro_id` on every spine table | one DB, RLS stays simple `[B1a]` |
| Keys | Composite `(metro_id, natural_key)` | GTFS ids collide across metros `[B18a]` |
| Config | `metros/<slug>.toml` authored truth + `metros` table mirror | human-editable + joinable `[B2c]` |
| Slug | Short, stable, kebab: `chicago`, `sf`, `nyc` | URL + filename + db key `[E16a]` |
| RLS | Public-read on all, no per-metro policy | data is public `[B3a]` |
| Routing | `[metro]/...` dynamic, SSG | static + indexable `[B5a, D10a]` |
| Pipeline | `--metro=<slug>` + `--dry-run` smoke | repeatable onboarding `[H1a, H20a]` |
| Bronze | `data/bronze/<metro>/<source>/...` | per-metro receipts `[H2a]` |
| dbt | `metro_id` + dbt var `metro` | one model set, N metros `[H5a]` |
| Reload | Upsert `(metro_id, key)`, no truncate | multi-metro safe `[H14a]` |
| Provenance | `as_of` + `source_hash` on gold | "data as of" + integrity `[H15a]` |
| Tz | Store UTC, render in metro tz | correctness `[B15a]` |

## Segments (dependency-ordered)

### v2.0.1 — Metro config + `metros` registry table

**Files:**
- Create: `metros/chicago.toml` — slug, name, bbox, tz, agencies (id/name/mode),
  GTFS feed urls + license, census FIPS (`17031`), ORS/source ids. Authored truth.
- Create: `metros/_schema.md` — the toml contract (what each key means, required vs
  optional). One source of truth for "how to add a metro."
- Create: `pipeline/metros.py` — `load_metro(slug) -> Metro`, `list_metros()`,
  pure validators (bbox sanity, required keys, slug format). No network.
- Modify: `pipeline/selftest.py` — parse `chicago.toml`, assert required keys + bbox
  + at least one agency + valid slug.
- Create: `db/migrations/<ts>_v2_0_1_metros.sql` — `public.metros (metro_id text pk,
  name text, slug text unique, bbox geometry(Polygon,4326), tz text, status text
  check in ('live','soon'), as_of date)`; RLS public-read.
- Modify: `db/schema.sql` — append `metros` snapshot.
- Modify: `pipeline/load.py` — `sync_metros()` upserts `metros/*.toml` → `metros`
  table (the mirror).

**Acceptance:**
- `python pipeline/selftest.py` green incl. config validators.
- Migration applied; `list_tables` shows `metros`, RLS enabled; `get_advisors`
  (security) clean.
- `sync_metros()` upserts `chicago` row idempotently (re-run = no dupes).

### v2.0.2 — `metro_id` migration of existing spine

**Files:**
- Create: `db/migrations/<ts>_v2_0_2_metro_id_backfill.sql` — for each v1 table
  (`authorities`, `stops`, `routes`, `hex_metrics`, `hex_access`, `agency_finances`,
  `vacancy_postings`): `ADD COLUMN metro_id text` → `UPDATE ... SET 'chicago'` →
  `ALTER ... SET NOT NULL` → add FK to `metros(metro_id)` → swap PK/unique to
  composite `(metro_id, <natural_key>)` `[B17a, B18a]`. Add `as_of`, `source_hash`
  where missing `[H15a]`.
- Modify: `db/schema.sql` — reflect new columns + composite keys.
- Modify: `pipeline/load.py` — all upserts key on `(metro_id, ...)`; accept a
  `metro` arg; set `as_of`/`source_hash`.

**Approach:** additive only; backfill before NOT NULL; keep GiST/btree indexes,
add `metro_id` to composite indexes where it improves per-metro filtering.

**Acceptance:**
- Migration applied; every spine table has NOT NULL `metro_id='chicago'`, composite
  key, FK to `metros`; `get_advisors` clean.
- Chicago row counts **unchanged** vs pre-migration (paste before/after).
- Re-running `load.py --metro=chicago` is idempotent (no dupes).

### v2.0.3 — Parametrize the pipeline (`--metro`)

**Files:**
- Modify: `pipeline/gtfs.py`, `census.py`, `funding.py`, `hiring.py`, `access.py`,
  `tiles.py`, `load.py`, `bronze.py` — accept `--metro=<slug>`, read `metros/<slug>.toml`,
  write bronze to `data/bronze/<metro>/...` `[H2a]`, hash per `(metro, source)` `[H4a]`.
- Add: a `--dry-run` flag that validates feed reachability + bbox/FIPS without
  writing `[H20a]`.
- Modify: `pipeline/__init__.py` / a small `cli` helper — shared `--metro` arg parse.
- Modify: `pipeline/selftest.py` — assert each entrypoint resolves Chicago config and
  bronze path; `--dry-run` returns a pass/fail report struct.
- Move: existing `data/bronze/<source>/...` → `data/bronze/chicago/<source>/...`
  (keep receipts; update `manifest.json`). gitignore large GTFS, keep manifest `[I7a]`.

**Acceptance:**
- `python pipeline/selftest.py` green.
- `python -m pipeline.gtfs --metro=chicago --dry-run` reports all Chicago feeds
  reachable + geo valid; a bogus slug fails loudly.
- Full `--metro=chicago` run reproduces v1 bronze under the new path; idempotent.

### v2.0.4 — dbt multi-metro (`metro_id` + var)

**Files:**
- Modify: every model in `transform/models/silver/*` and `gold/*` — carry `metro_id`
  through; filter/parametrize by `{{ var('metro', 'chicago') }}` `[H5a]`.
- Modify: GTFS-derived silver — normalize to canonical columns, tolerate missing
  optional GTFS fields `[H6a]`.
- Modify: `transform/dbt_project.yml` — add `metro` var (default `chicago`).
- Modify: `transform/models/*/_*.yml` + `transform/tests/*` — uniqueness tests become
  `(metro_id, key)`; add a test that `metro_id` is never null in gold.

**Acceptance:**
- `cd transform && dbt build --vars '{metro: chicago}'` green, all tests incl. the
  new composite-uniqueness + non-null-`metro_id` tests.
- Gold row counts for Chicago match v1 (paste).

### v2.0.5 — Astro `[metro]` routing + Chicago migration

**Files:**
- Create: `frontend/src/pages/[metro]/index.astro` (overview), `[metro]/map.astro`,
  `[metro]/funding.astro`, `[metro]/hiring.astro`, `[metro]/job-access.astro` —
  `getStaticPaths` from the `metros` table / a generated `metros.json` `[B5a, G2a]`.
- Create: `frontend/src/lib/metros.ts` — load metro list + per-metro data; types.
- Modify: `frontend/src/components/*` (`TransitMap`, `FundingChart`, `VacancyChart`)
  — take a `metro` prop; data swapped by metro, same code `[J1a, J2a, J7a]`.
- Modify: data loading — per-metro `frontend/src/data/<metro>/{transit,funding,hiring}.json`
  (Chicago files move under `chicago/`).
- Modify: `frontend/src/layouts/Base.astro` — carry `metro` to islands via props
  `[B7a]`; default map viewport from `metros.bbox` `[B12a]`.
- Delete (after parity verified): flat `frontend/src/pages/{index,funding,hiring}.astro`
  — replaced by `[metro]/*`. (Homepage `index.astro` is rebuilt in v2.1; here it can
  temporarily redirect to `/chicago`.)

**Approach:** `getStaticPaths` returns one entry per live metro (just `chicago` now).
Islands stay generic; the only per-metro input is data + bbox from config. Keep the
accessible table fallbacks and reduced-motion behavior from v1.

**Acceptance:**
- `cd frontend && npm run build` green, no type errors (`astro check`).
- `/chicago`, `/chicago/map`, `/chicago/funding`, `/chicago/hiring`,
  `/chicago/job-access` render at a Vercel preview with **v1 parity** (same figures,
  same map, same charts), verified via chrome-devtools at 360/768/1280/1920.
- `/` redirects to `/chicago` (placeholder until v2.1 homepage).

### v2.0.6 — Nightly multi-metro orchestration + golden test

**Files:**
- Modify: `.github/workflows/nightly.yml` — matrix over `metros` where
  `status='live'` `[H11a]`; one metro failing does not fail others `[H12a]`; stagger
  to stay within free Actions minutes `[I5a]`; per-metro freshness-floor check fails
  loud `[H13a]`.
- Modify: `pipeline/tiles.py` — output `tiles/<slug>.pmtiles`; enforce a size cap +
  per-zoom limits, simplify geometry to hit it `[B11a, I4]`.
- Create: `pipeline/checks.py` — `verify_metro(slug)`: every published figure traces
  to a source row + freshness floor met `[K6a]` (the data-integrity gate the loop
  reuses).
- Modify: `pipeline/selftest.py` — unit-test `verify_metro` on a fixture.

**Acceptance (the phase GATE — all must pass, output pasted):**
1. `python pipeline/selftest.py` green (config, `--dry-run`, `verify_metro`).
2. `cd transform && dbt build --vars '{metro: chicago}'` green.
3. `cd frontend && npm run build` green, no type errors.
4. `supabase get_advisors` (Project A, security) clean — RLS on `metros` + all
   altered tables.
5. **Golden test:** `/chicago/*` renders at a Vercel preview at full v1 parity
   (figures + map + charts identical), verified via chrome-devtools at 4 widths,
   Lighthouse a11y ≥ 90, perf within budget.
6. `pipeline/checks.verify_metro('chicago')` passes — every figure → a source row,
   freshness floor met.

---

## Deviations from the questionnaire

- **`metros` table mirrors the toml; toml is the authoring surface** `[B2c]`. The
  table exists for SQL joins + `getStaticPaths`; never hand-edit the table — edit the
  toml and `sync_metros()`.
- **`/` redirects to `/chicago` for the duration of v2.0.** The real homepage city
  directory is built in v2.1 `[D1d]`; shipping it here would couple foundation to
  product surface.
- **Modeling carry-overs (GTFS-RT, transit-leg access, equity) are NOT in v2.0** —
  they ride v2.5 `[L*]`. v2.0 only re-homes v1's existing pillars.

## File map (new/changed)

```
metros/chicago.toml                          (new)  authored truth
metros/_schema.md                            (new)  the toml contract
pipeline/metros.py                           (new)  config loader + validators
pipeline/checks.py                           (new)  verify_metro data-integrity gate
pipeline/{gtfs,census,funding,hiring,access,tiles,load,bronze}.py (mod) --metro
pipeline/selftest.py                         (mod)  config + dry-run + verify checks
data/bronze/chicago/...                       (mv)  per-metro receipts + manifest
transform/models/**/*.sql                    (mod)  metro_id + var('metro')
transform/{dbt_project.yml, tests/*, **/_*.yml} (mod) composite keys + metro_id tests
db/migrations/<ts>_v2_0_1_metros.sql          (new)
db/migrations/<ts>_v2_0_2_metro_id_backfill.sql (new)
db/schema.sql                                (mod)  metros + metro_id columns
frontend/src/pages/[metro]/*.astro           (new)  dynamic per-metro routes
frontend/src/lib/metros.ts                   (new)  metro list + types
frontend/src/components/*.tsx                 (mod)  metro prop
frontend/src/data/chicago/*.json              (mv)  per-metro data
frontend/src/pages/{index,funding,hiring}.astro (del/redirect)
.github/workflows/nightly.yml                (mod)  per-metro matrix + freshness floor
```
