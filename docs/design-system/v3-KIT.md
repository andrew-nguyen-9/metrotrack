# v3 Component Kit — "Field Instrument"

The shared kit every v3 page + island builds on (E1 foundation). Import via the
`@/*` alias (= `frontend/src/*`). Tokens: [`TOKENS.md`](TOKENS.md) ·
[`globals.css`](../../frontend/src/styles/globals.css). Reference page:
[`hiring.astro`](../../frontend/src/pages/[metro]/hiring.astro).

**Rule for every downstream epic:** build your page from this kit; don't
re-decide the spine. Never hardcode hex — reference tokens.

## Shell (`@/components/shell/`, `@/layouts/Base.astro`)

- `Base.astro` — page layout. `<Base metro={metro} title=… description=…>`. Hosts
  the skip-link, header (logo + `Nav` + `Toolbar`), `<main id="main">`, `Footer`,
  and the **pre-paint inline script** that applies a11y/theme prefs (no FOUC).
- `Nav.astro` — `<Nav metro here={pathname} />`. Per-metro primary nav.
- `Footer.astro` — `<Footer metro />`. Attribution + links + button → an9.dev.
- `Toolbar.astro` — hosts the one toggle island (`client:load`).
- `Toggles.tsx` — the ONE a11y/theme island. Don't add more islands for prefs.

## A11y / theme toggle contract (data-* on `<html>`, localStorage)

| Preference | Attribute | localStorage | Values |
|---|---|---|---|
| Theme | `data-theme` | `mt-theme` | `light` · absent = dark |
| Colorblind | `data-colorblind` | `mt-colorblind` | `on` · absent |
| Reduce motion | `data-motion` | `mt-motion` | `reduce` · absent |
| Text size | `data-text-size` | `mt-text-size` | `s` · `l` · absent = m |

CSS reacts to these attrs (see globals.css). Charts/maps that need to restyle on
theme/colorblind change should observe them (chart hook does this for you).

## Layout primitives (`@/components/kit/`) — tokens + Tailwind only

- `Stack.astro` — vertical rhythm. `<Stack gap="md" as="section">`. gap = space key.
- `Cluster.astro` — wrapping row. `<Cluster gap="sm" justify="between">`.
- `Grid.astro` — auto-fit card grid. `<Grid min="16rem" gap="md">`.
- `Sidebar.astro` — content + collapsing rail (map + controls). `side` slot + default slot.
- `Frame.astro` — aspect-ratio media box (no CLS). `<Frame ratio="16/9">`.
- `Bleed.astro` — full-viewport-width breakout (reserved for the map).

## Data primitives (`@/components/kit/`)

- `Stat.astro` — `<Stat value label hint? delta={{value,dir,tone}}? />`. Big tabular figure; delta arrow is redundant with color.
- `StatBand.astro` — responsive row of `Stat`s (wrap in default slot).
- `SourceTag.astro` — `<SourceTag source id? asOf? href? note? />`. **Required beside every published figure**; `id` = DATA_SOURCES.md row.
- `DataState.astro` — `<DataState state="empty|loading|error|coming" title? message? />`. The honest-scaffold state; never fabricate a number.
- `Legend.astro` — `<Legend items={[{label,color,shape,dash}]} />`. Color never sole signal.
- `Callout.astro` — `<Callout tone="note|warning|accent" title?>…</Callout>`. Caveats / warnings.
- `Card.astro` — `<Card title? href? status="live|soon">…</Card>`. `soon` = coming-soon variant (E2 directory).

## Chart shell (`@/lib/chart.ts`)

`useChartTheme()` → `{text,muted,line,accent,cat[]}` read from tokens, **re-reads
live** on theme/colorblind toggle. `SERIES_SYMBOLS` for per-series marker
redundancy. Wire ECharts: `series[i].color = theme.cat[i%len]`,
`series[i].symbol = SERIES_SYMBOLS[i%len]`, axis/legend colors from `theme`.
Reference: `@/components/VacancyChart.tsx`. Keep the no-JS table fallback.

## Map shell (`@/components/MapShell.tsx`)

`<MapShell buildStyle bbox ariaLabel onReady={(map)=>…} errorMessage? >` +
`<MapPanel label>` for the legend/control chrome. MapShell owns PMTiles protocol,
reduced-motion-aware init, NavigationControl, resize+refit, and the error banner;
you own style + layers + popups (via `onReady(map)`) + the panel UI + a table
fallback. Reference consumer: `@/components/TransitMap.tsx`.

## Adding a page

1. `src/pages/[metro]/<name>.astro`, `export const getStaticPaths = metroPaths;`
2. `<Base metro={metro} title=…>` → compose `Stack` + kit components.
3. Every figure gets a `SourceTag`; every chart/map gets a no-JS table fallback.
4. Add the nav item in `@/components/shell/Nav.astro`.
5. QA: `astro check` + `astro build`; toggles persist; light/dark/colorblind AA;
   empty/loading/error states; Lighthouse ≥90 mobile.
