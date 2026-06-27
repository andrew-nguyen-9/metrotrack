# Design Guideline — "Transit Instrument Panel"

The contract every UI segment is reviewed against. Derived from the design
questionnaire (section C). Tokens live in [`TOKENS.md`](TOKENS.md); a11y + perf bars
live in [`../DEFINITION_OF_DONE.md`](../DEFINITION_OF_DONE.md).

## The concept

**A transit control room's instrument panel.** Dark-native, data-as-instruments:
a disciplined near-black base, one charged accent, agency identity carried by
official line/brand colors, and numbers rendered like precision readouts — dials,
ridgelines, tickers, maps — not decorative cards. Fast and legible first; the two
or three cinematic moments are additive, never a tax on comprehension.

## Principles

1. **Instrument, don't decorate** (C9 Tufte-strict). Max data-ink, min chrome. No
   ornament that doesn't carry data. Numbers are the product.
2. **One base, one accent, agency colors for identity** (C3+C4). A single rationed
   accent marks value/action/trend. *Agency* color (CTA / Pace / Metra / NITA
   official brand) is a **data encoding**, used only to attribute data to an
   authority — never decoratively.
3. **Honest by construction.** Every figure shows its `as of` date; modeled values
   read as estimates with ranges (G9); shortfall carries its "≠ staffing alone"
   caveat (J4). The design never implies more certainty than the data has.
4. **Accessible + colorblind-safe** (M1–M3). WCAG 2.2 AA (AAA body text). Color is
   never the only signal — agency encoding always pairs with a label/shape/pattern.
   Every map view has an equivalent data table (M2).

## Visual system (values in `TOKENS.md`)

| Group | Direction |
|---|---|
| **Theme** | Dark default + light toggle (C2). Define both in OKLCH so they stay perceptually matched. |
| **Base** | Near-black layered charcoals + subtle grain (dark); warm-neutral paper (light). |
| **Accent** | One charged hue, rationed to value/action/trend. |
| **Agency colors** | Official CTA / Pace / Metra / NITA brand colors as the authority encoding. Source exact values from each agency's brand guide; store in OKLCH. *(TODO: fill in `TOKENS.md` during v1.1 — do not guess hex.)* |
| **Surfaces** | Frosted-glass panels, hairline borders, soft inner glow (dark) / soft shadow (light) (C7). No hard 1px box seams. |
| **Type** | Display: **condensed grotesk** with transit-signage character (C5). Body: neutral grotesk. **Mono/tabular numerals everywhere** (C6) — stats always align. |
| **Imagery** | None for v1 — data + maps only (C10). Door left open for tasteful station/city photography accents later. |
| **Motion** | Restrained + 2–3 signature moments (C8). All reduced-motion-aware with static fallbacks (M5). |

## Signature moments (the 2–3 "wow" budget)

1. **Access reveal** — clicking a point on the map blooms an isochrone + the reachable-
   jobs count counts up (the job-access signature feature, `../modeling/ACCESS_SCORE.md`).
2. **Funding flow** — the Sankey animates revenue → authority → category on first view.
3. **"My area" panel** — searching a stop/route slides in an instrument readout that
   re-ranks with a layout animation.

All three must hold a static, legible state under `prefers-reduced-motion`.

## Responsive

Mobile-first, desktop-excellent (A6). Fluid type via `clamp()`, fluid spacing scale,
grids via `minmax()`/`auto-fit`. Tabular numerals + min-column widths so no numeric
cell ever clips. Tables collapse to stacked stat-rows under 640px — never horizontal
scroll. Test 360/768/1280/1920 every segment. Touch targets ≥ 44px.

## What we explicitly avoid

Generic SaaS dashboard cards; rainbow accenting; decorative use of agency colors;
motion that blocks reading; hover-only information on touch; fixed-pixel layouts;
photography that competes with data; anything over the perf budget.

## Process

Build with the `frontend-design` skill in mind; verify every screen with
chrome-devtools (`resize_page` + `lighthouse_audit`) + an axe pass + the per-segment
QA checklist before a segment is done.
