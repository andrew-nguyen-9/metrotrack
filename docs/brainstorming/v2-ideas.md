# v2 — Ideas / Backlog

Seeded at v1 close (see [`../phases/v1/ARCHIVE.md`](../phases/v1/ARCHIVE.md)). Not a
plan — candidates for the next cycle. Promote into `docs/phases/v2/` when chosen.

## Carry-overs deferred from v1 (highest signal)

- **Service-shortfall headline** (UNDERSTAFFING_METRIC's chosen metric) — ingest
  GTFS-realtime / published delivered-service vs. scheduled; pairs with the v1.3 vacancy
  series for the credible staffing story.
- **Network / transit access score** — set `ORS_API_KEY`, batch-precompute ORS walk
  isochrones nightly; the v1.4 loader is already wired. Then the GTFS transit-leg spike
  (r5py / OpenTripPlanner) for schedule-aware "jobs reachable by transit" (the true
  ACCESS_SCORE definition).
- **Wire funding/hiring/access into the nightly refresh + production deploy** — v1 ships
  committed JSON; the nightly should regenerate `funding.json`/`hiring.json`, reload gold,
  and redeploy (the hiring-weekly cron intentionally does not deploy).

## Modeling / data depth

- **ACS equity overlay** (G7) — access vs income / race / vehicle-access: *who* has access.
- **Per-capita access normalization** (G10) — surface the deficit, not just raw counts.
- **NITA reallocation explainer** — once the dollar figures are primary-sourced + verified.
- **Capital-project tracker** (RTAMS) — status/budget/delay on a map.

## Reliability / scale

- Statewide (beyond Cook County) — the `--vars` swap exists; validate tile size + the
  O(n²) walkshed join (add an H3 k-ring prefilter / spatial index).
- Freshness-floor checks for the funding/hiring/access loaders (the nightly has one for GTFS).

## UI

- Light/dark theme toggle (tokens exist; no toggle shipped in v1).
- On-demand isochrone bloom + reachable-jobs count-up (the ACCESS_SCORE signature motion).
