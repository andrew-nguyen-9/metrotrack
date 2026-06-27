# Modeling: Job-Access Score (the v1 signature feature)

The launch bar includes this (questionnaire O6=C). It's the site's most defensible
"so what": **how many jobs can you reach by transit, from where you are, in a
reasonable time.** Standard transit-accessibility metric, computed for the whole
region and surfaced both ambiently (a hex layer) and on-demand (click → isochrone).

## Definition

```
access_score(origin, cutoff, departure) =
    Σ jobs(d) for every destination block d reachable from origin
              by transit within `cutoff` minutes, departing at `departure`
```

- **Origin unit:** H3 hexes, res 8/9 (G4) — pre-computed for ambient layer; arbitrary
  clicked point for on-demand.
- **Cutoffs:** **15 / 30 / 45 min** (G2). Three rings.
- **Departure:** **user-selectable** (G3) — Weekday AM peak / Midday off-peak /
  Weekday PM peak / daily average. Default AM peak.
- **Jobs source:** Census LEHD **LODES** block-level (`DATA_SOURCES.md`).
- **Walk legs:** access/egress within **½ mi** of a stop (G5).

## Engine

**openrouteservice** (free API, G1 / [`../decisions/ADR-003-routing-openrouteservice.md`](../decisions/ADR-003-routing-openrouteservice.md))
for street/walk routing + isochrones; transit legs from GTFS. For the ambient hex
layer, precompute access in the nightly pipeline (batch, cached) — never call ORS
live for every hex. On-demand point clicks call ORS for a single isochrone (within
free rate limits; cache by rounded coordinate + cutoff + departure).

## Surfacing (UI)

- **Ambient:** per-hex `access_score` choropleth (E9=C — point + ambient both).
- **On-demand:** click a point → isochrone polygons bloom (the signature motion) +
  a reachable-jobs count-up; compare against the regional median.
- **Equity overlay:** access vs income/race/vehicle-access (ACS, G7) to show *who*
  has access — the equity story.
- **Honesty:** show as an **estimate with a range** (G9); state assumptions
  (cutoff, departure, walk radius) inline.

## Normalization

Report both **absolute** reachable jobs and **per-capita / relative** (G10) so a
dense area's raw count doesn't drown out an underserved area's *deficit*.

## Pipeline outputs (gold)

- `hex_access` — `{h3, cutoff, departure, jobs_reachable, pct_of_region_median, as_of}`
- `hex_equity` — `{h3, access_score, median_income, pct_minority, pct_zero_vehicle}`

## Open questions (resolve in v1.4 plan)

- ORS free-tier isochrone quota vs. hex count — confirm batch precompute fits, else
  coarsen hex resolution or cache aggressively.
- GTFS-to-ORS transit-leg integration approach (ORS does street; transit graph
  needs a GTFS router — evaluate `r5py` / OpenTripPlanner vs. ORS public-transport).
  **This is the main v1.4 spike** — systematic-debugging / brainstorming first.
