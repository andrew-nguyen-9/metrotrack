# Design & Scope Questionnaire

Front-load the decisions so design + implementation are unblocked. Pick one per
question (mark the letter or edit in place); ⭐ = my recommended default given prior
decisions (Supabase+PostGIS, mapping-first, service-shortfall metric, free-tier).
Add notes after `→`. "Other" is always allowed. Skip what you don't care about yet.

Decisions that survive get promoted into `phases/`, `design-system/`, and ADRs.

---

## A · Product scope & positioning

**A1. Primary job of the site?**
a) Civic accountability tool (funding/service transparency) ⭐
b) Rider utility (find/score my service)
c) Data-journalism platform (story-driven)
d) Portfolio showcase of analytics skill
→ A -> B -> D -> C

**A2. Who is the #1 audience?**
a) Engaged residents/riders ⭐  b) Journalists/advocates  c) Policy/agency staff  d) Recruiters viewing your portfolio
→ A -> C -> B -> D

**A3. Editorial stance?**
a) Neutral, just-the-data ⭐  b) Pro-transit advocacy  c) Watchdog/critical
→ A

**A4. Geographic scope at launch?**
a) Full NITA region (CTA+Pace+Metra) ⭐  b) CTA/Chicago only first  c) Chicago + inner suburbs
→ A

**A5. Update cadence promised to users?**
a) Nightly data, "as of" dated ⭐  b) Weekly  c) Real-time where feeds allow
→ A

**A6. Mobile vs desktop priority?**
a) Mobile-first, desktop-excellent ⭐  b) Desktop-first (data-dense), mobile-OK
→ A

---

## B · Brand, name & voice

**B1. Public name?**
a) Keep "CTA Tracker"  b) Region-accurate ("Chicagoland Transit Tracker") ⭐
c) Branded coinage (e.g. "Transit Pulse", "RidesIL")  d) Decide later
→ MetroTrack (Please rename the repo to 'metrotrack' from 'CTA')

**B2. Tone of copy?**
a) Clear/civic/plain ⭐  b) Sharp/editorial  c) Playful/approachable
→ A

**B3. Logo direction?**
a) Mark from transit iconography (route line/node) ⭐  b) Wordmark only
c) Map-fragment motif  d) None for v1
→ Use the claude_design MCP (https://api.anthropic.com/v1/design/mcp, auth via /design-login) to import this project:
https://claude.ai/design/p/7a106bc6-706f-4b06-90a7-60d2d2495471?file=MetroTrack+Logos.dc.html

Implement: metrotrack-logos.dc.html

**B4. Tagline?**
a) Function-first ("Chicago transit, funded and mapped")  b) Mission ("Transit you can see")  c) None ⭐
→ B

**B5. Attribution/credibility framing?**
a) "Sources" footer + per-figure dates ⭐  b) Dedicated methodology page  c) Both ⭐
→ C

---

## C · Visual design system

**C1. Overall aesthetic?**
a) "Transit instrument panel" — dark-native, data-as-instruments (à la your FFB "Broadcast Instrument") ⭐
b) Clean civic/government (light, accessible, sober)
c) Editorial/newsroom (serif headlines, generous whitespace)
d) Map-forward, chrome-minimal
→ A

**C2. Default theme?**
a) Dark default + light toggle ⭐  b) Light default + dark toggle  c) Light only  d) System-follow
→ A

**C3. Accent strategy?**
a) One charged accent, rationed ⭐  b) Per-authority colors (CTA blue/Pace/Metra)  c) Sequential data palette only
→ A

**C4. Authority color coding — use official agency colors?**
a) Yes, official brand colors as data encoding ⭐  b) Custom palette (avoid brand confusion)  c) Neutral, no per-agency color
→ A

**C5. Typography — display face?**
a) Condensed grotesk (transit-signage feel) ⭐  b) Editorial serif  c) Neutral grotesk (one family)
→ A

**C6. Numerals?**
a) Mono/tabular everywhere ⭐  b) Proportional
→ A

**C7. Surface style?**
a) Flat civic cards  b) Frosted-glass panels + hairline borders ⭐  c) Borderless/airy
→ B

**C8. Motion budget?**
a) Functional only (transitions, no spectacle)  b) Restrained + 2-3 signature moments ⭐  c) Cinematic
→ B

**C9. Data-ink philosophy?**
a) Tufte-strict (max data-ink, min chrome) ⭐  b) Approachable (more labels/annotations)
→ A

