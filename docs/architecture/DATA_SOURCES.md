# Data Sources

Every published figure traces to a row here. Fill `License` and `Verified` before
a source's data ships to the site. Verify all funding/governance numbers against
the primary source — do not publish second-hand current-events claims.

| Source | Pillar | What | Auth | Refresh | License | Verified |
|---|---|---|---|---|---|---|
| Chicago Data Portal (Socrata) | funding, mapping | ridership, L-station entries, headcounts, shapefiles | none / app token (optional) | nightly | TBD | ☐ |
| RTAMS | funding | CTA/Pace/Metra financials, capital projects, ridership history | none | monthly | TBD | ☐ |
| FTA **National Transit Database** — Annual Data View, Metrics (by Agency) (DOT Socrata `g27i-aq2u`) | funding | **actual** audited operating expense, fare revenue, unlinked trips by agency × year (CTA/Metra/Pace subset) | **none** (key-free Socrata JSON/CSV) | annual | public domain (US Gov) | ☐ (v1.2.2) |
| **RTA adopted Operating Budget** (budget book / quarterly financial report, PDF) | funding | **budgeted** operating expense by service board × year | none | annual | public record | ☐ (v1.2.2 — transcribed w/ citation in `data/bronze/rta/SOURCE.md`; **PDF-only, no structured export**) |
| GTFS static (CTA, Pace, Metra) | mapping | routes, stops, schedules | none | weekly | TBD | ☐ |
| GTFS-realtime (CTA Bus/Train Tracker, Pace) | mapping | live positions, headways → usage | API key (free) | live / sampled | TBD | ☐ |
| US Census LEHD **LODES8** (WAC `S000 JT00`) | mapping | block-level jobs (workplace), `C000` total | **none** (key-free `.csv.gz`) | annual | public domain | ☐ |
| US Census **2020 Centers of Population** (block-group, IL `BG17`) | mapping | block-group population + centroid lat/lng (binning source for v1.1) | **none** (key-free `.txt`) | decennial | public domain | ☐ |
| US Census LODES8 **prior vintage** (WAC `S000 JT00`, e.g. 2019) + **2010 Centers of Population** (block-group, IL `BG17`) | tod | jobs + population growth baseline (like-for-like prior-vintage totals, binned to the same H3 grid) | **none** (key-free) | annual / decennial | public domain | ☐ (v3.10) |
| Authored **CBD anchors** (`metros/<slug>.toml` `[[cbd]]`) | tod | central-business-district id/name/lat/lon for the time-to-CBD metric (data-driven, N per metro; Chicago = the Loop) | none (config) | as authored | project config | ☐ (v3.10) |
| US Census **ACS** | mapping | population, demographics | API key (free) | annual | public domain | ☐ (deferred past v1.1) |
| Overpass / OpenStreetMap | mapping | POIs: shops, airports, attractions, venues | none | monthly | ODbL (attribution req.) | ☐ |
| Authority career pages — **CTA** `chicagotransit.taleo.net` (Taleo), **Metra** `cta.cadienttalent.com` (Cadient, `MetraKTMDReqExt`), **Pace** `pacebus.com/careers` (Drupal) | hiring | open job postings (count) per authority, weekly snapshot | none (polite scrape) | weekly | site ToS — robots: CTA `/careers/` allowed, Pace `/careers` allowed, Metra 403 to generic clients (public ATS used) | ☐ (v1.3.2; rendered listing saved as receipt) |
| NITA / state legislation | funding, vision | governance, the funding reallocation figures | none | as published | public record | ☐ |
| openrouteservice | mapping (access) | walk/street routing + isochrones | API key (free, env `ORS_API_KEY`) | on-demand + nightly precompute | ORS terms | ☐ (v1.4: loader built + tested vs committed sample; **no key configured**, so the published ambient access metric is a straight-line walkshed — ORS network isochrones activate when `ORS_API_KEY` is set) |
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

## Supabase project split

Two free-tier Supabase projects are provisioned (10GB pooled, 5GB each), but the
data-domain split is **deferred**. As of v1.0.2:

- **Project A** (`anooxzkkffyekcuprdzb`) is the **spine** — it holds the v1.0
  foundation schema (`authorities`, `routes`, `stops`; see `db/schema.sql`) and is
  the only project the pipeline writes to for now.
- **Project B** (`zqericbsgvaxjpmjyghf`) is **intentionally empty**. Which data
  domain (e.g. high-volume ridership/GTFS-rt time series) migrates to B is a later
  decision, made when storage on A approaches the 5GB tier. Record the cut here
  when it happens.
