# v1.2 — Funding Pillar — Implementation Plan

> **For workers:** dependency-ordered segments; each is a branch off `v1.2`,
> merged back when its acceptance criteria pass. Pure logic (parsing, reconciliation
> math) is TDD via `pipeline/selftest.py`. Follow
> [`../../../WORKFLOW.md`](../../../WORKFLOW.md) and
> [`../../../DEFINITION_OF_DONE.md`](../../../DEFINITION_OF_DONE.md).

**Goal:** A funding dashboard — **operating budget vs. actual operating expense**
per service board (CTA, Metra, Pace) over recent years, as an **Apache ECharts**
island with an accessible table fallback. Every figure traces to a committed
primary-source receipt in `data/bronze/` and a `DATA_SOURCES.md` row. Honest by
construction: a figure that cannot be verified from a primary source is **omitted**,
the way `index.astro` omits unsourced numbers.

**Architecture:** Same medallion path as v1.0/v1.1. Two funding sources land in
content-hashed bronze parquet; dbt silver types + reconciles them into one tidy
`(authority, fiscal_year, metric, budget, actual)` grain; gold is the serving shape
(adds derived variance + farebox-recovery where the inputs exist). A timestamped
migration adds `public.agency_finances` (RLS public-read) to Project A; `load.py`
upserts gold into it. A new `funding.json` export feeds an ECharts island on a
dedicated `/funding` page, with a no-JS table fallback.

**Tech stack:** Python (`urllib` + DuckDB, no pandas — matches `pipeline/bronze.py`);
dbt-duckdb; PostGIS/Postgres (Supabase Project A); **Apache ECharts** (new frontend
dep) in a React island (Astro, `client:only`/`client:visible`).

## Global constraints (every segment)

- **Branch base:** v1.2 is branched off **`v1.1`** (each phase branches off the
  previous; v1 merges to `main` only at the very end — a human step). Do **not**
  merge to `main`; do **not** start v1.3.
- No new client-bundle secrets; RLS public-read on every new table; service-role /
  direct-Postgres writes server-side only.
- Bronze is content-hashed + append-safe; loaders idempotent + re-runnable.
- **HARD RULE (CLAUDE.md):** every funding/governance figure traces to a committed
  primary-source receipt in `data/bronze/` + a `DATA_SOURCES.md` row; current-events
  claims are verified against the primary source; unverifiable figures are not shipped.
- Commits: `<type>(scope): <summary>  [v1.2.s.t]`, no AI attribution.
- ADD via migration; do **not** rewrite v1.0/v1.1 shared schema columns.

## Locked modeling decisions (ambiguities resolved with documented defaults)

The funding pillar's risk is **data provenance**, not engineering. These defaults
were chosen autonomously (per the phase prompt: pick a documented default, don't
block) after confirming source availability on the live web (2026-06-27).

| Decision | Default chosen | Why |
|---|---|---|
| **Actual operating expense** | FTA **National Transit Database (NTD)** "Annual Data View — Metrics (by Agency)", DOT Socrata dataset `g27i-aq2u` (`sum_total_operating_expenses`, `sum_fare_revenues_earned`, `sum_unlinked_passenger_trips` by `max_agency` × `report_year`) | **Key-free, structured, multi-year, fetchable** (Socrata JSON/CSV API) → fully reproducible bronze, the v1.1 gold standard. Audited actuals. Also carries fare revenue + trips → derived recovery/$-per-rider later. |
| **Budgeted operating expense** | **RTA adopted Operating Budget** by service board × year, transcribed from the official RTA budget book / quarterly financial report (PDF) | The RTA publishes adopted budgets **PDF-only** — confirmed no structured export exists (rtachicago.org/transit-funding/financial-documents). Figures are few, high-level, and **exactly quoted** from the cited table; the source citation (doc title, URL, page, as-of) is committed beside the CSV as the receipt. |
| **Source mismatch handling** | Disclose the two-source split + the definitional caveat on the chart and in `DATA_SOURCES`; never plot them as if identically defined | NTD "operating expenses" (audited) and RTA "budgeted operating expenses" differ slightly in scope. Honest by construction = disclose, don't hide. |
| **Authorities** | **CTA, Metra, Pace** (the three service boards). RTA regional total only if cleanly sourced both sides. | The three service boards are the comparison the public cares about; NITA is a governance overlay, not a separate budget line yet. |
| **NITA reallocation figure** | **Omitted from v1.2** until verified against primary legislation/RTA documents | VISION ⚠️ + CLAUDE.md: the "$1.5B question" dollar figure is a placeholder until primary-sourced. The dashboard ships honest without it; it lands as a sourced explainer later. |
| **Year span** | Actual: whatever NTD publishes (≈ last 5–8 years); Budget: the most recent cycle(s) the RTA book reports. Chart shows budget vs actual where both exist; actual-only (trend) for earlier years. | Maximizes the reproducible (NTD) series; keeps transcription minimal. The trend "thickens" toward recent years where both exist. |
| **Derived metrics** | `variance = actual − budget` (and `variance_pct`); farebox recovery = `fare_revenue / operating_expense` from NTD. Both computed in gold, not the client. | Cheap, useful, sourced. Keeps the client dumb. `$/rider` etc. deferred (YAGNI for v1.2). |
| **Surface** | A dedicated **`/funding`** page (VISION lists "Funding dashboard" as a top-level page) with the ECharts island + table fallback; a nav link from the layout. | Keeps `index.astro` the map landing; funding gets room for the chart + caveats + sources. |
| **Chart type** | ECharts **grouped bars** (budget vs actual) faceted/selectable **per service board**, fiscal year on the category axis | Matches v1-ideas "budget vs actuals small-multiples per authority"; bars compare two series per year cleanly. |
| **Non-color signal** | Budget vs actual distinguished by **label + axis + pattern/border**, not color alone; exact values in tooltip + the table fallback | DoD: color is never the only signal. |

