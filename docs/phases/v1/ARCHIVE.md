# v1 — Phase Archive

The v1 release: a neutral, public Chicagoland transit accountability tracker with
four pillars shipped end-to-end (bronze → dbt silver/gold → Supabase spine → Astro +
islands), merged to `main` and tagged `v1.0.0`.

## What shipped

| Phase | Pillar | Surface | Key data |
|---|---|---|---|
| v1.0 | Foundation | PMTiles map (routes + stops) | GTFS (CTA/Pace/Metra) → PostGIS spine |
| v1.1 | Mapping | Jobs + population hex choropleth overlay | Census LODES8 + 2020 Centers of Population → H3 res-8 |
| v1.2 | Funding | ECharts budget-vs-actual `/funding` + table | FTA NTD audited actuals + RTA Adopted 2025 Budget (committed PDF receipt) |
| v1.3 | Hiring | ECharts vacancy-trend `/hiring` + weekly cron | Open postings: CTA (Taleo) 13, Metra (Cadient) 21, Pace (Oracle Recruiting) 57 — 2026-06-27 |
| v1.4 | Access score | Walkshed job-access hex overlay + legend + table | ½-mi great-circle walkshed over v1.1 hex jobs; ORS isochrone loader wired |

Supabase Project A tables (all RLS public-read, advisors clean): `authorities`,
`routes`, `stops`, `hex_metrics`, `agency_finances`, `vacancy_postings`, `hex_access`.

## Decisions (resolved with documented defaults)

- **Funding** — two-source budget-vs-actual: NTD actuals (reproducible Socrata) +
  RTA adopted budget (PDF-only → transcribed with committed PDF + `SOURCE.md` receipt,
  reconciled against the document's printed total). NITA reallocation figure **omitted**
  (unverified). Cross-source definitional gap disclosed, not hidden.
- **Hiring** — published metric is **open-postings count** (each ATS's reliable signal),
  not a vacancy rate (no clean budgeted-headcount source) and not the service-shortfall
  headline (needs GTFS-rt). Weekly GitHub Actions cron appends snapshots; no prod deploy.
- **Access** — no `ORS_API_KEY` configured, so the published ambient metric is a
  **straight-line ½-mi walkshed** (honest, reproducible); the ORS network-isochrone
  loader is built + unit-tested against a committed schema fixture (test-only, no
  synthetic figure published) and activates when a key is set.

## Deviations from the original plan

- Each phase branched off the **previous** phase branch (v1.4→v1.3→v1.2→v1.1→v1.0→main),
  not main — v1 merges to main only at phase close (this archive).
- **Full GTFS transit-routing access score deferred** (the ACCESS_SCORE "spike":
  r5py/OTP) — beyond the free-tier/v1 budget. v1 ships walk access.
- **ECharts** added as a frontend dep (tree-shaken; funding ~167 KB gz, a documented
  per-page JS-budget overage like the map page — charting libs need the weight).
- **Playwright** added for the JS applicant-tracking systems (lazy-imported; the pure
  selftest stays dependency-free).

## Per-phase gate evidence (at close, on v1.4)

`python pipeline/selftest.py` → PASS (22 checks) · `cd transform && dbt build` →
PASS=50, 0 ERROR · `cd frontend && npm run check` 0 errors + `npm run build` 3 pages ·
`get_advisors` (Project A, security) clean · local-prod Lighthouse a11y = 100 on
`/`, `/funding`, `/hiring`.

## Follow-ups (seed v2)

See [`../../brainstorming/v2-ideas.md`](../../brainstorming/v2-ideas.md): GTFS-rt
delivered-service → service-shortfall headline; ORS/transit network isochrones with a
key; ACS equity overlay; per-capita access normalization; nightly funding/hiring/access
export wired into the production refresh.
