# v3 Design Direction — "Field Instrument"

The firm spine E1 implements. Supersedes the v1 "Transit Instrument Panel"
guideline as the active direction; TOKENS.md/DESIGN_GUIDELINE.md are refined to
match, not replaced wholesale. Every page and island in v3 inherits this. The
E1 agent executes detail (exact ramps, component internals); it does **not**
re-decide the spine below.

## Premise

MetroTrack is an instrument, not a brochure. The reference sites
(project-aperture, ten.375.studio, sentient.foundation, xnrgyclub, abvtek,
brand.ivress.co.jp) share one move: **precise typographic editorial layout,
generous negative space, one charged accent against a near-neutral field,
restrained purposeful motion, monospace as a data/label voice.** We adopt that
register and bend it toward civic-data legibility. Not: gradient-heavy SaaS,
card-soup dashboards, decorative illustration, AI-slop hero blobs.

## 1. Type

- **Two families.** A grotesque/geometric sans for prose + headings (system
  stack fallback `system-ui` to start; a self-hosted display face is optional
  polish, not required this phase). Existing mono (`--font-mono`) stays as the
  **data/label/figure voice** — every number, axis, code, agency tag is mono
  tabular.
- **Modular scale, ratio ~1.25** anchored at 16px body. Steps (rem):
  `0.75 / 0.875 / 1 / 1.125 / 1.5 / 2 / 2.75 / 3.75`. Expose as
  `--text-{xs,sm,base,md,lg,xl,2xl,3xl}`. Display steps clamp fluidly
  (`clamp()`) for 320→1920.
- **Measure** 60–72ch on prose (articles, methodology). Tight leading on
  display (1.05–1.1), open on body (1.5).
- Numbers are **always** `.tabular` (tabular-nums, mono) so columns align.

## 2. Color

- Keep **OKLCH** everywhere (already in globals.css) — themes stay perceptually
  matched. Dark is default; light is a peer, not an afterthought.
- **One charged accent** (evolve current cyan; may retune hue but keep a single
  charged accent rationed to value/action/trend — never decoration). Add a
  **positive/negative pair** for deltas (up/down funding, growth) and a
  **warning** for stale/blocked-data states.
- **Agency colors are a DATA ENCODING** (DESIGN_GUIDELINE rule holds). Fill the
  four TODO tokens from each agency's brand guide (do NOT guess hex; source in a
  comment): `--agency-cta`, `--agency-metra`, `--agency-pace`, `--agency-nita`.
  CTA rail lines keep their official line colors on the map.
- **Colorblind-safe requirement (a11y toggle):** color is never the *sole*
  signal. Every agency/mode/series also carries a shape, pattern, label, or
  dash. The colorblind toggle swaps to an Okabe-Ito-derived ramp; the base ramp
  must already pass with the non-color redundancy.

## 3. Space & layout

- **8px base grid.** Spacing scale `--space-{0..}` = 0,4,8,12,16,24,32,48,64,96.
- **Content column** max ~72rem; full-bleed reserved for the map. Generous
  section rhythm (vertical space between bands ≥ `--space-2xl`).
- **Layout primitives** (build these, compose everything from them):
  `Stack` (vertical rhythm), `Cluster` (wrap row w/ gap), `Grid` (auto-fit
  minmax cards), `Bleed`/`Frame` (map + media), `Sidebar` (map + control rail).
  Astro components; no CSS framework beyond Tailwind v4 utilities + tokens.
- **Mobile-first**, verified 320→1920. Map control rail collapses to a sheet on
  small screens.

## 4. Motion

- **Restrained + purposeful.** Transitions 120–200ms, ease-out; entrance
  reveals ≤300ms, one property (opacity/transform) not both-plus.
- Motion communicates state (layer toggling, value change, route highlight),
  never ambient decoration.
- **`prefers-reduced-motion` AND the reduce-motion toggle** both kill non-
  essential motion (globals.css already has the media query; the toggle sets
  `data-motion="reduce"` to force it independent of OS).

## 5. Component kit (inventory E1 must ship)

Documented + reusable, tokens only (never hardcoded hex):

- **Shell:** `Base` layout (evolve existing), global **Nav** (per-metro),
  global **Footer** (links + button back to `an9.dev`), **Toolbar** hosting the
  toggles.
- **Toggle island** (React, one island): theme (dark/light), colorblind,
  reduce-motion, text-size (S/M/L → sets `--text-scale`). All persist to
  `localStorage`, applied as `data-*` on `<html>`, **set pre-paint via an inline
  head script** to avoid FOUC.
- **Data primitives:** `Stat` (big tabular figure + label + optional delta),
  `StatBand` (row of stats), `SourceTag` (links the figure to its
  DATA_SOURCES.md row — reused everywhere a published number appears),
  `DataState` (empty / loading / error / "data coming" — the honest-scaffold
  state every data-hard epic reuses), `Legend`, `Callout`.
- **Chart shell:** shared ECharts/Recharts theme wrapper reading tokens (light/
  dark/colorblind aware) so E6/E8/E9/E11 charts are consistent by default.
- **Map shell:** MapLibre wrapper (evolve `TransitMap.tsx`) with a standard
  **legend + layer control + popup** slot that E3/E4/E5 reuse.
- **Card:** metro directory card (live / coming-soon variants for E2).

## 6. A11y baseline (non-negotiable, already partially live)

Keep + extend: no-JS table fallbacks for every chart/map, ARIA on interactive
islands, visible `:focus-visible`, target ≥44px, Lighthouse A11y ≥90 mobile,
the three toggles above. Color-contrast AA in **both** themes and the
colorblind palette.

## 7. What E1 delivers (accept)

Token set (type/color/space/motion) in globals.css + TOKENS.md; the component
kit above, documented in DESIGN_GUIDELINE (or a v3 kit doc) with a usage line
each; toggle island persisting across nav with no FOUC; **`hiring.astro`
rebuilt on the kit as the reference page** proving it end-to-end; footer global;
Lighthouse Perf/A11y/Best-Practices ≥90 mobile. Every downstream epic builds
its page from this kit — that is the standing rule, not a per-epic re-decision.
