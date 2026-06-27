# Workflow

How work moves through this repo: plan, isolate work on branches, build in small
reviewable units, gate every unit on tests + QA + review, close out cleanly.

Pair with [`VERSIONING.md`](VERSIONING.md) (naming) and
[`DEFINITION_OF_DONE.md`](DEFINITION_OF_DONE.md) (the quality bar).

## The three units

```
Phase  v{p}          a release-sized chunk          branch: v{p}        off main
 └─ Segment v{p}.{s}  one buildable feature area     branch: v{p}.{s}    off v{p}
     └─ Task v{p}.{s}.{t}  one focused change         commit(s) on the segment branch
```

A **task** is one change you could describe in a sentence and review in one
sitting. If it can't be, split it.

## Phase lifecycle

### 1. Open the phase
- Branch off `main`: `git checkout -b v{p}`.
- Write `docs/phases/v{p}/PHASES_OVERVIEW.md` + per-segment plans. **No code before
  the plan exists.**

### 2. Work the segments (repeat per segment)
1. **Branch** off the phase branch: `git checkout v{p} && git checkout -b v{p}.{s}`.
2. **Complete tasks** `v{p}.{s}.1 …`, committing per task with a `[v{p}.{s}.{t}]` trailer.
3. **Build it out** — real implementation, not stubs.
4. **Test** — `type-check`, `lint`, `build`; `pipeline/selftest.py` for ETL; dbt
   tests for transforms; behavior checks for the change.
5. **QA** — exercise like a user (real browser, mobile + desktop, light/dark,
   reduced-motion; map at 360/768/1280/1920).
6. **`/code-review`** — run it; address findings.
7. **Commit** the cleanup; **merge** the segment into `v{p}`; delete the segment branch.

A segment that isn't tested, QA'd, and reviewed does **not** enter the phase branch.

### 3. Close the phase (in order)
- **(a)** Full QA pass on the phase branch.
- **(b)** `/code-review` of the whole phase diff vs `main`.
- **(c)** Commit final fixes.
- **(d)** Merge `v{p}` → `main`, tag `v{p}.0.0`, cut a release.
- **(e)** Delete phase + straggler branches; prune remotes.
- **(f)** Review all docs (README, CLAUDE.md, design, this file) — fix what the phase made stale.
- **(g)** Archive phase notes into `docs/phases/v{p}/ARCHIVE.md` (what shipped, decisions, deviations).
- **(h)** Write the next brainstorm: `docs/brainstorming/v{p+1}-ideas.md`.

## Rules that don't bend

- `main` is always shippable; never commit to it directly.
- Tests + QA + review gate every merge — at both the segment and phase boundary.
- Data-pipeline tasks add an idempotency check + a source row in `DATA_SOURCES.md`.
- Docs are part of "done." A phase isn't closed until (f)–(h) are done.
- No AI attribution in commits, PRs, or branch names.

## Commit messages

Conventional-commit style, scoped, with the work-ID trailer:

```
feat(map): bus-stop ½-mi job-access layer        [v1.1.3]
feat(pipeline): Census LODES bronze loader       [v1.0.2]
fix(transform): dedupe stops by content_hash     [v1.1.5]
docs: archive v1 phase notes                     [v1.0.0]
```
