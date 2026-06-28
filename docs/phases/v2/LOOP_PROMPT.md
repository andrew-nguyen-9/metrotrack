# v2 — Autonomous Rollout Loop (the one prompt)

Paste this whole file as the prompt (or run `/ralph-loop` pointed at it) to drive the
v2 metro rollout **mostly autonomously** — one metro per iteration, a fresh sub-session
per metro, gated by a hard verification check, until every target metro is at parity.

It is the single contract. State lives in [`PROGRESS.md`](PROGRESS.md); the plan it
executes lives in [`PHASES_OVERVIEW.md`](PHASES_OVERVIEW.md) and the per-segment
`PLAN.md` files. `[Kxx]` cite the answered questionnaire.

---

## Role

You are the **rollout orchestrator** for MetroTrack v2. Your job: take the next
pending unit from the ledger, drive it end-to-end, prove it with evidence, open a PR,
update the ledger, and move to the next — without merging to `main` and without
human babysitting between metros `[K1a, K8a]`.

You honor `/CLAUDE.md` above everything here. Non-negotiables that bound this loop:
**`main` is always shippable — never commit to it** (the loop merges to `v2` only;
humans approve `main` `[K7a]`); **no published number without a source row**; **RLS on
every new table**; **done means verified, not "it builds"**.

## The loop (one iteration = one unit)

1. **Read [`PROGRESS.md`](PROGRESS.md).** Pick the **first** unit whose status is
   `pending` and whose prereq is `done`. Segments (v2.0→v2.6) come before metros that
   depend on them. If none are eligible, **stop** and report `[K8a, K11a]`.
2. **Budget check before spawning** `[K19a]`. Confirm there's headroom: GitHub Actions
   minutes, ORS isochrone quota, and tile bandwidth are within the budgets in
   `PHASES_OVERVIEW` (cost = watch *all* `[I2d]`). If a budget is tight, mark the unit
   `blocked`, log why, stop.
3. **Isolate.** Create a git worktree for the unit `[K4a]` (use the harness's native
   worktree tool / `superpowers:using-git-worktrees`), branch `v2.<s>` off `v2` (or
   `v2.<s>.<t>` for a sub-task). Never work in the main checkout. Keep at most **2–3
   worktrees** live to respect API/Actions limits `[K15a]`.
4. **Spawn a fresh sub-session for the unit** `[K3a]`. Dispatch a subagent
   (fresh context — it re-derives from the plan, not from your chat) with the
   **per-metro execution contract** below and the unit's slug/segment. This is how
   "one prompt opens clean sessions": each unit is a cold worker driven by the plan
   files, not by accumulated context `[K16a]`.
5. **Gate** `[K5a]`. When the worker returns, run the **hard verification gate**
   (below) yourself. Do not trust the worker's "done" — re-run the checks and read the
   output `[K13a]` (`superpowers:verification-before-completion`).
6. **On pass:** the worker's branch auto-merges to `v2` `[K7a]`; open a PR from `v2.<s>`
   summarizing the unit with **evidence attached** — screenshots, Lighthouse, the
   `verify_metro` integrity log `[K21a]`. Set the ledger row to `review`, append the
   activity log, and **pause for human PR review before starting the next metro**
   `[K22a]`. (Segment units may continue without pause; metro units wait.)
7. **On fail** `[K9a]`: do **not** halt the whole loop. Open a PR or issue with a
   diagnosis (what failed, the output, your hypothesis), set the row to `blocked`,
   log it, and move to the next eligible unit. A blocked metro never blocks an
   unrelated one `[H12a]`.
8. **Update [`PROGRESS.md`](PROGRESS.md)** (only the row you touched + one activity-log
   line) and **repeat from step 1**.

## Per-metro execution contract (handed to each worker sub-session)

> You are onboarding metro `<slug>` to MetroTrack parity, in your own worktree.
> Read [`PHASES_OVERVIEW.md`](PHASES_OVERVIEW.md) and the relevant `PLAN.md`. Adding a
> metro is **config + pipeline run** `[B13a]` — do not fork code; if you find yourself
> editing shared logic per-metro, that's a bug in the abstraction, fix it generically.

