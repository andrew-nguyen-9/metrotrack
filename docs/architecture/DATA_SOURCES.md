# Data Sources

Every published figure traces to a row here. Fill `License` and `Verified` before
a source's data ships to the site. Verify all funding/governance numbers against
the primary source — do not publish second-hand current-events claims.

| Source | Pillar | What | Auth | Refresh | License | Verified |
|---|---|---|---|---|---|---|
| Chicago Data Portal (Socrata) | funding, mapping | ridership, L-station entries, headcounts, shapefiles | none / app token (optional) | nightly | TBD | ☐ |
| RTAMS | funding | CTA/Pace/Metra financials, capital projects, ridership history | none | monthly | TBD | ☐ |
| GTFS static (CTA, Pace, Metra) | mapping | routes, stops, schedules | none | weekly | TBD | ☐ |
| GTFS-realtime (CTA Bus/Train Tracker, Pace) | mapping | live positions, headways → usage | API key (free) | live / sampled | TBD | ☐ |
| US Census LEHD **LODES** | mapping | block-level jobs (where people work) | none | annual | public domain | ☐ |
| US Census **ACS** | mapping | population, demographics | API key (free) | annual | public domain | ☐ |
| Overpass / OpenStreetMap | mapping | POIs: shops, airports, attractions, venues | none | monthly | ODbL (attribution req.) | ☐ |
| Authority career pages | hiring | open reqs, budgeted vs filled headcount | none (scrape) | weekly | site ToS — check | ☐ |
| NITA / state legislation | funding, vision | governance, the funding reallocation figures | none | as published | public record | ☐ |
| openrouteservice | mapping (access) | walk/street routing + isochrones | API key (free) | on-demand + nightly precompute | ORS terms | ☐ |
| Agency delivered-service reports | hiring | actual vs scheduled service (reconcile w/ GTFS-rt, G6) | none | as published | public record | ☐ |
| Divvy (GBFS) | mapping (v2) | bikeshare stations, first/last-mile | none | live | Lyft/NABSA terms | ☐ |

## Rules

- **Bronze is the receipt.** Every row served must be reproducible from a committed
  bronze snapshot under `data/`.
- **Attribution.** OSM (ODbL) and any other attribution-required source get a credit
  line in the site footer.
- **Scrape politely.** Rate-limit, cache, respect `robots.txt`/ToS; the weekly
  cadence is deliberate. If a career page forbids scraping, record it here and find
  an alternative (FOIA, official postings feed).
- **Dates on everything.** Each figure on the site shows its `as of` date.
