# Data Sources

Every published figure traces to a row here. Fill `License` and `Verified` before
a source's data ships to the site. Verify all funding/governance numbers against
the primary source — do not publish second-hand current-events claims.

| Source | Pillar | What | Auth | Refresh | License | Verified |
|---|---|---|---|---|---|---|
| Chicago Data Portal (Socrata) | funding, mapping | ridership, L-station entries, headcounts, shapefiles | none / app token (optional) | nightly | TBD | ☐ |
| RTAMS | funding | CTA/Pace/Metra financials, capital projects, ridership history | none | monthly | TBD | ☐ |
| **CTA — Ridership, Bus Routes, Monthly Day-Type Averages & Totals** (Chicago Data Portal Socrata `bynn-gwxy`) | ridership | **ridership by line** — monthly total boardings per CTA bus route (`monthtotal`), windowed 2021→ | **none** (key-free Socrata JSON; SOCATRA key = higher limits) | monthly | public (City of Chicago open data ToU) | ☐ (v3.6 — SourceTag id `ridership`) |
| **CTA — Ridership, 'L' Station Entries, Monthly Day-Type Averages & Totals** (Chicago Data Portal Socrata `t2rn-p8d7`) | ridership | **ridership by stop** — monthly total entries per CTA 'L' station (`monthtotal`), windowed 2021→ | **none** (key-free Socrata JSON) | monthly | public (City of Chicago open data ToU) | ☐ (v3.6 — SourceTag id `ridership`) |
| Metra / Pace ridership | ridership | per-line / per-stop ridership | — | — | **no free structured feed** (PDF monthly reports only) | ☐ (v3.6 — scaffolded, DataState "coming"; NTD annual system totals shown on funding) |
| FTA **National Transit Database** — Annual Data View, Metrics (by Agency) (DOT Socrata `g27i-aq2u`) | funding | **actual** audited operating expense, fare revenue, unlinked trips by agency × year (CTA/Metra/Pace subset) | **none** (key-free Socrata JSON/CSV) | annual | public domain (US Gov) | ☐ (v1.2.2) |
| **NTD-internal efficiency ratios** (derived, e8) — SourceTag id `funding-ntd-ratios` | funding | **farebox recovery** (fare ÷ opex), **subsidy per rider** ((opex − fare) ÷ unlinked trips), **cost per rider** (opex ÷ unlinked trips), by agency × year | derived from the NTD row above (no new fetch, same receipt) | annual | public domain (US Gov) | ☐ (v3.8 — computed in `gold_funding`, ratio-bounds tested by `assert_gold_funding_ratios.sql`; single-source, no cross-source mixing) |
| **RTA adopted Operating Budget** (budget book / quarterly financial report, PDF) | funding | **budgeted** operating expense by service board × year | none | annual | public record | ☐ (v1.2.2 — transcribed w/ citation in `data/bronze/rta/SOURCE.md`; **PDF-only, no structured export**) |
| GTFS static — **CTA** `transitchicago.com/downloads/sch_data/google_transit.zip` (bus + 'L' rail, one feed), **Metra** `schedules.metrarail.com/gtfs/schedule.zip` (commuter rail), **Pace** `pacebus.com/gtfs` (rotating dated `GTFS.zip`, suburban bus) | mapping | routes, stops (all agencies + modes); `mode` normalized from GTFS `route_type` (0/1→rail, 2→commuter-rail, 3/11→bus) via dbt macro `route_mode` | none | weekly | open (agency GTFS, redistribution permitted) | ☐ (v3.3 — all 3 agencies' bus/rail/commuter-rail routes+stops in gold + tiles) |
| GTFS-realtime (CTA Bus/Train Tracker, Pace) | mapping | live positions, headways → usage | API key (free) | live / sampled | TBD | ☐ |
| **Service-coordination candidates** (derived, e7) — SourceTag id `coordination` | mapping | cross-agency stop pairs within a walkable transfer radius (400 m) with **great-circle distance** (`ST_Distance_Sphere` / `ST_DWithin` on geography), an expected transfer wait, and a closeness+mismatch **score** | derived from the GTFS-static row above (stop geometry) + representative agency headways below | — | open | ☐ (v3.7 — `gold_stop_pairs`, uniqueness + not-null tested; served to `coordination.astro`) |
| **Representative published headways** (per agency) — used by `coordination` | mapping | one typical published headway per agency (**CTA** ~10 min `transitchicago.com/schedules`, **Metra** ~60 min off-peak `metra.com/maps-schedules`, **Pace** ~30 min `pacebus.com/schedules`) | agency public schedule pages | as published | open (agency schedules) | ☐ (v3.7 — dbt seed `service_headways`; **representative, NOT real-time** — a GTFS-realtime feed would sharpen them) |
| US Census LEHD **LODES8** (WAC `S000 JT00`) | mapping | block-level jobs (workplace), `C000` total | **none** (key-free `.csv.gz`) | annual | public domain | ☐ |
| US Census **2020 Centers of Population** (block-group, IL `BG17`) | mapping | block-group population + centroid lat/lng (binning source for v1.1) | **none** (key-free `.txt`) | decennial | public domain | ☐ |
| US Census **ACS 5-year, table-based Summary File** (`acsdt5y{year}-{table}.dat`, tables **B01003** total population + **B19013** median household income; vintages **2021** & **2023**, both on 2020 census tracts) | mapping (demographic change) | per-tract + county-rollup population + median-income change over two vintages (Cook County) | **none** (key-free `.dat`; the Census *Data API* needs a key, the Summary File does not) | annual | public domain (US Gov) | ☐ (v3.9; both vintages ingested as bronze receipts `data/bronze/chicago/census/acs_{2021,2023}.parquet`; median income is nominal, not inflation-adjusted) |
| US Census LODES8 **prior vintage** (WAC `S000 JT00`, e.g. 2019) + **2010 Centers of Population** (block-group, IL `BG17`) | tod | jobs + population growth baseline (like-for-like prior-vintage totals, binned to the same H3 grid) | **none** (key-free) | annual / decennial | public domain | ☐ (v3.10) |
| Authored **CBD anchors** (`metros/<slug>.toml` `[[cbd]]`) | tod | central-business-district id/name/lat/lon for the time-to-CBD metric (data-driven, N per metro; Chicago = the Loop) | none (config) | as authored | project config | ☐ (v3.10) |
| US Census **ACS** | mapping | population, demographics | API key (free) | annual | public domain | ☐ (deferred past v1.1) |
| Overpass / OpenStreetMap | mapping | POIs: shops, airports, attractions, venues | none | monthly | ODbL (attribution req.) | ☐ |
| Authority career pages — **CTA** `chicagotransit.taleo.net` (Taleo), **Metra** `cta.cadienttalent.com` (Cadient, `MetraKTMDReqExt`), **Pace** `pacebus.com/careers` (Drupal) | hiring | open job postings (count) per authority, weekly snapshot | none (polite scrape) | weekly | site ToS — robots: CTA `/careers/` allowed, Pace `/careers` allowed, Metra 403 to generic clients (public ATS used) | ☐ (v1.3.2; rendered listing saved as receipt) |
| NITA / state legislation | funding, vision | governance, the funding reallocation figures | none | as published | public record | ☐ |
| openrouteservice | mapping (access) | walk/street routing + isochrones | API key (free, env `ORS_API_KEY`) | on-demand + nightly precompute | ORS terms | ☐ (v1.4: loader built + tested vs committed sample. v3.5: **job-access page** publishes the ambient score as a **straight-line ½-mi walkshed** (`gold_hex_access`), labeled as such on-page. ORS street-network isochrone ambient precompute — batch, cached, rate-limited — is a scheduled spike (ACCESS_SCORE.md open questions), not yet wired; the published number is straight-line regardless of whether a key is set) |
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