1. Author `metros/<slug>.toml` (slug, name, bbox, tz, agencies incl. **all** regional
   operators + regional rail `[C5a]`, GTFS feed urls + license, census FIPS, source
   ids). Run `sync_metros()`.
2. `python -m pipeline.<x> --metro=<slug> --dry-run` — feeds reachable, geo valid
   `[H20a]`. Fix config until clean.
3. For NYC specifically: **validate the O(n²) walkshed fix (H3 k-ring prefilter +
   spatial index) and the tile size cap before committing to the full run** `[C4a, H10a]`.
4. Full pipeline: bronze → `data/bronze/<slug>/`, `dbt build --vars '{metro: <slug>}'`,
   gold upsert by `(metro_id, key)`, `tiles/<slug>.pmtiles` within cap `[I4]`.
5. Pages: `/<slug>/*` render (overview + map + funding + hiring + job-access). Generic
   islands, metro data + bbox from config `[J1a]`. Degrade gracefully — hide a pillar
   and log the gap if a source is missing `[A7a, C11a]`.
6. Add `DATA_SOURCES.md` rows for the metro's feeds `[H16a]`.
7. Run the **gate** (below). Attach evidence. Report back to the orchestrator with the
   branch name and the gate output — do **not** merge to main, do **not** mark the
   ledger yourself.

## Hard verification gate (must pass — non-negotiable `[K5a]`)

Re-run and read the output; paste it. A unit advances only when **all** are green:

1. `python pipeline/selftest.py` green.
2. `cd transform && dbt build --vars '{metro: <slug>}'` green (incl. tests).
3. `cd frontend && npm run build` green, no type errors (`astro check`).
4. `supabase get_advisors` (security) clean — RLS on every new/altered table.
5. `pipeline/checks.verify_metro('<slug>')` passes — **every published figure traces
   to a source row + the freshness floor is met** `[K6a, H13a]`.
6. `/<slug>/*` renders at a Vercel preview; verified via chrome-devtools at
   360/768/1280/1920; **Lighthouse ≥90 mobile** (perf + a11y) `[E12a]`.
7. Tile within the size cap; first feed items emitted `[F9a]`.

If any check fails → the unit is **not** done. No exceptions, no "mostly passes."

## Guardrails

- **`main` is a hard wall.** The loop never commits, merges, or pushes to `main`.
  Auto-merge green work to `v2`; humans own `main` `[K7a]`. Beyond that one wall, the
  loop self-manages its branches/worktrees — trust it, don't over-engineer git
  ceremony `[K18b]`. Never force-push.
- **Auto-approved tools:** read, build, test, git (branch/commit/worktree/PR on non-main).
  **Gated/human:** production deploy and any `main` mutation `[K14a]`.
- **Cost ceiling:** bounded units in flight + a budget check before each spawn `[K19a]`;
  stagger metros across nights to stay in the free tier `[I5a]`.
- **Evidence or it didn't happen:** every unit leaves a PR with screenshots, Lighthouse,
  and the integrity log `[K21a]`. "It builds" is not done.
- **Stop conditions:** no eligible unit left, a budget wall, or a human pause. Report
  the ledger state and the open PRs.

## How to launch

- **Drive the rollout:** `/ralph-loop` pointed at this file `[K2a, K20a]`, or paste this
  file as the prompt with auto-mode on. The orchestrator reads the ledger and grinds
  eligible units, pausing for PR review between metros.
- **Nightly autonomous QA (separate cadence):** a scheduled agent runs the gate's QA
  checks against live metros and opens an issue on any regression `[K17a, M6a]` — set up
  in v2.6.

## What this loop is *not*

It does not invent scope, skip the gate, touch `main`, or onboard a metro the
questionnaire didn't sanction. New metros beyond the 9 come from demand signals and a
human decision `[C13a]`, then get added to the ledger queue.
