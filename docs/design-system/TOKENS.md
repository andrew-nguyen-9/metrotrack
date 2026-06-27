# Design Tokens

The locked values behind [`DESIGN_GUIDELINE.md`](DESIGN_GUIDELINE.md). **Stub** —
filled during v1.1 (Mapping/Design segment). Define everything in **OKLCH** so
light/dark stay perceptually matched. Do not hardcode hex in components; reference
tokens.

## Theme

| Token | Dark | Light |
|---|---|---|
| `--bg` | TODO near-black | TODO warm paper |
| `--surface` | TODO frosted charcoal | TODO |
| `--border-hairline` | TODO | TODO |
| `--text` / `--text-muted` | TODO | TODO |
| `--accent` | TODO one charged hue | TODO (matched) |

## Agency colors (data encoding only)

Source exact values from each agency's official brand guide — **do not guess**.
Store in OKLCH; each must pass contrast on both themes or carry a paired non-color
signal (label/shape).

| Token | Authority | Value | Source |
|---|---|---|---|
| `--agency-cta` | Chicago Transit Authority | TODO | CTA brand guide |
| `--agency-pace` | Pace Suburban Bus | TODO | Pace brand guide |
| `--agency-metra` | Metra | TODO | Metra brand guide |
| `--agency-nita` | NITA | TODO | NITA brand guide (new agency) |

CTA rail-line colors (Red/Blue/Brown/Green/Orange/Purple/Pink/Yellow) may be needed
for rail-route rendering — add a `--line-*` group when the route layer is built.

## Type

| Token | Direction | Value |
|---|---|---|
| `--font-display` | condensed grotesk, transit-signage feel | TODO (pick + license-check) |
| `--font-body` | neutral grotesk | TODO |
| `--font-mono` | tabular numerals for all stats | TODO |

## Scale

Fluid type + spacing via `clamp()`. Define the min/max ramp here once chosen.

## Motion

| Token | Value |
|---|---|
| `--ease-standard` | TODO |
| `--dur-fast` / `--dur-slow` | TODO |
| reduced-motion | all of the above collapse to 0 / static |
