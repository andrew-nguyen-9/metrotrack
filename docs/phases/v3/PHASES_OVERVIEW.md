# v3 Phases — Overview

Phase **v3** = "the full public product": finish v2's unbuilt site shell, add the
new data/editorial/live epics, and land a full design overhaul. Versioning:
`v[phase].[segment].[task]` ([`../../VERSIONING.md`](../../VERSIONING.md)).

Unlike v1/v2 (segment sub-branches, one long session), v3 was built by a
**multi-agent orchestrator**: 16 units across 4 dependency waves, each on its own
`v3.<id>` worktree branch, merged into the `v3` integration branch, then landed to
`main` as one `--no-ff` phase merge tagged `v3.0.0`. The orchestrator contract and
per-unit receipts are archived in [`ARCHIVE.md`](ARCHIVE.md); the landing ledger is
[`PROGRESS.md`](PROGRESS.md).

> **v3 theme — ship the whole product for Chicago.** Chicago stays the sole live
> metro; the other 9 regions render as greyed "coming soon" cards (no real
> onboarding this phase). Every published figure still traces to a
> [`DATA_SOURCES.md`](../../architecture/DATA_SOURCES.md) row; data-blocked features
> ship a scaffold + honest "data coming" state rather than a fabricated number.

## Scope at a glance

| In v3 | Out of v3 (deferred) |
|---|---|
| New design system + rebuild every page | Real SF/NYC (or other) metro onboarding |
| Homepage + metro directory | Auth / accounts · paid tiers |
| Full CTA bus+rail + Metra + Pace map coverage + filters + search | Embeddable widgets · email digest |
| Live CTA vehicle layer + next-arrivals (Bus/Train Tracker) | Non-US metros |
| Job-access page (real `gold_hex_access` scores) | deck.gl migration (no epic needed it) |
| Ridership · finance depth · demographic change · TOD | |
| Service-coordination (PostGIS cross-agency spatial join) | |
| Utilization + delays (from the live feed) | |
| Articles (MDX content collection) · About · Methodology | |
| A11y toggles: theme, reduce-motion, text-size, colorblind palette | |

## Epics → units (waves)

Session B split each epic into build units; the orchestrator ran them in
dependency waves. `s` = segment number used in commit tags.

| Epic | Unit(s) | s | Wave | What |
|------|---------|---|------|------|
| **E0** Pipeline repair | e0 | 0 | 1 | Fix nightly: DB percent-crash (code-side conninfo), Vercel double-nest deploy path, hiring-weekly diagnose |
| **E1** Design system + shell | e1 | 1 | 1 | Token spine, component kit, shell (Nav/Footer), dark/light + a11y toggles; rebuild existing pages |
| **E2** Homepage + directory | e2 | 2 | 2 | National `/` homepage, metro directory grid, per-metro region page |
| **E3** Map overhaul + full scope | e3a, e3b | 3 | 2 | Full CTA/Metra/Pace coverage (e3a data), agency/mode filters + route/stop search + map UX (e3b) |
| **E4** Live CTA tracking | e4a, e4b | 4 | 3 | Server-side live feed endpoint (e4a, keys hidden), live vehicle layer + next-arrivals (e4b) |
| **E5** Job-access page | e5 | 5 | 2 | Export `gold_hex_access` → H3 choropleth + methodology |
| **E6** Ridership | e6 | 6 | 2 | CTA ridership by line + by stop (Socrata) |
| **E7** Service-coordination | e7 | 7 | 3 | PostGIS cross-agency stop-pair spatial join → ranked merge/timing candidates |
| **E8** Financial depth | e8 | 8 | 2 | Granular finance (capital/opex, per-mode, per-capita, farebox trend) + new analyses |
| **E9** Demographic change | e9 | 9 | 2 | ACS change over ≥2 vintages |
| **E10** TOD | e10 | 10 | 2 | Density + growth + time-to-CBD; multi-CBD-capable schema |
| **E11** Utilization + delays | e11 | 11 | 3 | Delayed-share + wait histogram + bunching crowding proxy from the live feed |
| **E12** Articles / editorial | e12 | 12 | 2 | MDX content collection; general + region-filtered index |
| **E13** About + methodology | e13 | 13 | 2 | `/about` + `/methodology` (per-region-capable) |
| **E14** Deep QA sweep | e14 | 14 | 4 | Backend + UI + UX QA across the phase; fix or log |

## Dependency shape (why this wave order)

- **Wave 1 (foundation/independent):** **E0** (unblocks the nightly), **E1** (design
  system — every UI unit inherits it).
- **Wave 2 (inherit E1):** E2, E3, E5, E6, E8, E9, E10, E12, E13 — all page builds,
  parallel-safe once the token/kit spine exists.
- **Wave 3:** E4a (deps E3 data) → E4b (deps E4a) → E11 (deps E4a feed) → E7 (deps E3
  stops). Merged in that dep order.
- **Wave 4:** **E14** deep QA after everything.

## Locked decisions (Session A defaults)

| Concern | Decision |
|---|---|
| **Metro scope** | Placeholders-only. Chicago sole live metro; 9 regions greyed "coming soon". No real onboarding. |
| **Design** | New design system + rebuild all pages (not a reskin of v2). |
| **Data-hard items** | Real where a free source exists, else scaffold + honest "data coming" state. No fabricated figures. |
| **Live tracking** | Live vehicle map layer + next-arrivals via CTA Bus/Train Tracker (free tier); keys server-side only. |
| **A11y toggles** | All three: colorblind-safe palette, reduce-motion, text-size (+ dark/light theme). All persisted. |
| **Articles** | Astro content collection (MDX), no CMS. |
| **Release policy** | Ship-without — a data-blocked unit drops + logs; the phase is not held. |

## Cross-cutting (acceptance criteria in every unit)

Data-integrity (every figure → a `DATA_SOURCES.md` row) · idempotent pipeline · RLS
on every new table · per-segment QA (responsive / a11y / themes / empty-loading-error
/ map-perf) · Lighthouse ≥90 mobile. See
[`../../DEFINITION_OF_DONE.md`](../../DEFINITION_OF_DONE.md).

## Tag

v3 merged `v3` → `main` as a `--no-ff` phase merge and tagged **`v3.0.0`**. Patches
bump the third digit.
