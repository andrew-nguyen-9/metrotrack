# ADR-002: Astro for the frontend

**Status:** Accepted
**Date:** 2026-06-27
**Deciders:** Andrew Nguyen

---

## Context

The frontend is mostly **static, data-dense content pages** (funding dashboard,
hiring, methodology, per-authority profiles) with a few **heavy interactive
surfaces** (the MapLibre + deck.gl map, ECharts charts). Questionnaire L2 picked
"static + ISR for data pages, client map." L1: Andrew explicitly wants to expand
beyond Next.js (many recent Next projects) and deferred the choice.

## Decision

Use **Astro** with the Vercel adapter. Pages render static HTML by default;
interactive pieces (map, charts, search, theme toggle, "my area" panel) are
**React islands** (`client:*` hydration). Tailwind + tokens for styling (L3),
Radix headless primitives inside islands (L4), Supabase JS client for data (L5),
MapLibre GL JS + deck.gl for the map (L6).

## Consequences

**Positive:**
- Ships near-zero JS on static pages → easiest path to the perf budget (LCP ≤ 2.5s,
  Lighthouse ≥ 90) on a data-heavy site.
- Islands isolate the expensive map/chart JS to the routes that need it.
- Genuinely new skill vs. Next.js (the stated goal), while reusing React knowledge
  inside islands.
- First-class content collections fit the methodology / per-authority pages.

**Negative:**
- No Next-style ISR; on-demand/SSR needs the Vercel adapter + explicit server
  endpoints. Acceptable — most pages rebuild nightly with the data anyway.
- Smaller ecosystem than Next for some integrations; map/chart libs are framework-
  agnostic so this is low-risk.
- Server-rendered React patterns (RSC) don't apply; data fetching is in Astro
  frontmatter or island-side via Supabase.

**Mitigations:**
- Nightly pipeline triggers a redeploy/rebuild so "static" pages stay current.
- Dynamic bits (on-demand isochrone, search) are Astro server endpoints or
  island-side Supabase calls.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Next.js App Router (the ⭐) | Andrew's default already; doesn't expand skills. Heavier client runtime for a mostly-static site. |
| Remix / React Router 7 | Closer mentally to Next (SSR-React); less of a skill stretch and less optimal for static-dominant content. |

Revisit if a feature needs deep server-React/streaming that islands can't serve.
