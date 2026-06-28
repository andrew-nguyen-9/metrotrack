# v1 — Segment Initiation Prompts

Copy-paste prompts to start each v1 segment in a fresh session (or hand to
ralph-loop). Grab the preamble + the segment block. Every block names a branch,
scope, **END STATE**, a hard **STOP**, **TOOLING**, and a **GATE** — the real
commands that must pass. Per `../../TOOLING.md`, **a loop without its GATE is banned**;
the gate is commands, not the model's self-assessment.

## Shared preamble (prepend to every segment)

```
MetroTrack (Chicagoland transit tracker; repo formerly CTA). Source of truth: docs/
— read docs/README.md (router) first, then WORKFLOW, VERSIONING, TOOLING,
DEFINITION_OF_DONE, plus the architecture/decisions/design-system/modeling docs this
segment touches. Stack is LOCKED: Astro + React islands (ADR-002), Supabase + PostGIS
(ADR-001), openrouteservice (ADR-003), dbt + DuckDB, MapLibre + deck.gl, Apache
ECharts, PMTiles. caveman + ponytail on; rtk for git/file ops; NO AI attribution in
commits/PRs/branches. No code before the plan — the plan is
docs/phases/v1/PHASES_OVERVIEW.md. Locate code with serena (call initial_instructions
first); context7 for live library docs before writing API code. Run
superpowers:verification-before-completion before claiming done. STOP at the boundary.
```

## v1.0 — Foundation  ·  `v1.0` (off `main`)  ⚠ the spine; merge before any pillar work

```
Execute docs/phases/v1/PHASES_OVERVIEW.md §"v1.0 — Foundation", tasks v1.0.1–v1.0.5,
committing per task with a [v1.0.t] trailer. THIS IS THE FOUNDATION — the ONLY phase
allowed to create shared files (db/schema.sql, frontend app shell + globals/tokens,
shared lib types, CI workflows). Build them right; later segments must not edit them.

- v1.0.1 Scaffold: pipeline/ transform/ db/ data/ frontend/ (Astro + Tailwind +
  Vercel adapter) .github/workflows/; pipeline/selftest.py + a dbt skeleton. Extract
  design/logos/metrotrack-chicago-*.svg → frontend/public/; wire favicon + OG.
- v1.0.2 Dedicated Supabase project + PostGIS; db/schema.sql (authorities, stops,
  routes; SRID 4326; GiST indexes; RLS public-read) + a timestamped migration.
- v1.0.3 GTFS static loader (CTA/Pace/Metra) → bronze parquet (content-hashed) →
  silver stops/routes via dbt. Commit a small bronze sample so the build is reproducible.
- v1.0.4 tippecanoe → PMTiles build; one MapLibre map (React island) renders
  routes + stops at a Vercel preview URL, with an accessible data-table fallback.
- v1.0.5 Nightly workflow (extract → dbt build+test → load gold → rebuild tiles →
  trigger redeploy) + a Lighthouse CI budget gate on PRs.

FILES I OWN: all of v1.0 (this phase owns the shared spine).

GATE (loop stop condition — ALL must pass; re-check each iteration):
  1. `python pipeline/selftest.py` green
  2. `dbt build` green (silver stops/routes from the committed bronze sample)
  3. `astro build` (frontend production build) green, no type errors
  4. Supabase `get_advisors` → no RLS/security errors on the new tables
  5. MapLibre map renders CTA + Pace + Metra routes + stops at the preview URL;
     verified with chrome-devtools at 360/768/1280/1920; data-table fallback present

END STATE: branch v1.0 holds the working spine; the 5-point GATE is fully green;
per-task commits exist; phase NOT merged.

STOP at the gate. Do NOT start v1.1 pillar features (population/jobs overlays, POIs,
access score) — foundation only. Do NOT merge to main. Report the green gate and hand
back for the phase-close ritual (QA → /code-review → merge + tag v1.0.0).

TOOLING: context7 (Astro, MapLibre, deck.gl, dbt, DuckDB, PostGIS, GTFS); supabase
MCP (apply_migration, get_advisors); serena (code nav); chrome-devtools (resize +
lighthouse_audit); systematic-debugging if pipeline/dbt breaks (root-cause, don't
guess); frontend-design for the app shell + logo; vercel:deploy for the preview.

EXTERNAL (Andrew, not code — required before the gate can pass):
  - Create the dedicated Supabase project; enable PostGIS; set DATABASE_URL + keys.
  - Link a Vercel project (domain transit.an9.dev) for the preview.
  - No other API keys needed for v1.0 (GTFS static is keyless; Census/ORS/realtime
    keys come in v1.1+).
```

> Later segment prompts (v1.1 mapping, v1.2 funding, v1.3 hiring, v1.4 job-access)
> get written as each phase opens, following this same shape.