---

## Segments (dependency-ordered)

### v1.2.1 — Plan + data-source receipts (this doc)

**Files:** `docs/phases/v1/v1.2/PLAN.md` (this); `docs/architecture/DATA_SOURCES.md`
(add NTD row; refine RTAMS/RTA + NITA rows with the budget-book citation + verified
status once the figures are committed in v1.2.2).

**Acceptance:** plan committed; DATA_SOURCES has rows for both funding series.

### v1.2.2 — Funding bronze loaders (actual + budget)

**Files:**
- Create: `pipeline/funding.py` — pure parsers + `fetch_*` + `ingest`.
- Modify: `pipeline/selftest.py` — pure-parser + reconciliation checks.
- Create (committed receipts): `data/bronze/ntd/operating.parquet` (CTA/Metra/Pace
  subset), `data/bronze/rta/budget.parquet`, `data/bronze/rta/SOURCE.md` (exact RTA
  citation + quoted figures) + manifest rows.

**Approach (TDD on the pure parts):**
- `parse_ntd(json_bytes) -> csv` — keep the three Chicago service boards (match by
  `max_agency`/`ntd_id`, `max_state == "IL"`), emit
  `authority_id,fiscal_year,operating_expense,fare_revenue,unlinked_trips`.
  `authority_id` normalized to `cta`/`metra`/`pace` (the v1.0 vocabulary).
- `fetch_ntd()` — `urllib` GET the Socrata JSON (`$where`/`$limit`), key-free; goes
  through `bronze.ingest_csv` (content-hashed, idempotent).
- `parse_rta_budget(csv_bytes) -> csv` — validate/normalize the transcribed RTA budget
  CSV (`authority_id,fiscal_year,operating_budget`); a `reconcile()` check asserts the
  service-board figures sum to the regional total within rounding (catches a fat-finger).
- The RTA budget CSV is committed as the bronze sample; `SOURCE.md` records the doc
  title, URL, page, accessed date, and the exact quoted figures (the primary receipt).

**Acceptance:**
- `python pipeline/selftest.py` green incl. new checks: NTD agency filter + authority
  normalization + field selection; RTA budget parse + reconciliation; header-whitespace
  tolerant.
- Re-running loaders on identical bytes does **not** rewrite parquet (idempotent).
- `data/bronze/ntd/*.parquet`, `data/bronze/rta/*` committed with manifest receipts;
  rows > 0; `SOURCE.md` present with citation.

### v1.2.3 — Funding in dbt (silver + gold)

**Files:**
- Create: `transform/models/silver/silver_funding.sql` — type both sources; one tidy
  row per `(authority_id, fiscal_year)` carrying `operating_budget`, `operating_actual`,
  `fare_revenue`, `unlinked_trips` (NULL where a side is absent).
- Create: `transform/models/gold/gold_funding.sql` — serving shape + derived
  `variance`, `variance_pct`, `farebox_recovery`.
- Modify: `_silver.yml`, `_gold.yml` — model docs + tests.
- Create: `transform/tests/assert_silver_funding_unique.sql` (one row per
  authority+year), `transform/tests/assert_silver_funding_nonneg.sql`
  (budget/actual ≥ 0 when present).

**Approach:** silver full-joins NTD actuals to RTA budget on `(authority_id,
fiscal_year)`; gold computes `actual − budget`, `recovery = fare_revenue /
nullif(operating_actual,0)`.

**Acceptance:** `cd transform && dbt build` green incl. the new schema tests; row
counts sane (3 authorities × N years); no negative/null-key rows.

### v1.2.4 — Supabase table (migration to Project A)

**Files:**
- Create: `db/migrations/<ts>_v1_2_4_agency_finances.sql`.
- Modify: `db/schema.sql` — append the snapshot.
- Modify: `pipeline/load.py` — upsert gold funding rows.

