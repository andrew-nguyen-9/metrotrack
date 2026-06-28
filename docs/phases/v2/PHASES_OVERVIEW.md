# v2 Phases — Overview

Dependency-ordered. Each phase opens a branch off `v2`, runs its segments
(sub-branches), and finishes with the WORKFLOW ritual
([`../../WORKFLOW.md`](../../WORKFLOW.md)). Versioning: `v[phase].[segment].[task]`
([`../../VERSIONING.md`](../../VERSIONING.md)).

Decisions below are the survivors of
[`../../brainstorming/v2-QUESTIONNAIRE.md`](../../brainstorming/v2-QUESTIONNAIRE.md)
(200 MCQs, all answered). Each locked decision cites its question id, e.g. `[B1a]`.

> **v2 theme — go multi-city.** Chicago becomes one metro under a MetroTrack
> homepage; the architecture turns "adding a metro" into *one config file + one
> pipeline run* `[B13a]`. v2 ships **3 metros live** (Chicago + SF + NYC) `[A2a]`
> plus national infra (homepage/SEO/RSS) and an **autonomous build loop** that
> grinds the remaining metros. Unbuilt metros show greyed "coming soon" `[C12a]`.

## Scope at a glance

| In v2 | Out of v2 (deferred) |
|---|---|
| Multi-tenant DB + pipeline + routing `[B1a,H1a,B5a]` | Auth / accounts `[A8e]` |
| Homepage city directory + national band `[D1d]` | Real-time vehicle map `[A8e]` |
| SEO (sitemap, JSON-LD, OG, CWV) `[E1a]` | Non-US metros `[A8e,C14a]` (note for v3) |
| Per-region RSS feeds `[F1a]` | Paid tiers `[A8e]` |
| SF + NYC onboarded to parity `[A2a]` | Embeddable widgets `[G10a]` (v3) |
| Chicago-first modeling carry-overs `[L*]` | Email digest `[F14a]` (v3) |
| Autonomous loop + remaining-metro rollout `[K*]` | The other 6 metros to *full* parity (loop grinds as capacity allows) |

**Parity bar = a metro is "done"** when all four pillars render — map, funding,
hiring, job-access `[A4a]` — degrading gracefully (hide a pillar, log the gap) when
a source is missing `[A7a, C11a]`.

## Phases (segments of v2)

| Phase | Branch | Name | Unblocks |
|-------|--------|------|----------|
| v2.0 | `v2.0` | **Multi-tenant foundation** — `metros` config+table, `metro_id` everywhere, `--metro` pipeline, `[metro]` routing, migrate Chicago → `/chicago` (golden reference `[A6a]`) | everything |
| v2.1 | `v2.1` | **Site shell, pages & SEO** — homepage directory + national band, top-nav metro switcher, theme toggle, Compare/Methodology/About/Glossary/Downloads pages, sitemap + JSON-LD + OG + analytics | metros become discoverable |
| v2.2 | `v2.2` | **RSS / regional feeds** — `feed_items` table, nightly gold-diff delta detector, per-metro + global feeds, `/feeds` index | distribution |
| v2.3 | `v2.3` | **Metro onboarding: SF** — first repeat of the add-a-metro path; multi-agency incl. regional rail `[C2,C5a]`; sets the per-metro parity checklist | the loop's template |
| v2.4 | `v2.4` | **Metro onboarding: NYC** — validate O(n²) walkshed fix + tile budget *first* `[C4a,H10a,I4]`; the hard metro | scale proof |
| v2.5 | `v2.5` | **Modeling depth (Chicago-first)** — service-shortfall via GTFS-RT `[L1a,L2a]`, transit-leg ACCESS_SCORE spike `[L3a]`, ACS equity overlay `[L4a]`, per-capita normalization `[L5a]`, capital-project pilot `[L6a]`, wire funding/hiring/access into nightly `[L11a]` | the signature stories |
| v2.6 | `v2.6` | **Autonomous loop + rollout** — harden `LOOP_PROMPT.md`, worktree orchestration, gates; grind DC/Boston/LA/Philly/Seattle/Atlanta `[C1a]` as capacity allows | national coverage |

## Why this order

- **Foundation (v2.0) first** — nothing multi-city works until `metro_id` exists on
  every table, the pipeline takes `--metro`, and routing is `[metro]`-aware.
  Migrating Chicago to `/chicago` and keeping it green is the **golden test**
  `[A6a]` that proves the abstraction without losing v1.
- **Shell + SEO (v2.1) before adding metros** — the homepage, nav, and SEO scaffold
  give every subsequent metro a place to appear and be indexed `[E1a]`.
- **RSS (v2.2) before the metro grind** — so each onboarded metro emits feed items
  from its first nightly `[F9a,F12a]`.
- **SF (v2.3) before NYC (v2.4)** — SF is mid-size with clean multi-agency GTFS;
  it de-risks the add-a-metro path before NYC's MTA-scale stress test `[C2,C4a]`.
- **Modeling (v2.5) after coverage** — service-shortfall + transit-leg access are
  Chicago-first deepenings; they don't block metros, so they ride after the machine
  works. Heuristic-first, ML only if it measurably beats it `[L8a]`.
- **Loop (v2.6) last to *scale*, but its prompt is authored in v2.0** — the loop is
  how the remaining 6 metros ship; it only runs once v2.3 proved the template.

## Locked architecture decisions

