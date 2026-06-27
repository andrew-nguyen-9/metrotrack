# Definition of Done + QA & Review Checklists

A task/segment/phase is **done** only when it passes the relevant checklist. "It
builds" is not done.

## Per-task DoD

- [ ] Implements exactly its acceptance criterion; no scope creep.
- [ ] `build` + `type-check` pass; no new errors/warnings.
- [ ] New logic has a test (unit for pure fns, integration for data paths).
- [ ] Pipeline scripts touched are **idempotent** and re-runnable; `selftest.py` passes.
- [ ] dbt models touched have schema tests; `dbt build` green.
- [ ] No secrets in the client bundle; RLS on any new table; service-role key server-only.
- [ ] Any published figure has a row in `architecture/DATA_SOURCES.md` (source, license, cadence).
- [ ] Commit follows `<type>(scope): <summary>  [v{p}.{s}.{t}]`, no AI attribution.

## Per-segment QA (every UI segment)

- [ ] **Responsive** 320 → 1920px; map + charts legible; no overflow/clipped numbers.
      Test 360/768/1280/1920.
- [ ] **Reduced motion**: every animation has a static fallback.
- [ ] **Accessibility**: keyboard-navigable, visible focus, semantic landmarks,
      contrast ≥ WCAG AA, color never the only signal (map layers need a non-color encoding).
- [ ] **Themes**: correct in light + dark.
- [ ] **Empty / loading / error states**: render gracefully with no backend / no data.
- [ ] **Map performance**: vector tiles load fast; large point layers use deck.gl,
      not DOM; no main-thread jank panning/zooming.

## Per-phase verification (the 8-step finish, abbreviated)

QA (full phase) → `/code-review` (full diff) → commit → merge to `main` + tag →
delete branches → review all docs → archive phase docs → write next brainstorm.
Full detail in [`WORKFLOW.md`](WORKFLOW.md).

## Data-integrity checks (every pipeline/transform segment)

- [ ] Bronze is content-hashed and append-safe; re-running doesn't duplicate.
- [ ] A row count / freshness floor fails the nightly loudly if a source goes dark.
- [ ] Geometries are validated (`ST_IsValid`) and in a known SRID before load.
- [ ] No figure is published that can't be traced to a `DATA_SOURCES.md` entry.

## Performance budgets

| Metric | Budget |
|--------|--------|
| LCP (mobile, 4G) | ≤ 2.5s |
| CLS | ≤ 0.05 |
| Map first interaction | ≤ 200ms after tiles load |
| JS shipped to a page | ≤ 200KB gzip (map page may exceed; document it) |
| Lighthouse (Perf/A11y/Best-Practices) | ≥ 90 each |
