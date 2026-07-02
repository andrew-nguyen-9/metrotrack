# v3 — Archive (orchestrator method + unit receipts)

Historical record of *how* v3 was built and *what each unit shipped*. The raw
working memory lived in the gitignored `.orchestrator/` directory (spec, prd,
depmap, per-unit `.done.md` receipts, handoff); this file is the durable
distillation kept in git.

## Build method — multi-agent orchestrator

v3 was not a single long session. A router sized the phase, Session B split each
epic into small bounded units, and an orchestrator (Session C) dispatched them as
subagents across dependency waves, each in an isolated git worktree
(`../mt-wt/<id>`) on a `v3.<id>` branch off the `v3` integration branch. Session D
reviewed and landed.

**Why small bounded units:** fewer hallucinations than one big prompt, each unit
independently gated, a failure re-executes one unit from its checkpoint (its
`.done.md`) rather than the whole fan-out.

**Integration model:** local-branch-merge (no PRs). Each green unit merged `--no-ff`
into `v3`; the phase landed to `main` as one `--no-ff` merge tagged `v3.0.0`.

### Safeguards that governed the run

- **Notes are claims, not gospel.** A wrong `.done.md` poisons every dependent, so
  dependents (and Session D) verified load-bearing claims against committed code
  (Serena/LSP), not the note alone.
- **Producer-blind review.** Isolated reviewers (separate context) scored output;
  deterministic tests for exact correctness, judgment review only for judgment.
- **Hard verification gate.** No unit advanced without build + selftest + dbt +
  data-integrity (every figure → a source row) green. No loop without a gate.
- **Idempotent units + checkpoints.** Re-running never double-applies; `.done.md` is
  the checkpoint.

### Notable run events

- **Wave-2 529 overload:** all 9 wave-2 agents died on an API 529 (global overload),
  not code failure. Recovery was to resume each agent via its preserved context
  (worktree work intact), not re-create fresh agents.
- **dbt/Python 3.14 trap:** the recurring cross-cutting gotcha injected into every
  backend dispatch — local `uv` defaults to CPython 3.14 which breaks dbt; pin 3.12.

## Unit receipts

Distilled from each `.orchestrator/<id>.done.md`. Commits are on the `v3` history
now in `main`.

### e0 — pipeline repair (a8362ef)
3 nightly bugs. **Bug1 (DB crash):** `load.build_conninfo()` parses the URL with
stdlib `urlsplit` → psycopg keyword conninfo (`make_conninfo`), no percent-decode,
so any raw `%` in the password connects. **Bug2 (Vercel double-nest):** dropped
`working-directory: frontend` from the deploy step — the project Root Directory is
already `frontend`, so deploy runs from repo root. **Bug3 (hiring-weekly):** ran
green e2e locally; the 2026-06-29 failure did not reproduce = transient scrape
timeout, no code fix. Live DB upsert unverifiable locally (host IPv6-only).

### e1 — design system + shell (16c4402)
Field-instrument token spine + component kit + shell (Nav/Footer) + a11y toggles
(dark/light theme, reduce-motion, text-size, colorblind palette), all persisted.
Existing pages rebuilt against the system. Design contract:
[`../../design-system/v3-DESIGN_DIRECTION.md`](../../design-system/v3-DESIGN_DIRECTION.md),
[`v3-KIT.md`](../../design-system/v3-KIT.md), [`TOKENS.md`](../../design-system/TOKENS.md).

### e2 — homepage + directory (77dd34a)
National `/` homepage (hero + national stat band + city directory grid). Chicago =
live full card; 9 regions greyed "coming soon". Per-metro region homepage.

### e3a / e3b — map overhaul (d19af25 / 33965fc)
e3a: full CTA bus+rail + Metra + Pace coverage in the sample, tiles, and spine;
normalized `mode` (bus/rail/commuter-rail) on silver+gold routes/stops. e3b:
agency/mode filters + route/stop search (APG combobox) + map UX polish.

### e4a — live feed endpoint (0170aef)
Server-side Astro endpoint `GET /api/live/<metro>` (`prerender = false` → Vercel
serverless), CTA keys read from server env and never in the client bundle. Returns
a `LiveFeed` (vehicles + arrivals + errors), always 200, degrades into `errors[]`
(never throws). Normalizer lives only in TS; the E11 python sampler is a dumb curl
appending NDJSON. Needs `CTA_BUS_TRACKER_API` + `CTA_TRAIN_TRACKER_API` in env.

### e4b — live layer + arrivals (3eb8175)
Live CTA vehicle layer on the map (GeoJSON symbol layer, rAF tween, reduce-motion
aware) + next-arrivals panel. Polls the e4a endpoint only; types imported as
`import type` so no server code/URLs reach the bundle. **Known limit:** rail
platform stops (30xxx) return no arrivals (e4a `stations` is map-id only).

### e5 — job-access page (4a9aea3)
Real job-access scores: exports `gold_hex_access` → H3 choropleth + methodology
link. ORS isochrones only if a key is provided, else labeled straight-line.

### e6 — ridership (f934527)
CTA ridership by line + by stop from Socrata (`bynn-gwxy`, `t2rn-p8d7`).

### e7 — service-coordination (556a6f7)
PostGIS cross-agency spatial join: `gold_stop_pairs` pairs stops from different
agencies within a walkable radius (`ST_Distance_Sphere`, `pair_radius_m=400`),
scored `0.5·closeness + 0.5·headway-mismatch` (equal weight, transparent). Headways
are a seeded representative published figure per agency (CTA 10 / Pace 30 / Metra
60), not real-time. Served as static JSON (no new Supabase table, no RLS migration).

### e8 — finance depth (51e9cf3)
More granular finance (capital vs opex, per-mode, per-capita, farebox trend) plus
new analyses (NTD ratios: `funding-ntd-ratios`).

### e9 — demographic change (76d9d92)
ACS change over ≥2 vintages (Summary File B01003 population, B19013 income).

### e10 — TOD (9ffaac5)
`gold_hex_tod` — density + growth + time-to-CBD (`min_to_cbd` = km ÷ 24 km/h × 60).
Multi-CBD-capable schema (`cbds` + `hex_tod` tables, both RLS public-read). Sources:
LODES prior + 2010 CenPop + authored CBD anchors.

### e11 — utilization + delays (db25075)
Delays page from live-feed samples: delayed share by mode (CTA's own `delayed` flag,
*not* schedule deviation — the free feed carries no scheduled time), next-arrival
wait histogram, and a bunching crowding proxy (two same-route vehicles ≤2 min at a
stop). Served JSON (not dbt: the NDJSON sample log is gitignored, never exists at
`dbt build`). Honest "coming" state until samples accumulate.

### e12 — articles (1225a3f)
Astro MDX content collection; general index + region-filtered index, linked from
the national + region homepages.

### e13 — about + methodology (3f6e26b)
`/about` + `/methodology` (structured for per-region variants).

### e14 — deep QA sweep (no commit)
Backend + UI + UX QA across the phase. CLEAN — 0 bugs, empty tree, no commit.
Gates at sweep: selftest 52, dbt 146, Lighthouse ≥96.
