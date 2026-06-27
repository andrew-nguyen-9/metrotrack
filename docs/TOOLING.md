# Tooling, Plugins & Loops

How agents work in this repo: which plugins/skills to reach for, output discipline,
and when (and when NOT) to run autonomous loops. Pair with
[`WORKFLOW.md`](WORKFLOW.md) (the ritual) and [`DEFINITION_OF_DONE.md`](DEFINITION_OF_DONE.md).

## Output + build discipline (always on)

| Mode | Role |
|---|---|
| **caveman** | Terse output: drop articles/filler/hedging. Code, commits, security write normal. |
| **ponytail** | Lazy = minimal. Climb the ladder: does it need to exist? stdlib? native? one line? Mark deliberate simplifications `// ponytail:`. |
| **rtk** | Token-killer proxy. Auto-rewrites git/file ops via hook — transparent, 0 overhead. Use `rtk gain` to see savings. |

## Code navigation + research

| Tool | Use for |
|---|---|
| **serena** (MCP) | Semantic code nav once code exists: `find_symbol`, `find_referencing_symbols`, `get_symbols_overview`. Beats grep for "what calls X". Call `initial_instructions` first. |
| **context7** (MCP) | Live docs before writing against a library — MapLibre, deck.gl, dbt, DuckDB, PostGIS, Census/Socrata APIs, Next.js. Don't trust memory for API syntax. |
| **Explore agent** | Broad fan-out search when you need a conclusion, not file dumps. |

## Data + deploy plugins

| Tool | Use for |
|---|---|
| **supabase** (MCP) | `list_tables` before schema changes; `apply_migration`; **`get_advisors` for RLS/security lints** (run after every new table); `generate_typescript_types`. |
| **vercel** (skills) | `/vercel:deploy`, `/vercel:env` for preview + prod; runtime logs/errors. |
| **chrome-devtools / playwright** (MCP) | Map QA: `resize_page` at 360/768/1280/1920, `lighthouse_audit`, console/network checks. Required per-segment QA. |

## Review + planning skills

| Skill | When |
|---|---|
| **`/code-review`** | Every segment + the full phase diff (gated by WORKFLOW). `--fix` to apply. |
| **superpowers:brainstorming** | Before any new feature/segment with open design questions. |
| **superpowers:systematic-debugging** | Any bug/test failure/pipeline break — root-cause before fixing. Never guess. |
| **superpowers:test-driven-development** | New pure logic (scoring, access score, metric math). |
| **superpowers:verification-before-completion** | Before claiming any task done. Evidence before assertions. |
| **compound-engineering:ce-plan / ce-debug** | Heavier planning + debugging passes when a phase warrants it. |

## Loops & autonomy

Loops are powerful and expensive. **A loop without a hard verification gate is
banned** — it burns tokens and ships garbage. Every loop names its stop condition.

| Mechanism | Use for | Stop gate (required) |
|---|---|---|
| **`/loop`** (interval or self-paced) | Polling external state the harness can't notify on — a deploy, a CI run, a slow nightly ETL. | A concrete condition ("deploy = READY", "dbt build green"), not "a while". |
| **ralph-loop** | Autonomous multi-step execution of a **bounded, verifiable** PRD — e.g. hardening the pipeline until `selftest.py` + `dbt build` are green, or batch-forging a metric across authorities. | A passing test/selftest/build that the loop checks each iteration. |

**Rules for any loop here:**
- Bounded scope + a "FILES I OWN" allowlist (see the segment-prompt pattern in
  `phases/`). No editing shared schema/types inside a loop.
- The gate is a real command (`pipeline/selftest.py`, `dbt build`, `npm run build`,
  a vitest suite) — not the model's self-assessment.
- Data loops respect source rate limits + idempotency (re-run ≠ duplicate).
- Pick `/loop` delays by cache window: <270s to actively poll, 1200s+ for idle
  fallback. Don't poll harness-tracked work — you're re-invoked when it finishes.

**Good loop fits for this repo:** nightly-pipeline fix-until-green; distractor/
quality-style batch passes with a selftest gate; waiting on a Vercel preview deploy.
**Bad fits:** anything touching `db/schema.sql` or shared types; open-ended "improve
the map" with no measurable gate.

## First-session checklist (fresh agent)

1. Read [`/CLAUDE.md`](../CLAUDE.md) → [`docs/README.md`](README.md).
2. `serena initial_instructions` if touching code.
3. Confirm the active phase/segment in [`phases/v1/PHASES_OVERVIEW.md`](phases/v1/PHASES_OVERVIEW.md).
4. Branch per [`VERSIONING.md`](VERSIONING.md). No code before the plan exists.
