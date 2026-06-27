# v1 — Idea Backlog

Seed ideas. Graduate the chosen ones into phase plans; let the rest sit. Add to
this as ideas surface during phases (the closeout ritual feeds the next file).

## Mapping
- Isochrones from major hubs (Loop, O'Hare, Midway) — travel-time polygons over jobs.
- H3 hex layer: jobs-per-hex vs. stops-per-hex → "transit desert" score.
- Toggle layers: population density · jobs · destinations · ridership.
- Destination categories from OSM: shopping, airports, attractions, sports venues,
  music venues, day-to-day commercial.
- GTFS-realtime: live bus positions + headway reliability as a usage proxy.

## Funding
- Budget vs. actuals small-multiples per authority.
- $ per rider and $ per service-hour, trended.
- Capital project map (where the money is physically going).
- The NITA reallocation: before/after share by authority (once sourced).

## Hiring
- Vacancy rate per authority over time (the time series is the product).
- Open reqs by role family (operators vs. mechanics vs. admin).
- Overlay: understaffing vs. service cuts vs. ridership — does staffing predict service?

## Analysis (likely v1.4+)
- Baseline forecast of vacancy rate (statsmodels/Prophet) — heuristic first.
- "Access score" combining stop proximity + frequency + reachable jobs.

---

# Additional feature ideas (candidate v2+)

Grouped by theme. Each tagged `[skill]` (what it grows) and `[source]`. ⭐ = signature
bet worth a whole phase. Graduate the strong ones; the rest stay parked.

## Equity & access (the analytic heart) ⭐
- ⭐ **Job-access score** — # of jobs reachable by transit in 30/45/60 min from each
  block. The canonical accessibility metric; the site's most defensible "so what."
  `[isochrones + GTFS routing]` `[GTFS, LODES]`
- **Car-vs-transit gap** — same destination, drive time vs transit time, mapped.
  Surfaces where transit is non-competitive. `[isochrones]` `[GTFS, OSM/ORS]`
- **Transit equity index** — service quality (frequency/access) overlaid on income +
  race (ACS). An environmental-justice lens; high journalistic value.
  `[choropleth, normalization]` `[ACS]`
- **Transit deserts** — population/jobs present, frequent service absent. Falls out
  of the H3 hex layer already planned. `[H3 binning]` `[LODES, GTFS]`

## Funding transparency ⭐
- ⭐ **"Where the money goes" Sankey** — revenue sources → authority → ops/capital.
  One image that explains the whole funding picture. `[Sankey/ECharts]` `[RTAMS]`
- **Capital project tracker** — status, budget, delay, on a map. `[geo + status viz]` `[RTAMS]`
- **Fiscal-cliff timeline** — projected operating deficit vs. the funding runway.
  Timely given the NITA transition. `[time-series]` `[RTAMS, state docs]`
- **Efficiency leaderboard** — farebox recovery, $/rider, subsidy/trip, trended per
  authority. `[ratios]` `[RTAMS, Socrata]`

## Service quality & reliability
- **On-time / bunching detector** from realtime feeds. `[realtime stream processing]` `[GTFS-rt]`
- **Rail slow-zone map** — CTA publishes slow-zone data; animate it over time. `[geo + time]` `[CTA]`
- **Crowding heatmap** by route/time from APC ridership. `[heatmap]` `[Socrata]`
- **Service-change diff** — compare GTFS versions over time → "your route got cut."
  Directly visualizes the staffing→service story. `[GTFS diffing]` `[GTFS history]`

## Rider-facing tools
- ⭐ **"My commute"** — enter home + work → personal access score, nearby stops,
  reachable jobs, and the shortfall on *your* routes. Makes it personal. `[routing]` `[all]`
- **Stop dashboard** — per-stop ridership trend, nearby POIs, reliability.
- **Live service alerts** overlaid on the map. `[GTFS-rt alerts]`
- **Bike + transit** — Divvy station overlay for first/last-mile. `[geo join]` `[Divvy GBFS]`

## Workforce (extends the hiring pillar)
- **Shortage ↔ service correlation** — vacancy postings vs service-shortfall on one
  chart. The thesis of the whole hiring pillar, made visual. `[correlation]`
- **Time-to-fill / wage comparison** across authorities, if obtainable. `[scrape]`

## Civic / open-data (portfolio flex)
- **Open the data** — publish gold tables as CSV/GeoJSON + a tiny read API. Civic
  good and a strong portfolio signal. `[API design]`
- **Embeddable widgets** — iframe a chart/map for journalists. `[embed/OG]`
- **Share cards** — OG snapshot of a route/neighborhood (reuse the trivia share-card
  pattern). `[@vercel/og]`
- **Board-meeting + budget calendar** with agenda links. `[ICS/scrape]`

## Analytics depth (skill-building)
- **Forecasting** — ridership recovery, vacancy + shortfall trend. Heuristic →
  statsmodels/Prophet before ML. `[time-series forecasting]`
- **Anomaly detection** — flag a route falling off a cliff. `[stats]`
- ⭐ **Scenario tool** — "if NITA shifts $X to bus, projected access change." The most
  ambitious; ties funding ↔ access into a model. `[modeling]`
- **"As-of" time-travel slider** — replay the network/funding/staffing at any past
  date. `[versioned data]`

## Monetization & analytics (v2 research, from O3)
- **Server-side analytics gateway** — proxy events server-side; fan out to GA4,
  Meta/Facebook, Snap, TikTok, Bing, Google Ads, Pinterest, LinkedIn pixels from one
  first-party endpoint. `[server-side tagging]`
- **Privacy-masking ad revenue** — explore clean ad/affiliate revenue with user-info
  masking (hashed/aggregated identifiers, no raw PII forwarded).
  ⚠️ **Tension to resolve:** this conflicts with the v1 "privacy-friendly analytics"
  stance (O3=A) and the neutral civic positioning (A3). Decide the line before
  building — a transparency tracker that quietly monetizes user data is a credibility
  risk. Likely outcome: first-party aggregate analytics only; ads (if any) are
  context-targeted, not user-tracked. Needs its own ADR + a public privacy policy.

## Deferred / non-goals
- Real-time trip planning (Google/Transit own this).
- Coverage beyond the NITA service area.
- ML models beyond a simple baseline (until a heuristic measurably falls short).
- Public comment / annotation layer — moderation cost > v1 value.
