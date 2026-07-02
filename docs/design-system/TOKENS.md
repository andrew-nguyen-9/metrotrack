# Design Tokens

The locked values behind the "Field Instrument" direction
([`v3-DESIGN_DIRECTION.md`](v3-DESIGN_DIRECTION.md)). Live in
[`frontend/src/styles/globals.css`](../../frontend/src/styles/globals.css) — that
file is the source of truth; this doc is the map. **Theme** colors are OKLCH so
light/dark stay perceptually matched. **Agency brand** colors are the one
exception: fixed brand values (constant across themes) stored as their exact
sourced hex so we never drift a brand. Never hardcode hex in components —
reference the token.

## Theme (OKLCH)

| Token | Role |
|---|---|
| `--bg` / `--surface` / `--surface-2` | page · panel · raised panel (popover, map control) |
| `--border-hairline` | 1px seams, dividers |
| `--text` / `--text-muted` | body · secondary |
| `--accent` / `--accent-ink` | one charged cyan (value/action/trend) · text on an accent fill |
| `--delta-pos` / `--delta-neg` | value up / down (funding, growth) — always paired with ▲/▼ |
| `--warning` | stale / blocked-data state |

Dark is default (`:root`); light is `:root[data-theme="light"]`.

## Categorical series ramp

`--cat-1 … --cat-6` — the ramp multi-series charts use (distinguishable +
paired with a marker symbol). `:root[data-colorblind="on"]` swaps it to an
Okabe-Ito palette; `--delta-pos/neg` also swap (bluish-green / vermilion) to
avoid the red/green confusion. Read from JS via `lib/chart.ts`.

## Agency colors (data encoding only)

Exact sourced hex; each pairs with a label/shape wherever it appears. All three
operators brand blue, so multi-agency charts use `--cat-*` (distinguishable) +
symbols — `--agency-*` is for single-agency attribution (badges, SourceTag).

| Token | Authority | Value | Source |
|---|---|---|---|
| `--agency-cta` | Chicago Transit Authority | `#1743A6` | transitchicago.com/developers/branding (PMS 2728C · RGB 23 67 168) |
| `--agency-metra` | Metra | `#0A3D6A` | metrarail.com official site brand navy |
| `--agency-pace` | Pace Suburban Bus | `#011489` | pacebus.com official theme stylesheet brand blue |
| `--agency-nita` | NITA | `#2F7D8A` **(provisional)** | Proposed 2025 NE-Illinois transit-reform agency; **no brand guide exists yet** — provisional slate-teal, replace when one is published. |

CTA rail-line colors keep their official GTFS-published line colors on the map
(read from tile data, not a token) — add a `--line-*` group if a route legend
needs them.

## Type

Modular scale ~1.25 at 16px. `--text-{xs,sm,base,md,lg,xl,2xl,3xl}` =
`0.75 / 0.875 / 1 / 1.125 / 1.5 / 2 / 2.75 / 3.75` rem; the display steps
(`xl/2xl/3xl`) `clamp()` fluidly for 320→1920. `--leading-{tight,snug,normal}`
= `1.08 / 1.25 / 1.5`; `--measure` = 68ch (prose). Numbers are always `.tabular`
(mono, tabular-nums). `--font-mono` is the data/label/figure voice.

**Text-size a11y toggle:** `--text-scale` (0.9 / 1 / 1.15 for S/M/L) multiplies
the root font-size, scaling every rem-based size.

## Space (8px grid)

`--space-{0,3xs,2xs,xs,sm,md,lg,xl,2xl,3xl}` = `0,4,8,12,16,24,32,48,64,96`px.
Layout primitives take these as t-shirt `gap` props. `--measure-content` = 72rem
(page content column max).

## Motion

`--ease` / `--ease-out`; `--dur-fast|dur|dur-slow` = 120/160/200ms; `--dur-reveal`
= 300ms. Both `prefers-reduced-motion` **and** the reduce-motion toggle
(`data-motion="reduce"`) collapse non-essential motion.
