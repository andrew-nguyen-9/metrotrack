# Design Assets

Brand + visual source files. The *written* design contract is in
[`../docs/design-system/`](../docs/design-system/) — this folder is the artwork.

## Logos

Generated via Claude design (questionnaire B3). Source: `MetroTrack Logos.dc.html`
(open to re-edit). Exported SVGs in `logos/`, named `metrotrack-<city>-<format>.svg`.

**Chosen variant: `chicago`** — launch scope is the Chicagoland/NITA region. Keep
`global` as a neutral fallback; other cities are template variants, not used.

| Format | File | Use |
|---|---|---|
| `route` | `logos/metrotrack-chicago-route.svg` | Icon / compact mark (nav, small spaces) |
| `square` | `logos/metrotrack-chicago-square.svg` | Favicon, app icon, OG square |
| `wide` | `logos/metrotrack-chicago-wide.svg` | Wordmark / header / hero |

## Implementation status

**Queued for `v1.0.1`** (frontend scaffold). When `frontend/` (Astro) exists:
- Copy the three Chicago SVGs into `frontend/public/`.
- Wire favicon + apple-touch + OG image; use `wide` in the header, `route` as the
  compact mark.
- Verify the mark holds on both themes (dark default + light) per the design guideline.

Not implemented yet — no frontend to implement into (no code before the plan, per
`CLAUDE.md`).

## Other design artifacts

Map mockups, chart studies, and screenshot QA references go here as they're produced
(mirrors the `mocks/` folder pattern in the fantasy-football-tool repo).