**C10. Imagery?**
a) No photos, data + maps only ⭐  b) Station/city photography accents  c) Illustration
→ A but leave door open for B

---

## D · Information architecture & subpages

**D1. Top-level nav model?**
a) By pillar: Map · Funding · Hiring ⭐  b) By question ("Is my area served?", "Where's the money?")  c) Single scrolling dashboard
→ A

**D2. Landing page?**
a) Big map + headline stats ⭐  b) Story/scrollytelling intro  c) Dashboard of all three pillars  d) Search-first ("enter your address")
→ Mix of B and A

**D3. Subpages to build for v1 (multi-select — list letters):**
a) Map explorer ⭐  b) Funding dashboard ⭐  c) Hiring/staffing ⭐  d) Methodology/Sources ⭐
e) Per-authority profile pages  f) Per-route pages  g) Per-stop pages  h) About  i) Data download/API  j) Blog/updates
→ A, B, C, D, H, I, E, 

**D4. Per-authority profile pages (CTA/Pace/Metra/NITA)?**
a) Yes, one rich page each ⭐  b) Just sections on dashboards  c) Later
→ A

**D5. Per-route detail pages?**
a) Yes, generated for all routes  b) Top/notable routes only ⭐  c) Drill-down panel, no standalone page  d) Later
→ D

**D6. Per-stop pages?**
a) Yes  b) Hover/click panel only ⭐  c) Later
→ C

**D7. Methodology page depth?**
a) Full per-metric writeup + formulas ⭐  b) Short sources list  c) Link to docs/ in repo
→ A

**D8. Search/entry point?**
a) Address → "my transit" view ⭐  b) Route/stop search  c) Both  d) None for v1
→ B

---

## E · Map UX (the core surface)

**E1. Map base?**
a) Dark custom (PMTiles, minimal labels) ⭐  b) Light  c) Both toggle  d) Satellite option
→ A

**E2. Default map view?**
a) Whole region  b) Chicago + zoom-to-location prompt ⭐  c) Geolocate on load (with consent)
→ B

**E3. Layer control model?**
a) Toggleable layer stack (population/jobs/POIs/routes/access) ⭐  b) Preset "lenses" (one story at a time)  c) Both
→ A

**E4. Population/jobs rendering?**
a) H3 hexbins ⭐  b) Census-tract choropleth  c) Dot-density  d) Heatmap
→ A

**E5. Route rendering?**
a) All routes as lines, weight = ridership ⭐  b) Frequency-colored  c) Selectable single route
→ A

**E6. Stop rendering?**
a) Dots, size = ridership/access ⭐  b) Uniform dots  c) Cluster at low zoom
→ A

**E7. Destinations (POIs) display?**
a) Categorized icon layer, toggle per category ⭐  b) Heat of "things to reach"  c) Only in access calcs, not drawn
→ A

**E8. Primary interaction?**
a) Click a stop/area → side panel with stats ⭐  b) Hover tooltips  c) Both
→ B

**E9. The "access" visualization?**
a) Isochrone polygons from a clicked point ⭐  b) Per-hex access score choropleth  c) Both (point + ambient)
→ C

**E10. Map performance approach?**
a) deck.gl for big layers + MapLibre base ⭐  b) MapLibre native layers only  c) Decide by layer
→ A

**E11. Time dimension on the map?**
a) Static "current" v1, time-slider later ⭐  b) Time-slider in v1  c) None
→ A

---

## F · Charts & data viz

**F1. Charting library?**
a) Apache ECharts ⭐  b) Visx/D3 (custom)  c) Recharts  d) Observable Plot
→ A

**F2. Funding flow viz?**
a) Sankey (sources→authority→category) ⭐  b) Stacked bars  c) Treemap
→ A

**F3. Trends (ridership/funding/staffing)?**
a) Small-multiple line charts ⭐  b) One multi-series chart w/ toggles  c) Area charts
→ A

**F4. Comparison across authorities?**
a) Ranked bars / leaderboard ⭐  b) Radar  c) Bump chart over time
→ A

**F5. Annotations on charts (events, policy dates)?**
a) Yes, annotated timelines ⭐  b) Plain charts
→ A

**F6. Every chart has an accessible data table?**
a) Yes, toggle/expand ⭐  b) Download only  c) No
→ A

---

## G · Modeling & analysis

**G1. Job-access score — travel-time engine?**
a) openrouteservice (free API) ⭐  b) Self-host Valhalla/OSRM  c) GTFS-only graph (no street routing)
→ A

