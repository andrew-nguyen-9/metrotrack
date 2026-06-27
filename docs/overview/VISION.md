# Vision — MetroTrack

**Tagline:** *Transit you can see.*

MetroTrack is a civic-accountability tracker for Chicagoland transit. Primary job:
**funding + service transparency** (A1); secondary: rider utility, then portfolio
showcase, then data journalism. Stance: **neutral, just-the-data** (A3).

## Premise

Chicagoland transit is being restructured (RTA → NITA) with a large funding
reallocation across CTA, Pace, and Metra. Public and political interest in *where
the money goes* and *who it serves* is high and there is no single accessible
tracker. This is that tracker.

> ⚠️ The governance/funding specifics (the NITA transition timing, dollar figures)
> must be verified against primary sources before they appear on the site. See
> `architecture/DATA_SOURCES.md`. The vision stands regardless of the exact numbers.

## Who it's for (priority order, A2)

1. **Engaged residents & riders** — "is my area served, and is it getting better or worse?"
2. **Policy / agency staff** — a sourced view to ground decisions.
3. **Journalists & advocates** — citable funding vs. service vs. staffing.
4. **Recruiters / Andrew** — a portfolio-grade geospatial + ETL build.

## The three pillars

1. **Funding** — budget vs. actuals for NITA / CTA / Pace / Metra over time, from
   RTAMS + the Chicago Data Portal. Charts, not just tables.
2. **Mapping** — routes and stops mapped against **population**, **jobs** (Census
   LODES), and **destinations** (Overpass/OSM: shopping, airports, attractions,
   sports + music venues, commercial). The analytic core: *who can reach what*.
3. **Hiring** — vacancy rates and understaffing per authority, scraped weekly from
   career pages into a **time series** so the trend (not a snapshot) is the product.

## Launch bar (v1 "done", O6=C)

All three pillars **plus the signature job-access feature**, all sourced:

- **Map explorer** a resident understands in 10 seconds: their neighborhood, nearby
  stops, jobs/destinations within a short walk + ride.
- **Job-access score** (`../modeling/ACCESS_SCORE.md`) — the signature analysis: how
  many jobs you can reach by transit in 15/30/45 min.
- **Funding dashboard** incl. a dedicated **"the $1.5B question"** explainer on the
  NITA reallocation (H4) — *built only once the figure is verified against primary
  sources; the dollar amount is a placeholder until then.*
- **Hiring/staffing** with the service-shortfall metric + its honesty caveat.
- **Methodology/Sources** page with per-metric formulas; every number dated.
- Runs on free tiers; nightly updates automatic.

### v1 subpages (D3)

Map explorer · Funding dashboard · Hiring/staffing · Methodology/Sources ·
per-authority profile pages (CTA/Pace/Metra/NITA, D4) · About · Data download/API
(N2). Per-route = drill-down panel only, standalone pages deferred (D5); per-stop =
hover/click panel, no page (D6/E8). Entry point: route/stop search (D8).

## Explicit non-goals (v1)

- Real-time trip planning (Google/Transit already do this).
- Predictive modeling beyond a simple baseline (forecasting is a *later* phase).
- Coverage outside the NITA service area.
