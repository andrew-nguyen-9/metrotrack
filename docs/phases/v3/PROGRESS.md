# v3 — Progress Ledger (final)

Phase **v3 shipped.** All 16 units landed; `main` fast-forwarded via a `--no-ff`
phase merge and tagged `v3.0.0`. This is the closing ledger — the live build state
lived in the orchestrator's working memory (`.orchestrator/`, distilled into
[`ARCHIVE.md`](ARCHIVE.md)).

## Unit status (all done)

| Unit | id | Wave | Commit | Notes |
|------|----|------|--------|-------|
| Pipeline repair | e0 | 1 | a8362ef | 3 bugs: DB percent-crash (code-side conninfo), Vercel double-nest, hiring transient |
| Design system + shell + toggles | e1 | 1 | 16c4402 | token spine + component kit + Nav/Footer + theme/a11y toggles |
| Homepage + directory | e2 | 2 | 77dd34a | national `/` + 10 metro cards (1 live, 9 soon) |
| Transit data coverage | e3a | 2 | d19af25 | full CTA/Metra/Pace in sample, tiles, spine |
| Map UI: filters + search + UX | e3b | 2 | 33965fc | agency/mode filters, route/stop search, map polish |
| Job-access page | e5 | 2 | 4a9aea3 | H3 choropleth on `gold_hex_access` score |
| Ridership | e6 | 2 | f934527 | CTA by line + by stop (Socrata) |
| Finance depth | e8 | 2 | 51e9cf3 | capital/opex, per-mode, per-capita, farebox trend + new analyses |
| Demographic change | e9 | 2 | 76d9d92 | ACS ≥2 vintages |
| TOD | e10 | 2 | 9ffaac5 | density + growth + time-to-CBD; multi-CBD schema |
| Articles | e12 | 2 | 1225a3f | MDX collection, general + region index |
| About + methodology | e13 | 2 | 3f6e26b | `/about` + `/methodology` |
| GTFS-RT / live feed endpoint | e4a | 3 | 0170aef | server-side `/api/live/<metro>`, keys hidden, E11 sampler |
| Live layer + arrivals | e4b | 3 | 3eb8175 | live vehicle GeoJSON layer + next-arrivals panel |
| Service-coordination | e7 | 3 | 556a6f7 | PostGIS cross-agency stop-pairs, static JSON |
| Utilization + delays | e11 | 3 | db25075 | delayed-share + wait histogram + bunching proxy |
| Deep QA sweep | e14 | 4 | — | CLEAN — 0 bugs, no commit |

## Integration + land

- **Wave-2 integration** → `v3` 558e200 (selftest 45, dbt 138/138).
- **Wave-3 integration** → `v3` 7ce0e42 (selftest 52, dbt 146/146). Merge order
  e4a→e4b→e11→e7 (dep order); 1 conflict resolved: `DATA_SOURCES.md` UNION → 26 rows.
- **Session D (review & land):** verified load-bearing receipts against committed
  code, 3 isolated domain reviews, fixed 1 finding (duplicate migration timestamp,
  `3aee3eb`), then `main` ← `--no-ff` merge of `v3` (`53afb9c`), tag **`v3.0.0`**,
  pushed.

## Final gates (green on the landed trunk)

- `astro check` 0 errors · `astro build` 17 pages
- `pipeline/selftest.py` **52** checks
- `dbt build --vars '{metro: chicago}'` **146/146**
- client-bundle leak-scan clean (no CTA keys / DB URL)
- RLS on new tables (`cbds`, `hex_tod` public-read; `routes`/`stops` gained a `mode`
  column, inherit existing policy)
- Lighthouse mobile ≥96

## Accepted known-limitations (documented, not bugs)

- **e4b** — CTA rail *platform* stops (id 30xxx) return no arrivals: the e4a
  `stations` param is map-id (4xxxx) only. Bus stops (majority) work; rail degrades
  to an empty state.
- **e11** — the delays page shows a zero-sample "coming" `DataState` locally; no
  cron/CTA keys means no samples accumulate. Logic is TDD'd in selftest. Rebuild
  after real samples: `uv run --python 3.12 python pipeline/delays.py`.
- **e0** — the live-DB upsert is unverifiable locally (Supabase host is IPv6-only,
  no route from the dev box); the pre-network percent-crash is fixed. CI/pooler has
  IPv4.
- **astro** — 7 pre-existing hints (`z` deprecation from `astro:content`), cosmetic.

## Gotchas for future sessions

- **dbt needs Python 3.12.** Local `uv` defaults to CPython 3.14, which breaks dbt
  (mashumaro `UnserializableField`). Always `uv run --python 3.12 ...`. CI pins 3.12.
- Fresh worktrees need `npm install` in `frontend/` before `astro check`.
- Secrets (`CTA_*`, `SUPABASE_A_DB_URL`, `VERCEL_*`, `SMTP_*`, optional `ORS_API_KEY`)
  come from local `.env` (dev) + GitHub Actions secrets (CI). None in the bundle —
  the live feed's keys stay server-side in `frontend/src/pages/api/live/[metro].ts`
  (`prerender = false`).
- **Delays need a running feed.** Until the nightly cron + CTA keys accumulate live
  samples, the delays page renders its "coming" state by design.
