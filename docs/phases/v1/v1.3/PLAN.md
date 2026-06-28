# v1.3 — Hiring Pillar — Implementation Plan

> **For workers:** dependency-ordered segments; each is a branch off `v1.3`,
> merged back when its acceptance criteria pass. Pure logic (HTML/JSON parsing,
> append/dedup math) is TDD via `pipeline/selftest.py`. Follow
> [`../../../WORKFLOW.md`](../../../WORKFLOW.md) and
> [`../../../DEFINITION_OF_DONE.md`](../../../DEFINITION_OF_DONE.md).

**Goal:** A hiring dashboard whose product *is the time series* — **open job
postings per authority (CTA, Metra, Pace), snapshotted weekly** — as an Apache
ECharts trend island with an accessible table fallback. It renders honestly with
whatever snapshots exist (1–2 points now; the trend thickens over weeks). A weekly
GitHub Actions cron appends new snapshots.

**Architecture:** Same medallion path. A weekly scrape lands an append-only snapshot
row per authority in content-hashed bronze; dbt silver types + dedups (one row per
authority × date), gold shapes the serving time series; a migration adds
`public.vacancy_postings` (RLS public-read); a `hiring_export.py` emits `hiring.json`
for the ECharts island on a `/hiring` page.

**Tech stack:** Python (`urllib`/`requests` for server-rendered listings; **Playwright**
headless for JS applicant-tracking systems — ADR/CLAUDE.md — lazy-imported inside
`fetch_*` so the no-network selftest never needs it); dbt-duckdb; Postgres (Supabase
Project A); Apache ECharts island (Astro).

## Global constraints (every segment)