| Concern | Decision | Q |
|---|---|---|
| **Tenancy** | Single DB, `metro_id` column on every table; composite `(metro_id, natural_key)` keys | `B1a, B18a` |
| **Metro source of truth** | **Both**: `metros/<slug>.toml` is authored truth; a `metros` table mirrors it (slug, name, bbox, agencies, tz) | `B2c, B6a, B9a` |
| **RLS** | Keep public-read on all tables, no per-metro restriction | `B3a` |
| **URLs** | Path-based: `/chicago`, `/sf`, `/nyc`; stable kebab slugs `/chicago/job-access` | `B4a, E16a` |
| **Routing** | Astro dynamic `[metro]/...` from `getStaticPaths`; static SSG, islands for maps | `B5a, D10a` |
| **Pipeline** | Every script takes `--metro=<slug>`, reads config; `--dry-run` smoke test validates feeds+geo first | `H1a, H20a` |
| **Bronze layout** | `data/bronze/<metro>/<source>/...`; commit small/canonical, gitignore large re-fetchable GTFS | `H2a, H3a, I7a` |
| **dbt** | Add `metro_id`, parametrize via dbt vars; normalize GTFS variance to canonical silver, tolerate missing | `H5a, H6a` |
| **Gold reload** | Upsert by `(metro_id, key)`, no truncate; `as_of` + `source_hash` provenance columns | `H14a, H15a` |
| **Migration** | Add nullable `metro_id`, backfill `'chicago'`, set NOT NULL; numbered SQL migrations, RLS on every new table | `B17a, H19a` |
| **Tiles** | One PMTiles per metro `tiles/<slug>.pmtiles`, served static off Vercel; size cap + per-zoom limits | `B11a, I3a, I4` |
| **Walkshed scale** | H3 k-ring prefilter + spatial index **before** NYC | `H10a` |
| **Isochrone cost** | Precompute, cache; refresh **monthly** not nightly (some access recompute nightly) | `C9c/a, I6a` |
| **Time zones** | Store UTC, render in metro tz from config | `B15a` |
| **Naming** | "Metro" everywhere (a metro = its whole region, e.g. Bay Area) | `B16a, F10a` |
| **Cost** | Watch **all** constraints (Actions minutes, ORS quota, tile bandwidth), set budgets; stagger metros across nights to stay free | `I2d, I5a, I8a` |
| **Second Supabase project** | "MetroTrack B" = staging/branch DB | `I11a` |

## Locked product/SEO/feed decisions

| Concern | Decision | Q |
|---|---|---|
| **Homepage** | City **directory + national stat band**; US map (pins) + card grid; live = full card, soon = greyed; geolocate soft-suggests nearest | `D1d, D2a, D3a, D6a` |
| **Card** | Name, agencies, headline **job-access score**, status, "data as of" | `D4a, D15a, L14a` |
| **Homepage logo** | Reuse MetroTrack marks **+ a generic, non-city MetroTrack logo** for the homepage | `D12a +note` |
| **First-visit framing** | One-line subhead **plus** a full explainer block | `D14a+b` |
| **Theme** | Dark-native default **+ ship the v1-deferred toggle** | `D13a` |
| **Pages** | Home, Compare, Methodology (per-pillar, sourced), About, Glossary, Downloads (CSV/parquet), Feeds | `G1a, G5a, G8a, G9a` |
| **Nav** | Global top nav (persistent metro switcher + pages) + footer | `G11a, G12a` |
| **SEO** | High priority, built-in: templated titles/descriptions with live figures, auto `sitemap.xml`, JSON-LD (Dataset + Organization + BreadcrumbList), per-metro OG images pre-rendered at build, self-canonical, breadcrumbs, privacy analytics, Lighthouse ≥90 mobile in CI | `E1a–E22a` |
| **Coming-soon** | Real 200 indexable "coming soon" page per unbuilt metro | `E21a` |
| **RSS** | **Both** global + per-metro feeds; URL `/rss/<metro>` (+ global `/rss/index.xml`); RSS 2.0; delta-triggered from a `feed_items` table (RLS public-read); neutral factual titles; generated at end of nightly after gold reload; backfill "now tracking <metro>" | `F2c, F3b, F4a, F5a, F7a, F8a, F9a, F12a, F15a` |

## Cross-cutting (acceptance criteria in every segment)

Data-integrity (every figure → a `DATA_SOURCES.md` row `[K6a]`) · idempotent
pipeline · RLS on new tables · freshness-floor checks per metro per source
`[H13a]` · design guideline + accessibility + reduced-motion + performance budgets
· Lighthouse ≥90 mobile in CI `[E12a]`. See
[`../../DEFINITION_OF_DONE.md`](../../DEFINITION_OF_DONE.md). Not separate segments.

## The autonomous loop

The remaining-metro rollout runs as a **mostly-autonomous loop** — one prompt,
fresh sub-session per metro. The contract lives in:

- [`LOOP_PROMPT.md`](LOOP_PROMPT.md) — the single prompt that drives one metro
  end-to-end `[K1a, K12a]`.
- [`PROGRESS.md`](PROGRESS.md) — the ledger a fresh session reads to pick the next
  pending metro `[K10a, K11a]`.

**Hard verification gate (non-negotiable `[K5a]`):** a metro only advances when
build + Lighthouse + data-integrity (every figure traces to a source row, freshness
floor met) all pass `[K5a, K6a]`. The loop **never merges to `main`** — it
auto-merges green work to `v2`, humans approve `main` `[K7a]`, and review a
per-metro PR before the next metro starts `[K22a]`.

## Tags

Finishing v2 merges `v2` → `main` and tags `v2.0.0`. Patches bump the third digit.
