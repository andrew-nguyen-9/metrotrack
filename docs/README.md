# Documentation

The navigation hub. Written for two readers: **Andrew** (planning, decisions) and
**a fresh Claude session** (orient fast, then execute). New session: read
[`/CLAUDE.md`](../CLAUDE.md) first, then the doc that matches your task.

## Process docs (how we work)

| Doc | Read it when |
|-----|--------------|
| [`WORKFLOW.md`](WORKFLOW.md) | Before starting any phase or segment. Branch + QA + review + merge ritual. |
| [`VERSIONING.md`](VERSIONING.md) | Naming a branch, tag, or version. The `v[p].[s].[t]` scheme. |
| [`DEFINITION_OF_DONE.md`](DEFINITION_OF_DONE.md) | Before claiming any task/segment/phase done. |
| [`TOOLING.md`](TOOLING.md) | Which plugins/skills/MCP to use, output discipline, and the rules for autonomous loops. |

## What we're building

| Doc | What it holds |
|-----|---------------|
| [`overview/VISION.md`](overview/VISION.md) | The product premise, the 3 pillars, who it's for. |
| [`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md) | The medallion data flow, stack, serving path. |
| [`architecture/DATA_SOURCES.md`](architecture/DATA_SOURCES.md) | Every external source, its auth, license, refresh cadence. |
| [`modeling/ACCESS_SCORE.md`](modeling/ACCESS_SCORE.md) | The signature job-access metric (engine, cutoffs, surfacing). |
| [`modeling/UNDERSTAFFING_METRIC.md`](modeling/UNDERSTAFFING_METRIC.md) | The service-shortfall hiring metric + caveats. |
| [`design-system/DESIGN_GUIDELINE.md`](design-system/DESIGN_GUIDELINE.md) | The visual contract ("Transit Instrument Panel") every UI segment is reviewed against. |
| [`design-system/TOKENS.md`](design-system/TOKENS.md) | Token values (stub; filled v1.1). Brand/logo assets live in `/design`. |

## Decisions

[`decisions/`](decisions) — one ADR per file (Context / Decision / Consequences /
Alternatives):
- [`ADR-001`](decisions/ADR-001-supabase-postgis.md) — Supabase + PostGIS backbone.
- [`ADR-002`](decisions/ADR-002-astro-frontend.md) — Astro + React islands frontend.
- [`ADR-003`](decisions/ADR-003-routing-openrouteservice.md) — openrouteservice routing/isochrones.

## Phases (the plan)

Each phase has a folder under [`phases/`](phases): overview, per-segment plans,
and (at close) an archive. Current: [`phases/v1/PHASES_OVERVIEW.md`](phases/v1/PHASES_OVERVIEW.md).

## Brainstorming (what might come next)

- [`brainstorming/v1-ideas.md`](brainstorming/v1-ideas.md) — the seed backlog + candidate v2+ features.
- [`brainstorming/DESIGN_QUESTIONNAIRE.md`](brainstorming/DESIGN_QUESTIONNAIRE.md) — front-loaded MCQs to lock design/scope/modeling before build. Answers graduate into phases + design-system + ADRs.

## Conventions for this folder

- **One source of truth per concept.** Link, don't duplicate.
- **Docs have a lifecycle:** `brainstorming/` → `phases/v{p}/PLAN` → `archive/` at
  phase close.
- **Keep the index honest.** Add a doc, add a row here.