- **Branch base:** v1.3 off **`v1.2`**. Do **not** merge to `main`; do **not** start v1.4.
- No new client-bundle secrets; RLS public-read on the new table; writes server-side only.
- Bronze is content-hashed + **append-safe** (re-running on the same day replaces that
  day's row, never duplicates).
- **Scrape politely** (DATA_SOURCES rule): descriptive UA, weekly cadence, respect
  robots.txt/ToS; record each source + its robots status in `DATA_SOURCES.md`.
- Every published figure traces to a committed receipt (the saved rendered listing).
- Commits: `<type>(scope): <summary>  [v1.3.s.t]`, no AI attribution.
- ADD via migration; do **not** rewrite v1.0–v1.2 shared columns.

## Locked modeling decisions (ambiguities resolved with documented defaults)

Confirmed against the live web (2026-06-27): robots.txt for `transitchicago.com`
allows `/careers/`; `pacebus.com` allows `/careers`; `metra.com` returns 403 to
generic clients and recruits via the public **Cadient** ATS.

| Decision | Default chosen | Why |
|---|---|---|
| **Headline metric (v1.3)** | **Open job postings** (absolute count) per authority, weekly snapshot | The prompt's deliverable is the *scrape → vacancy time series*; the count is directly observable from each authority's listing and needs no second source. |
| **Vacancy *rate*** (`open / budgeted`) | **Deferred** — no clean primary budgeted-headcount source (FOIA/board-doc bound, per UNDERSTAFFING_METRIC.md) | Publishing a rate would need an unsourced denominator. Absolute postings is honest by construction; the rate lands if/when a budgeted-headcount receipt exists. |
| **Service-shortfall headline** | **Deferred** to a later segment/phase | [`UNDERSTAFFING_METRIC.md`](../../../modeling/UNDERSTAFFING_METRIC.md) names service-shortfall the *eventual* headline, but it needs GTFS-realtime / published delivered-service data not yet ingested. v1.3 ships the secondary **vacancy-postings** series the same doc prescribes; the page says so plainly. |
| **Sources** | CTA → `chicagotransit.taleo.net` (Taleo); Metra → `cta.cadienttalent.com` (Cadient, `MetraKTMDReqExt`); Pace → `pacebus.com/careers` (Drupal view) | Each authority's own public listing is the primary source for its own postings. |
| **Fetch method** | Server-rendered HTML via HTTP where possible (Pace); **Playwright** headless render for JS ATSs (CTA Taleo, Metra Cadient). Parser is pure + tested on a committed rendered sample. | Robust enough for a weekly cron; the saved rendered listing is the receipt. |
| **Seed snapshot** | Captured **2026-06-27** via the available browser (renders the JS ATSs), saving each rendered listing as the bronze receipt | Gives ≥1 honest, dated point per authority now; the cron grows the series. An authority that cannot be fetched honestly is recorded "scrape pending" and omitted (honest by construction), not guessed. |
| **Snapshot grain** | `{authority_id, as_of (date), open_postings (int), source_url, method}` — append-only, one row per authority × date | Minimal, dated, comparable. |
| **Chart** | ECharts **line** (open postings over time), one line per authority; renders points when only 1–2 snapshots exist | The trend is the product; lines read the accumulation over weeks. |
| **Non-color signal** | Per-authority line distinguished by label + marker symbol + the table; legend names each; tooltip shows exact counts + as-of | DoD: color never the only signal. |

---

## Segments (dependency-ordered)

### v1.3.1 — Plan + data-source receipts (this doc)

**Files:** this plan; `DATA_SOURCES.md` (refine the career-pages row → per-authority
source + robots status + verified date).

**Acceptance:** plan committed; DATA_SOURCES rows present.

### v1.3.2 — Hiring scraper + seed snapshot

**Files:**
- Create: `pipeline/hiring.py` — pure `parse_*(rendered) -> count` per source +
  `fetch_*` (urllib / lazy Playwright) + append-safe `snapshot()`.
- Modify: `pipeline/selftest.py` — pure-parser + append/dedup checks.
- Create (committed receipts): `data/bronze/hiring/postings.csv` (append-only snapshot
  log) + `data/bronze/hiring/samples/*.html` (rendered listing receipts) + parquet + manifest.

**Approach (TDD on the pure parts):**
- `parse_taleo`, `parse_cadient`, `parse_pace` extract the open-req **count** from each
  rendered listing (count job rows or read the printed total). Tested on committed samples.
- `append_snapshot(existing_csv, rows, today) -> csv` — adds today's rows, replaces a
  same-date row (idempotent), keeps history. Pure + tested.
- `snapshot()` fetches each source, parses the count, appends to `postings.csv`, and
  `bronze.ingest_csv` → parquet. `fetch_*` is network/Playwright, out of selftest.

**Acceptance:** `python pipeline/selftest.py` green incl. parser + append-dedup checks;
re-running `snapshot()` same day does not duplicate; committed `postings.csv` has ≥1
real dated row per fetchable authority; rendered samples committed.

### v1.3.3 — Vacancy time series in dbt (silver + gold)

**Files:**
- Create: `transform/models/silver/silver_vacancy.sql` (typed, one row per
  authority × as_of), `transform/models/gold/gold_vacancy.sql` (serving series).
- Modify: `_silver.yml`, `_gold.yml`. Create
  `transform/tests/assert_silver_vacancy_unique.sql`,
  `assert_silver_vacancy_nonneg.sql`.

**Acceptance:** `dbt build` green incl. new tests; one row per authority × date; counts ≥ 0.

### v1.3.4 — Supabase table (migration to Project A)

**Files:** `db/migrations/<ts>_v1_3_4_vacancy_postings.sql`; `db/schema.sql` snapshot;
`pipeline/load.py` upsert.

**Approach:** `public.vacancy_postings (authority_id text, as_of date, open_postings int,
source_url text, primary key (authority_id, as_of))`; RLS enable + public-read policy;
`load.py` `VACANCY_UPSERT` on conflict (authority_id, as_of).

**Acceptance:** migration applied; `list_tables` shows RLS-enabled table; `get_advisors`
(security) clean; upsert idempotent.

### v1.3.5 — Weekly cron

**Files:** Create `.github/workflows/hiring-weekly.yml` (mirror `nightly.yml`).

**Approach:** weekly `schedule:` cron → set up Python + Playwright → `python
pipeline/hiring.py` (snapshot) → commit the updated `postings.csv`/parquet → trigger
redeploy. Resilient: an authority that fails to fetch is skipped that week, not fatal.

**Acceptance:** workflow validates (yaml + step commands); a failed single-authority
fetch does not fail the run.

### v1.3.6 — Vacancy-trend ECharts island

**Files:** Create `pipeline/hiring_export.py` (gold → `frontend/src/data/hiring.json`),
`frontend/src/lib/hiring.ts`, `frontend/src/components/VacancyChart.tsx`,
`frontend/src/pages/hiring.astro`; modify `frontend/src/layouts/Base.astro` (nav link).

**Approach:** ECharts line island (`client:visible`), reduced-motion (animation off),
keyboard-reachable, non-color encoding (markers + legend + table), honest empty/sparse/
error states. Page carries the UNDERSTAFFING_METRIC caveat (postings ≠ understaffing;
service-shortfall headline pending) + per-figure source + as-of.

**Acceptance:** `npm run build` green + `npm run check` 0 errors; chart renders the
series (even at 1–2 points); table fallback present; caveat + sources shown.

### v1.3.7 — QA + performance + gate

Same as v1.2.6: chrome-devtools at 360/768/1280/1920, reduced-motion, local-prod
Lighthouse a11y ≥ 90; `/code-review --fix` on the v1.3 diff;
`superpowers:verification-before-completion` before the marker.

**Acceptance (phase GATE — all pass, output pasted):**
1. `python pipeline/selftest.py` green.
2. `cd transform && dbt build` green (new vacancy models + tests).
3. `cd frontend && npm run build` green + `npm run check` 0 errors.
4. `get_advisors` (Project A, security) clean — RLS on `vacancy_postings`.
5. Island renders with legend + table fallback, verified at 4 widths, Lighthouse a11y ≥ 90.

Then emit: **HIRING PILLAR GATE GREEN**.

---

## Deviations / notes

- **Postings, not a rate or shortfall, is the v1.3 headline** — the only figure with a
  clean primary source now. The page states this plainly (honest by construction); the
  service-shortfall headline (UNDERSTAFFING_METRIC) lands when GTFS-rt/delivered data is ingested.
- **Playwright** is added for the JS ATSs, lazy-imported so the pure selftest stays no-dep.

## File map (new/changed)

```
pipeline/hiring.py                          (new)  scrapers + pure parsers + snapshot
pipeline/selftest.py                        (mod)  + hiring parser/append checks
pipeline/hiring_export.py                   (new)  gold → hiring.json
pipeline/load.py                            (mod)  + vacancy upsert
transform/models/silver/silver_vacancy.sql  (new)
transform/models/gold/gold_vacancy.sql      (new)
transform/models/silver/_silver.yml         (mod)
transform/models/gold/_gold.yml             (mod)
transform/tests/assert_silver_vacancy_*.sql (new)
db/migrations/<ts>_v1_3_4_vacancy_postings.sql (new)
db/schema.sql                               (mod)  + vacancy_postings snapshot
data/bronze/hiring/postings.csv             (new)  append-only snapshot log (receipt)
data/bronze/hiring/samples/*.html           (new)  rendered listing receipts
.github/workflows/hiring-weekly.yml         (new)  weekly snapshot cron
frontend/src/lib/hiring.ts                  (new)
frontend/src/components/VacancyChart.tsx    (new)  ECharts trend island
frontend/src/pages/hiring.astro             (new)  hiring page + table fallback
frontend/src/layouts/Base.astro             (mod)  nav link
```