**G2. Access cutoffs?**
a) 30/45/60 min ⭐  b) 15/30/45  c) Single 45-min  d) User-adjustable
→ B

**G3. Access departure assumptions?**
a) Weekday AM peak ⭐  b) Midday off-peak  c) Average across day  d) User-selectable
→ D with options for A, B, C, Weekday PM peak 

**G4. Spatial unit for population/jobs analysis?**
a) H3 res-8/9 hexes ⭐  b) Census block groups  c) Census tracts
→ A

**G5. "Walk to stop" radius?**
a) ½ mi (≈800m) ⭐  b) ¼ mi  c) 10-min walk isochrone
→ A

**G6. Service-shortfall — delivered-service source priority?**
a) GTFS-realtime sampled vs scheduled ⭐  b) Agency published delivered-service reports  c) Both, reconcile
→ C

**G7. Equity overlay variables?**
a) Income + race + vehicle-access (ACS) ⭐  b) Income only  c) A composite vulnerability index
→ A

**G8. Forecasting in v1?**
a) No — descriptive only, forecast in v2 ⭐  b) Simple baseline (trend/seasonal)  c) Prophet/statsmodels
→ A

**G9. Confidence/uncertainty shown?**
a) Yes where modeled (ranges, "estimate") ⭐  b) Point values only
→ A

**G10. Normalization for fairness comparisons?**
a) Per-capita + per-service-hour ⭐  b) Absolute only  c) Both shown
→ C

---

## H · Funding pillar specifics

**H1. Granularity?**
a) Authority + category (ops/capital) ⭐  b) Authority only  c) Line-item where available
→ A

**H2. Budget vs actuals?**
a) Both, variance highlighted ⭐  b) Actuals only  c) Budget only
→ A

**H3. Time range?**
a) Last 10 yrs + projections ⭐  b) 5 yrs  c) Since NITA transition only
→ A

**H4. The NITA reallocation — feature it how?**
a) Dedicated "the $1.5B question" explainer (once sourced) ⭐  b) Just a data series  c) Skip until verified
→ A

**H5. Farebox/efficiency metrics?**
a) Recovery ratio + subsidy/trip ⭐  b) None  c) Full efficiency suite
→ C

**H6. Capital projects?**
a) Map + status tracker ⭐  b) Table  c) Later
→ A

---

## I · Mapping pillar specifics

**I1. Ridership data resolution?**
a) Route + stop level where available ⭐  b) Route only  c) System totals
→ A

**I2. Destination categories to include (multi-select):**
a) Grocery/shopping ⭐  b) Airports ⭐  c) Hospitals/healthcare ⭐  d) Tourist attractions ⭐
e) Sports venues ⭐  f) Music venues ⭐  g) Schools/universities  h) Parks  i) Major employers/commercial ⭐
→ A, B, C, D, E, F, G, H, I

**I3. Bike/first-last-mile (Divvy)?**
a) v2 overlay ⭐  b) v1  c) Never
→ A

**I4. Show transit deserts explicitly?**
a) Yes, named layer ⭐  b) Implicit in access score  c) Later
→ A

**I5. Realtime vehicle positions?**
a) v2 ⭐  b) v1 "live" layer  c) Never (use for stats only)
→ A

**I6. Compare modes (bus vs rail) on map?**
a) Toggle/filter ⭐  b) Combined only
→ A

---

## J · Hiring pillar specifics

**J1. Headline = service-shortfall (decided). Secondary series?**
a) Posting-based vacancy rate ⭐  b) None  c) Time-to-fill if scrapeable
→ A

**J2. Role granularity?**
a) Authority-wide + operator/mechanic/admin split ⭐  b) Authority-wide only
→ A

**J3. Scrape targets?**
a) Official career pages ⭐  b) Career pages + job boards (Indeed/etc.)  c) FOIA/board docs supplement
→ A

**J4. Causal honesty UI?**
a) Persistent "shortfall ≠ staffing alone" caveat ⭐  b) Footnote  c) Methodology page only
→ A

**J5. Correlation view (vacancy ↔ shortfall ↔ service cuts)?**
a) Yes, the pillar's centerpiece ⭐  b) Separate charts  c) v2
→ C

---

## K · Data & pipeline

**K1. DB-less local dev from committed bronze?**
a) Yes (repo works offline from data/) ⭐  b) Require live Supabase
→ B (will get its own free project with two separate storages of 5GB)

**K2. Bronze storage format?**
a) Parquet ⭐  b) JSONL  c) Mixed by source
→ A