**Approach:**
- Table `public.agency_finances (authority_id text, fiscal_year int, operating_budget
  bigint, operating_actual bigint, fare_revenue bigint, unlinked_trips bigint,
  variance bigint, variance_pct double precision, farebox_recovery double precision,
  primary key (authority_id, fiscal_year))`.
- RLS enable + public-read SELECT policy for `anon, authenticated` (mirror v1.0/v1.1).
- Apply via `supabase` MCP `apply_migration`; `get_advisors` (security) clean.
- `load.py` gains `FINANCE_UPSERT` (insert … on conflict (authority_id, fiscal_year)
  do update) reading `gold_funding`.

**Acceptance:** migration applied; `list_tables` shows `agency_finances` RLS-enabled;
`get_advisors` (security) returns no new ERROR/WARN; `load.py` upserts idempotently.

### v1.2.5 — Funding export + ECharts island

**Files:**
- Create: `pipeline/funding_export.py` — query `gold_funding` → `frontend/src/data/funding.json`.
- Modify: `frontend/package.json` — add `echarts`.
- Create: `frontend/src/lib/funding.ts` — types + label/format helpers.
- Create: `frontend/src/components/FundingChart.tsx` — ECharts grouped budget-vs-actual
  bars; service-board selector; reduced-motion (no animation); keyboard-reachable
  controls; non-color encoding (labels/pattern); tooltip with exact values + source.
- Create: `frontend/src/pages/funding.astro` — page shell, intro + caveat + source
  lines, the island, and an accessible table fallback (budget/actual/variance per
  authority × year).
- Modify: `frontend/src/layouts/Base.astro` — nav link to `/funding`.

**Approach:** `funding_export.py` mirrors `tiles.py`'s JSON write (read DuckDB gold,
dump tidy records + per-authority series + as-of). Island `client:visible`; ECharts
imported in the island only (keeps it off other pages). Empty/loading/error states
render gracefully with no data.

**Acceptance:** `cd frontend && npm run build` green, `npm run check` 0 errors; chart
renders budget vs actual with the authority selector; table fallback present with the
same numbers; every figure shows a source + as-of.

### v1.2.6 — QA + performance + gate

**Approach:**
- `chrome-devtools` at **360 / 768 / 1280 / 1920**: no overflow, chart + table legible,
  controls keyboard-reachable, focus visible, light/dark correct.
- Reduced-motion verified (chart animation disabled under the media query).
- Local production build (`npm run build && npm run preview`) → `lighthouse_audit`:
  **a11y ≥ 90**. A Vercel preview reaching READY proves the remote build (do not
  weaken SSO; do not promote to prod).
- `/code-review --fix` on the full v1.2 diff; resolve real findings.
- `superpowers:verification-before-completion` before emitting the gate phrase.

**Acceptance (the phase GATE — all must pass, output pasted):**
1. `python pipeline/selftest.py` green.
2. `cd transform && dbt build` green (new funding models + tests).
3. `cd frontend && npm run build` green + `npm run check` 0 errors.
4. `supabase get_advisors` (Project A, security) clean — RLS on `agency_finances`.
5. Funding island renders with selector + table fallback, verified via chrome-devtools
   at 4 widths, Lighthouse a11y ≥ 90.

Then emit: **FUNDING PILLAR GATE GREEN**.

---

## Deviations / notes

- **Two-source budget-vs-actual.** No structured RTA budget export exists (PDF only),
  so actual (NTD, reproducible) and budget (RTA, transcribed-with-citation) come from
  different sources; the definitional difference is disclosed, not hidden.
- **NITA reallocation deferred** to a sourced explainer (VISION ⚠️ / CLAUDE.md).
- **`$/rider` and ratio trends deferred** (YAGNI for v1.2; the inputs are in NTD for
  a later segment).

## File map (new/changed)

```
pipeline/funding.py                         (new)  NTD + RTA loaders + pure parsers
pipeline/selftest.py                        (mod)  + funding parser/reconcile checks
pipeline/funding_export.py                  (new)  gold → funding.json
pipeline/load.py                            (mod)  + agency_finances upsert
transform/models/silver/silver_funding.sql  (new)
transform/models/gold/gold_funding.sql      (new)
transform/models/silver/_silver.yml         (mod)
transform/models/gold/_gold.yml             (mod)
transform/tests/assert_silver_funding_*.sql (new)
db/migrations/<ts>_v1_2_4_agency_finances.sql (new)
db/schema.sql                               (mod)  + agency_finances snapshot
data/bronze/ntd/operating.parquet           (new)  NTD CTA/Metra/Pace receipt
data/bronze/rta/budget.parquet              (new)  RTA budget receipt
data/bronze/rta/SOURCE.md                   (new)  RTA primary-source citation
frontend/package.json                       (mod)  + echarts
frontend/src/lib/funding.ts                 (new)  types + formatters
frontend/src/components/FundingChart.tsx    (new)  ECharts island
frontend/src/pages/funding.astro            (new)  funding dashboard page
frontend/src/layouts/Base.astro             (mod)  nav link
```