**K3. Large geometry — commit or generate?**
a) Generate PMTiles in CI, don't commit ⭐  b) Commit tiles  c) Commit raw geo, build tiles in CI
→ A

**K4. Secrets/keys needed (confirm acceptable):**
a) Census API key + ORS key + GTFS-rt key, all free ⭐  b) Minimize — drop ORS, GTFS-only routing
→ A

**K5. Pipeline failure handling?**
a) Per-source health floor, fail loud, keep last-good ⭐  b) Fail whole run  c) Silent skip
→ A

**K6. Data versioning/history retention?**
a) Append-only snapshots, keep all ⭐  b) Rolling window  c) Latest only
→ A

---

## L · Tech & frontend

**L1. Framework?**
a) Next.js App Router ⭐  b) Astro (content-leaning)  c) Remix
→ B or C. Defer to you. I've been doing a lot of Next.js projects but want to expand my skills.

**L2. Rendering strategy?**
a) Static + ISR for data pages, client map ⭐  b) Mostly SSR  c) SPA
→ A

**L3. Styling?**
a) Tailwind + tokens ⭐  b) CSS modules  c) Vanilla-extract
→ A

**L4. Component lib?**
a) Headless (Radix) + custom ⭐  b) shadcn/ui  c) Fully bespoke
→ A

**L5. State/data fetching?**
a) Server components + Supabase client ⭐  b) TanStack Query  c) SWR
→ A

**L6. Map library (confirm)?**
a) MapLibre GL JS + deck.gl ⭐  b) MapLibre only  c) deck.gl only
→ A

---

## M · Accessibility & performance

**M1. A11y target?**
a) WCAG 2.2 AA, AAA body text ⭐  b) AA  c) Best-effort
→ A

**M2. Map accessibility fallback?**
a) Every map view has an equivalent data table/summary ⭐  b) ARIA on map only  c) Skip-to-data link
→ A

**M3. Colorblind-safe encodings?**
a) Mandatory — never color-only ⭐  b) Where feasible
→ A

**M4. Perf budget enforcement?**
a) Lighthouse CI gate on PRs ⭐  b) Manual checks  c) None
→ A

**M5. Reduced-motion?**
a) Full static fallbacks, mandatory ⭐  b) Honor where easy
→ A

---

## N · Engagement & civic

**N1. Shareability?**
a) OG share cards per route/area + embeds ⭐  b) Basic OG only  c) None v1
→ A

**N2. Open data?**
a) Publish gold tables (CSV/GeoJSON) + read API ⭐  b) Download only  c) v2  d) No
→ A

**N3. Email/newsletter for updates?**
a) v2  b) v1 (Resend)  c) Never ⭐
→ C

**N4. "Contact your rep / take action"?**
a) v2, neutral info-only  b) Yes v1  c) No (stay neutral) ⭐
→ C

**N5. Saved views / personalization?**
a) localStorage "my area" ⭐  b) Accounts (overkill)  c) None
→ A

---

## O · Launch & ops

**O1. Hosting?**
a) Vercel (frontend) + Supabase + GitHub Actions ⭐  b) All-Vercel  c) Add Cloudflare R2 for tiles
→ A

**O2. Domain?**
a) New dedicated domain ⭐  b) Subdomain of an9.dev/portfolio  c) Vercel default for now
→ B (transit.an9.dev)

**O3. Analytics?**
a) Privacy-friendly (Plausible/Vercel Analytics) ⭐  b) GA4  c) None
→ A, look into server-side analytics with integrations into GA4, Facebook Pixel, Snap Pixel, TikTok Pixel, Bing Ads, GAds, Pinterest Pixel, LinkedIn Pixel, See if there are any clean ad-revenue generation techniques with a focus on masking user's information 

**O4. Error monitoring?**
a) Sentry free tier ⭐  b) Vercel logs only  c) None v1
→ A

**O5. License / open-source the repo?**
a) Public repo, MIT, data attributed ⭐  b) Public code, private data  c) Private
→ A

**O6. Launch bar — what's the v1 "done"?**
a) Map + funding + hiring + methodology, all sourced ⭐  b) Map pillar only, ship early  c) All + ⭐ signature feature (job-access)
→ C

---

## How to use this

1. Mark picks (edit letters / add `→` notes). Don't overthink ⭐ — override freely.
2. Hand it back; I'll promote answers into `phases/v1/` segment plans, the
   `design-system/` docs, and any new ADRs (e.g. routing engine, naming).
3. Anything you mark "Other" or leave blank becomes a brainstorming follow-up.
