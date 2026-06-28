# v2 — Scope & Build Questionnaire (200 MCQs)

Front-load the v2 decisions so planning + autonomous build are unblocked. Same
convention as [`DESIGN_QUESTIONNAIRE.md`](DESIGN_QUESTIONNAIRE.md): pick one per
question, ⭐ = my recommended default given prior decisions
(Supabase+PostGIS, Astro+islands, PMTiles, free-tier, "Transit Instrument Panel").
Add notes after `→`. "Other" always allowed. Skip what you don't care about yet.

Answers that survive graduate into `docs/phases/v2/`, `design-system/`, and ADRs.

**v2 theme:** go multi-city. Chicago becomes one metro under a MetroTrack
homepage; add NYC/SF then DC/Boston then LA/Philly then Seattle/Atlanta. Plus:
more pages, SEO, per-region RSS feeds, and mostly-autonomous one-prompt build loops.

**Storage reality (measured 2026-06-27):** Chicago gold DB = ~232 KB; bronze
receipts = 6.4 MB; PMTiles served static (off Supabase). Free-tier DB cap (500 MB)
fits ~2,000 metros — **storage is not the constraint.** Real limits: ETL compute
(Actions minutes), ORS isochrone quota, PMTiles bandwidth. Rollout order is set by
audience + data uniformity, not bytes.

---

## A · v2 framing & goals (A1–A8)

**A1. The headline job of v2?**
a) Multi-city expansion (Chicago → national) ⭐  b) Deepen Chicago modeling first  c) Growth/SEO/distribution  d) All three, sequenced
→ A

**A2. How many metros live by v2 close?**
a) 3 (Chicago+NYC+SF) ⭐  b) 5 (+DC+Boston)  c) 9 (full proposed list)  d) Chicago + 1 proof-of-concept
→ A

**A3. v2 success metric?**
a) N metros live with parity to Chicago ⭐  b) Organic search traffic  c) RSS/feed subscribers  d) Portfolio depth (skills shown)
→ A

**A4. Parity bar for a new metro = "done"?**
a) Map + funding + hiring + access, all 4 pillars ⭐  b) Map + access only  c) Map only, pillars follow  d) Per-metro configurable
→ A

**A5. Ship cadence within v2?**
a) One metro per segment, serially ⭐  b) Architecture segment, then metros in parallel  c) Big-bang all metros at end
→ A

**A6. Chicago's role post-v2?**
a) Reference implementation / golden test ⭐  b) Just another metro  c) Flagship with extra features
→ A

**A7. Scope discipline when a metro lacks a data source?**
a) Degrade gracefully, hide that pillar ⭐  b) Block the metro until parity  c) Show "data not available" placeholder
→ A

**A8. v2 explicitly excludes…?**
a) Auth/accounts ⭐  b) Real-time vehicle tracking  c) Non-US cities  d) Paid tiers  e) All of these ⭐
→ E

---

## B · Multi-city architecture (B1–B18)

**B1. Tenancy model in Postgres?**
a) Single DB, `metro_id` column on every table ⭐  b) Schema-per-metro  c) DB-per-metro (Supabase project each)  d) Single DB, table-per-metro
→ A

**B2. Where does `metro` live?**
a) New `metros` dimension table (slug, name, bbox, agencies, tz) ⭐  b) Hard-coded config file  c) Both: table mirrors config ⭐
→ C

**B3. RLS strategy with `metro_id`?**
a) Keep public-read on all, no per-metro restriction ⭐  b) Per-metro policies  c) Public-read + metro filter in views
→ A

**B4. URL scheme for a metro?**
a) Path: `/chicago`, `/nyc` ⭐  b) Subdomain: `chicago.transit.an9.dev`  c) Query: `?metro=chicago`
→ A

**B5. Per-metro page routing in Astro?**
a) Dynamic `[metro]/...` routes from `getStaticPaths` ⭐  b) Hand-built folders per metro  c) Single SPA, client-side metro switch
→ A

**B6. Metro config source of truth?**
a) `metros/<slug>.toml` (agencies, bbox, GTFS urls, source ids) ⭐  b) DB rows  c) Env vars  d) One big `metros.json`
→ A

**B7. How is "current metro" carried through islands?**
a) Astro prop → island, from route ⭐  b) Global store/context  c) URL param read client-side
→ A

**B8. Agency abstraction?**
a) `authorities` already generic → add `metro_id` FK ⭐  b) New `agencies` table per modal type  c) Keep per-metro bespoke
→ A

**B9. GTFS feed registry?**
a) `metros/<slug>.toml` lists feed urls + license ⭐  b) DB table `gtfs_feeds`  c) Hard-coded in pipeline
→ A

**B10. Cross-metro shared dims (e.g. NTD, LODES schema)?**
a) Shared tables keyed by metro/geoid ⭐  b) Duplicated per metro  c) Materialized views per metro over shared
→ A

**B11. Tile storage layout?**
a) One PMTiles per metro (`tiles/<slug>.pmtiles`) ⭐  b) One global PMTiles, filtered  c) Per-metro per-layer files
→ A

**B12. Map default viewport?**
a) From `metros.bbox` in config ⭐  b) Geolocate user  c) Fixed national, zoom on select
→ A

**B13. Adding a metro should require…?**
a) One config file + run pipeline `--metro=slug` ⭐  b) Config + a few code edits  c) A full new phase each time
→ A

**B14. Handle differing transit modes (subway/LRT/ferry/BRT)?**
a) Generic `route_type` (GTFS) drives styling ⭐  b) Per-metro mode config  c) Only bus+rail, ignore rest
→ A

**B15. Time zones across metros?**
a) Store UTC, render in metro tz from config ⭐  b) Store local  c) Ignore (all dates are "as of" daily)
→ A

**B16. Naming for the org concept above a metro (region vs metro vs city)?**
a) "Metro" everywhere ⭐  b) "City"  c) "Region"  d) "Metro area"
→ A

**B17. Migration path for existing Chicago tables?**
a) Add nullable `metro_id`, backfill 'chicago', set NOT NULL ⭐  b) New tables, migrate data  c) Rebuild from bronze
→ A

**B18. Cross-metro unique keys?**
a) Composite (metro_id, natural_key) everywhere ⭐  b) Global surrogate ids  c) Prefix natural keys with slug
→ A

---

## C · City selection & rollout order (C1–C14)

**C1. Confirm wave order?**
a) NYC,SF → DC,Boston → LA,Philly → Seattle,Atlanta ⭐  b) Reorder by ridership  c) Reorder by data ease  d) Let me re-rank
→ A

**C2. First metro after Chicago?**
a) SF (BART+Muni, clean GTFS, mid-size) ⭐  b) NYC (biggest impact, hardest)  c) DC (compact, WMATA)
→ A but include regional rail as well. From Wikipedia (Public transportation in the San Francisco Bay Area is quite extensive, including one rapid transit system, three commuter rail lines, two light rail systems, two ferry systems, Amtrak inter-city rail services, and four major overlapping bus agencies, in addition to dozens of smaller ones.)

**C3. Selection criteria weight?**
a) Ridership + audience size ⭐  b) Data uniformity/ease  c) Geographic spread  d) Equal blend ⭐
→ D

**C4. NYC special handling (MTA GTFS huge)?**
a) Validate O(n²) walkshed + tile size on NYC before committing ⭐  b) Subset to subway first  c) Treat like any metro
→ A

**C5. Multi-agency metros (SF=BART+Muni+AC+Caltrain)?**
a) Aggregate all into one metro ⭐  b) Primary agency only first  c) User toggles agencies
→ A

**C6. What gates promotion of the next metro?**
a) Prior metro passes parity QA ⭐  b) Time-boxed  c) Data availability check passes
→ A

**C7. Hiring/career-scrape per metro (fragile)?**
a) Best-effort per agency, skip if no career page ⭐  b) Require it for parity  c) Drop hiring pillar for non-Chicago in v2
→ A

**C8. Funding data per metro (varies wildly by state)?**
a) NTD operating $ as the uniform baseline ⭐  b) Per-metro primary-source dig  c) Skip funding outside Chicago in v2
→ A

**C9. Access-score routing cost per metro (ORS quota)?**
a) Nightly batch, cache aggressively, throttle ⭐  b) Self-host ORS for scale  c) Precompute once, refresh monthly ⭐
→ C, maybe A for some things

**C10. Census geography per metro?**
a) Auto-derive block groups from metro bbox ⭐  b) Curate county lists per metro  c) CBSA definition from Census
→ A

**C11. A metro that fails a data source mid-rollout?**
a) Ship with that pillar hidden, log gap ⭐  b) Hold the metro  c) Manual fallback data
→ A

**C12. Do we publish a public "coming soon" for unbuilt metros?**
a) Yes, greyed on homepage w/ waitlist-less "soon" tag ⭐  b) No, only live metros  c) Yes + email capture
→ A

**C13. Beyond the 9 — backlog cities chosen how?**
a) Demand signals (search/feed/analytics) ⭐  b) Ridership ranking  c) Manual
→ A

**C14. International later?**
a) Out of scope, note for v3 ⭐  b) Pick one (Toronto/London)  c) Never
→ A

---

## D · Homepage / city directory (D1–D16)

**D1. Homepage primary purpose?**
a) City directory — pick your metro ⭐  b) National rollup dashboard  c) Marketing/explainer  d) Directory + national stat band ⭐
→ D

**D2. Layout of the city picker?**
a) Map of US with pins + card grid ⭐  b) Card grid only  c) Searchable list  d) Map only
→ A

**D3. Live vs coming-soon cities shown how?**
a) Live = full card, soon = greyed w/ tag ⭐  b) Separate sections  c) Live only
→ A

**D4. Per-city card content?**
a) Name, agencies, 1 headline stat (e.g. access score), status ⭐  b) Name only  c) Name + thumbnail map
→ A

**D5. National stat band on homepage?**
a) Sum/avg across live metros (riders, $, access) ⭐  b) None  c) "N metros, M agencies tracked"
→ A

**D6. Geolocate to suggest nearest metro?**
a) Yes, soft suggestion, no redirect ⭐  b) Auto-redirect  c) No
→ A

**D7. Homepage search?**
a) Search metros + jump to in-metro search ⭐  b) Metro search only  c) None for v2
→ A

**D8. Hero treatment?**
a) Instrument-panel motif w/ national map ⭐  b) Big claim + CTA  c) Minimal wordmark + grid
→ A

**D9. Where does the methodology/about link live?**
a) Global footer + dedicated page ⭐  b) Homepage section  c) Per-metro
→ A

**D10. Homepage rendering?**
a) Static (SSG), islands for map ⭐  b) SSR  c) Client SPA
→ A

**D11. Cross-metro comparison entry point?**
a) "Compare metros" link → table page ⭐  b) On homepage inline  c) Defer to v3
→ A

**D12. Brand/logo placement carries from v1?**
a) Reuse MetroTrack logos, add national lockup ⭐  b) New homepage logo  c) Wordmark only
→ A; There should be a generic MetroTrack logo that is not city specific that we can use for the homepage.

**D13. Theme on homepage?**
a) Dark-native default + toggle (ship the v1-deferred toggle) ⭐  b) Dark only  c) Light
→ A

**D14. "What is MetroTrack" for first-time visitors?**
a) One-line subhead + link to About ⭐  b) Full explainer block  c) Modal on first visit
→ A + B

**D15. Homepage update cadence shown?**
a) "Data as of <date>" per metro on cards ⭐  b) Global "as of"  c) None
→ A

**D16. Empty-state when no metro selected?**
a) Directory IS the default state ⭐  b) Auto-pick Chicago  c) Geolocated default
→ A

---

## E · SEO (E1–E22)

**E1. SEO priority for v2?**
a) High — built-in from the start ⭐  b) Medium — basics only  c) Low — defer
→ A

**E2. Per-metro page titles?**
a) Templated "<Metro> transit funding, ridership & job access — MetroTrack" ⭐  b) Generic  c) Hand-written each
→ A

**E3. Meta descriptions?**
a) Templated per page type w/ live figures ⭐  b) Static per page  c) Auto from content
→ A

**E4. Sitemap?**
a) Auto-generated `sitemap.xml` (Astro integration) covering all metros+pages ⭐  b) Manual  c) None
→ A

**E5. Structured data (JSON-LD)?**
a) Dataset + Organization + BreadcrumbList ⭐  b) Organization only  c) None
→ A

**E6. `Dataset` schema for each pillar?**
a) Yes — funding/ridership/access as Dataset w/ source+date ⭐  b) No  c) Just one site-level Dataset
→ A

**E7. Open Graph / Twitter cards?**
a) Per-metro OG image (static or generated) ⭐  b) One global OG  c) None
→ A

**E8. OG image generation?**
a) Pre-rendered per metro at build (Satori/sharp) ⭐  b) Static hand-made  c) Live edge function
→ A

**E9. Canonical URLs?**
a) Self-canonical per page, strip query params ⭐  b) None  c) Canonical to metro root
→ A

**E10. Heading/semantic structure?**
a) Strict one-H1, sectioned, ARIA landmarks ⭐  b) Visual-only  c) Loose
→ A

**E11. Robots policy?**
a) Index everything public, disallow internal/api ⭐  b) Index all  c) Noindex non-Chicago until parity
→ A

**E12. Page speed / Core Web Vitals target?**
a) Lighthouse ≥90 mobile, enforce in CI (already have .lighthouserc) ⭐  b) Best-effort  c) Desktop only
→ A

**E13. Map/island and LCP?**
a) Static hero, defer map hydration (no LCP hit) ⭐  b) Map is hero, accept cost  c) Skeleton then hydrate
→ A

**E14. Internal linking?**
a) Cross-link metros + pillars + methodology ⭐  b) Nav only  c) Minimal
→ A

**E15. Per-metro landing copy for search intent?**
a) Short unique intro paragraph per metro/pillar ⭐  b) Templated identical  c) None
→ A

**E16. URL slugs?**
a) Stable kebab `/chicago/job-access` ⭐  b) Short `/chi/access`  c) IDs
→ A

**E17. Breadcrumbs (UI + schema)?**
a) Yes, Home › Metro › Pillar ⭐  b) Schema only  c) None
→ A

**E18. hreflang / i18n?**
a) en-US only, no hreflang ⭐  b) Add es-US later  c) Now
→ A

**E19. RSS discovery for SEO?**
a) `<link rel=alternate type=rss>` per metro ⭐  b) Footer link only  c) None
→ A

**E20. Analytics for SEO (privacy-friendly per CLAUDE.md)?**
a) Plausible/Umami, track search landings ⭐  b) None  c) GA4
→ A

**E21. 404 / soft-404 for unbuilt metros?**
a) Real 200 "coming soon" page, indexable ⭐  b) 404  c) Redirect home
→ A

**E22. Build a methodology/about hub for E-E-A-T?**
a) Yes — per-pillar methodology pages, sourced ⭐  b) One page  c) Footer only
→ A

---

## F · RSS / regional feeds (F1–F16)

**F1. What does the RSS feed publish?**
a) Notable changes per metro (funding updates, new data, access shifts) ⭐  b) Every nightly refresh  c) Editorial posts only
→ A

**F2. Feed granularity?**
a) One feed per metro ⭐  b) One global feed  c) Both global + per-metro ⭐  d) Per pillar per metro
→ C

**F3. Feed URL scheme?**
a) `/<metro>/feed.xml` + `/feed.xml` global ⭐  b) `/rss/<metro>`  c) Query param
→ B

**F4. Format?**
a) RSS 2.0 ⭐  b) Atom  c) Both  d) JSON Feed + RSS ⭐
→ A

**F5. What triggers a feed item?**
a) Detected delta over threshold (e.g. funding ±X%, vacancy change) ⭐  b) Any data change  c) Manual editorial
→ A

**F6. Item content?**
a) Headline + figure + source + "as of" + link ⭐  b) Headline + link  c) Full explainer
→ A

**F7. How are deltas computed?**
a) Diff gold snapshots night-over-night in a `feed_items` table ⭐  b) Git diff of JSON  c) Manual
→ A

**F8. Feed item persistence?**
a) `feed_items` table (metro_id, type, ts, payload), RLS public-read ⭐  b) Static files  c) Regenerate each build
→ A

**F9. Backfill on launch?**
a) Seed with "now tracking <metro>" items ⭐  b) Empty until first delta  c) Synthetic history
→ A

**F10. Region rollups (e.g. "Bay Area" = multi-agency)?**
a) Metro feed already = region ⭐  b) Separate region feeds  c) Agency-level feeds
→ A

**F11. Dedup / noise control?**
a) Threshold + daily max items per metro ⭐  b) None  c) Manual review
→ A

**F12. Feed generation timing?**
a) End of nightly transform, after gold reload ⭐  b) On deploy  c) Separate cron
→ A

**F13. Discoverability?**
a) `<link rel=alternate>` + footer + /feeds index page ⭐  b) Footer only  c) None
→ A

**F14. Email digest later?**
a) Out of scope v2, note for v3 ⭐  b) Add now (free tier)  c) Never
→ A

**F15. Item titles tone?**
a) Neutral factual ("CTA operating budget updated: $X, as of <date>") ⭐  b) Editorial  c) Terse
→ A

**F16. Feed item retention?**
a) Keep all, paginate ⭐  b) Last 90 days  c) Last 50 items
→ A

---

## G · New pages & information architecture (G1–G16)

**G1. New top-level pages in v2?**
a) Home, Compare, Methodology, Feeds, About ⭐  b) Just Home + Compare  c) Home only + per-metro
→ A

**G2. Per-metro page set?**
a) Overview, Map, Funding, Hiring, Job Access ⭐  b) One long scroll  c) Map + one stats page
→ A

**G3. Metro "overview" page?**
a) Yes — dashboard of all 4 pillars + feed ⭐  b) Redirect to map  c) No
→ A

**G4. Compare page scope?**
a) Table: metros × key metrics, sortable ⭐  b) Two-metro side-by-side  c) Charts only
→ A

**G5. Methodology pages?**
a) One per pillar, sourced (graduates DATA_SOURCES) ⭐  b) Single page  c) Inline tooltips only
→ A

**G6. About/colophon?**
a) Yes — mission, stack, attribution, neutrality stance ⭐  b) Footer only  c) No
→ A

**G7. Per-pillar deep pages vs sections?**
a) Dedicated pages (SEO + linkable) ⭐  b) Anchored sections on overview  c) Modal
→ A

**G8. Glossary / definitions page?**
a) Yes, links from tooltips ⭐  b) Inline only  c) No
→ A

**G9. Data downloads page?**
a) Yes — per-metro CSV/parquet export (portfolio + transparency) ⭐  b) No  c) API only
→ A

**G10. Embeddable widgets?**
a) Defer to v3 ⭐  b) One embeddable map  c) Now
→ A

**G11. Navigation pattern?**
a) Global top nav (metro switcher + pages) + footer ⭐  b) Sidebar  c) Footer-heavy
→ A

**G12. Metro switcher placement?**
a) Persistent in top nav ⭐  b) Homepage only  c) Breadcrumb
→ A

**G13. Status/changelog page?**
a) Public "what changed" tied to feed ⭐  b) None  c) Git-linked
→ A

**G14. 404 design?**
a) Branded, suggests metros ⭐  b) Default  c) Redirect
→ A

**G15. Search scope?**
a) Within-metro (stops/routes/places) + metro jump ⭐  b) Global only  c) None
→ A

**G16. Print/share affordances?**
a) Per-figure share links (deep-link state) ⭐  b) None  c) Screenshot button
→ A

---

## H · Data model & ETL scaling (H1–H20)

**H1. Pipeline parametrization?**
a) Every script takes `--metro=<slug>`, reads config ⭐  b) Per-metro forked scripts  c) Env switch
→ A

**H2. Bronze layout per metro?**
a) `data/bronze/<metro>/<source>/...` ⭐  b) `data/bronze/<source>/<metro>/...`  c) Flat w/ metro in filename
→ A

**H3. Keep committing bronze receipts at scale?**
a) Commit small/canonical, gitignore large GTFS (re-fetchable) ⭐  b) Commit all  c) Commit none, manifest only
→ A

**H4. Content-hash idempotency across metros?**
a) Hash per (metro, source) ⭐  b) Global hash  c) Keep current
→ A

**H5. dbt models multi-metro?**
a) Add `metro_id`, parametrize via dbt vars ⭐  b) Model per metro  c) Union per-metro seeds
→ A

**H6. GTFS schema variance handling?**
a) Normalize to canonical silver columns, tolerate missing ⭐  b) Per-agency parsers  c) Strict, fail on variance
→ A

**H7. LODES/ACS per metro?**
a) Fetch by state, filter to metro bbox/counties ⭐  b) National pull once  c) Per-county curated
→ A

**H8. Hex grid (H3) per metro?**
a) Generate from metro bbox at fixed res ⭐  b) Shared national grid, filter  c) Per-agency
→ A

**H9. H3 resolution?**
a) Keep v1 res, validate density for dense metros (NYC) ⭐  b) Per-metro res  c) Higher everywhere
→ A

**H10. Walkshed join scale fix (O(n²) flagged in v2-ideas)?**
a) H3 k-ring prefilter + spatial index before NYC ⭐  b) Accept, throttle  c) Self-host routing
→ A

**H11. Per-metro pipeline run orchestration?**
a) Matrix over metros in one Actions workflow ⭐  b) One workflow per metro  c) Sequential single job
→ A

**H12. Partial failure in a metro's nightly?**
a) Isolate — one metro fails, others proceed ⭐  b) Fail whole run  c) Retry then skip
→ A

**H13. Freshness-floor checks (carry-over)?**
a) Per metro per source, fail loud below floor ⭐  b) Global only  c) GTFS only (current)
→ A

**H14. Gold reload strategy?**
a) Upsert by (metro_id, key), no full truncate ⭐  b) Truncate+reload per metro  c) Full rebuild
→ A

**H15. Data versioning / "as of" provenance?**
a) `as_of` + `source_hash` columns on gold ⭐  b) Manifest file  c) Commit date
→ A

**H16. New DATA_SOURCES rows per metro?**
a) Required — every metro's feeds documented ⭐  b) Once per source type  c) Skip
→ A

**H17. Career-scrape (Playwright) at scale?**
a) Per-agency adapters, best-effort, weekly cron ⭐  b) Generic scraper  c) Drop for v2
→ A

**H18. Transit-leg access (r5py/OTP) scope?**
a) Spike on Chicago, then 1 metro, not all in v2 ⭐  b) All metros  c) Defer to v3
→ A

**H19. Schema migrations discipline?**
a) Numbered SQL migrations, RLS on every new table ⭐  b) MCP apply ad-hoc  c) dbt-managed
→ A

**H20. New-metro smoke test?**
a) `--metro=slug --dry-run` validates feeds+geo before full run ⭐  b) Run and inspect  c) None
→ A

---

## I · Storage, cost & free-tier budget (I1–I12)

**I1. Given DB ≈0.25 MB/metro, DB tier concern?**
a) Non-issue, stay free ⭐  b) Monitor at 50 metros  c) Plan paid now
→ A

**I2. Primary cost constraint to watch?**
a) ETL compute (Actions minutes) ⭐  b) ORS API quota  c) PMTiles bandwidth  d) All, set budgets ⭐
→ D

**I3. PMTiles hosting?**
a) Vercel static / object storage ⭐  b) Supabase Storage  c) R2 (Cloudflare free)
→ A

**I4. Tile size budget per metro?**
a) Cap, simplify geometry to hit it (validate NYC) ⭐  b) No cap  c) Per-zoom limits
→ A/C

**I5. Actions minutes budget?**
a) Stagger metros across nights to stay free ⭐  b) Parallel, accept cost  c) Self-hosted runner
→ A

**I6. ORS quota strategy?**
a) Cache isochrones, refresh monthly not nightly ⭐  b) Nightly  c) Self-host ORS
→ A

**I7. Bronze git bloat?**
a) gitignore large re-fetchable GTFS, keep manifest ⭐  b) Git LFS  c) Commit all
→ A

**I8. Cost monitoring?**
a) Lightweight budget doc + Actions usage check ⭐  b) None  c) Dashboard
→ A

**I9. Egress/bandwidth concern (Supabase 5 GB free)?**
a) Tiles off Supabase, so low risk ⭐  b) Monitor  c) CDN now
→ A

**I10. When to consider paid tier?**
a) Defined trigger (e.g. >5 GB egress or Actions cap) ⭐  b) Never in v2  c) Pre-emptively
→ A

**I11. Second Supabase project ("MetroTrack B") role?**
a) Staging/branch DB ⭐  b) Shard for scale  c) Decommission  d) Decide later
→ A

**I12. Data retention for time series (vacancies/funding/feed)?**
a) Keep all (tiny) ⭐  b) Rollup old to monthly  c) Cap
→ A

---

## J · Performance, tiles & maps (J1–J12)

**J1. One island for all maps or per-pillar?**
a) Shared MapLibre island, metro+layer props ⭐  b) Per-pillar islands  c) One big map
→ A

**J2. deck.gl layers per metro?**
a) Same layer code, data swapped by metro ⭐  b) Per-metro layer config  c) Static images for small metros
→ A

**J3. Tile generation in pipeline?**
a) tippecanoe per metro, output `<slug>.pmtiles` ⭐  b) One combined  c) On-demand
→ A

**J4. Lazy-load map?**
a) Hydrate on view/interaction ⭐  b) Eager  c) Static fallback then upgrade
→ A

**J5. Basemap?**
a) Self-styled minimal vector (no Mapbox bill) ⭐  b) Raster  c) Third-party free tiles
→ A

**J6. Mobile map perf?**
a) Reduce layers/zoom on small screens ⭐  b) Same everywhere  c) Static image on mobile
→ A

**J7. Chart island (ECharts) reuse?**
a) Generic chart island, data-driven ⭐  b) Per-chart  c) Server-rendered images
→ A

**J8. Color/legend consistency across metros?**
a) Shared scales from tokens ⭐  b) Per-metro auto-scale  c) Mixed
→ A

**J9. Access-overlay (walkshed) render cost on dense metros?**
a) Pre-simplified hex polygons in tiles ⭐  b) Client compute  c) Raster heatmap
→ A

**J10. Search index for stops/places per metro?**
a) Static JSON per metro, client fuzzy search ⭐  b) DB full-text  c) Server endpoint
→ A

**J11. Bundle budget per route?**
a) Set + enforce in CI ⭐  b) Best-effort  c) None
→ A

**J12. Prefetch on metro hover?**
a) Yes, prefetch metro route data ⭐  b) No  c) Only map tiles
→ A

---

## K · Autonomous loops & orchestration (K1–K22)

> The v2 ask: mostly-autonomous loops that run on one prompt — ideally spawning
> fresh auto-mode sessions / clean chats per unit. Must respect CLAUDE.md:
> "No loop without a hard verification gate."

**K1. What unit does one autonomous loop own?**
a) One metro end-to-end (config→pipeline→pages→QA→PR) ⭐  b) One pillar across metros  c) One task (v{p}.{s}.{t})  d) One segment
→ A

**K2. Loop driver?**
a) ralph-loop plugin (in your stack) ⭐  b) /loop skill (interval/self-paced)  c) schedule (cron cloud agents)  d) Custom prompt + ScheduleWakeup
→ A

**K3. "One prompt opens new clean sessions" — mechanism?**
a) Orchestrator spawns subagents per unit (fresh context) ⭐  b) Cron cloud agents, one per unit  c) Scripted `claude -p` headless per unit  d) Manual new chats
→ A

**K4. Per-unit isolation?**
a) git worktree per metro/unit ⭐  b) Branch only  c) Same workspace
→ A

**K5. The hard verification gate (non-negotiable) is…?**
a) Build + Lighthouse + data-integrity checks must pass to advance ⭐  b) Build only  c) Tests only  d) Human review only
→ A

**K6. Data-integrity gate specifics?**
a) Every figure traces to a source row + freshness floor met ⭐  b) Row counts >0  c) Schema valid
→ A

**K7. Who approves merge to phase branch?**
a) Auto-merge to `v2` if gates green, human for `main` ⭐  b) Human every merge  c) Full auto incl. main
→ A

**K8. Loop stop condition?**
a) All target metros at parity + gates green ⭐  b) Fixed iterations  c) Manual stop
→ A

**K9. Failure handling in a loop?**
a) Open a PR/issue with diagnosis, skip to next unit ⭐  b) Halt loop  c) Retry N then halt
→ A

**K10. State/progress tracking across sessions?**
a) A `docs/phases/v2/PROGRESS.md` ledger updated each unit ⭐  b) GitHub issues  c) Task tool only  d) DB table
→ A

**K11. How does a fresh session know what's next?**
a) Reads PROGRESS ledger + picks next pending metro ⭐  b) Cron assigns  c) Prompt hard-codes
→ A

**K12. Loop prompt lives where?**
a) `docs/phases/v2/LOOP_PROMPT.md` (the one prompt) ⭐  b) Skill  c) Inline
→ A

**K13. Verification before "done" claim?**
a) Run actual build+QA, paste evidence (per DoD) ⭐  b) Assert done  c) Spot-check
→ A

**K14. Auto-mode scope (which tools auto-approved)?**
a) Read/build/test/git auto; deploy+main gated ⭐  b) All auto  c) Nothing auto
→ A

**K15. Parallelism across metros?**
a) Bounded (2–3 worktrees) to respect API/Actions limits ⭐  b) All at once  c) Strictly serial
→ A

**K16. Cross-session context handoff?**
a) Ledger + per-metro plan files, no shared chat memory ⭐  b) Long single chat  c) Memory files
→ A

**K17. Cron-driven nightly autonomous QA?**
a) Scheduled agent runs QA, opens issues on regression ⭐  b) Manual  c) CI only
→ A

**K18. Guardrails on autonomous git?**
a) Never touch main; branch per unit; no force-push ⭐  b) Trust loop  c) Read-only, human commits
→ B

**K19. Cost ceiling per loop run?**
a) Bounded units + Actions/API budget check before spawn ⭐  b) Unbounded  c) Time-boxed
→ A

**K20. How is a loop kicked off?**
a) `/ralph-loop` (or one prompt) referencing LOOP_PROMPT.md ⭐  b) Cron only  c) Manual chat each time
→ A

**K21. Evidence/artifact each unit must leave?**
a) PR + screenshots + Lighthouse + integrity log ⭐  b) PR only  c) Commit msg
→ A

**K22. Human checkpoints?**
a) Per-metro PR review before next metro starts ⭐  b) End of phase only  c) None
→ A

---

## L · Modeling depth — v1 carry-overs (L1–L14)

**L1. Service-shortfall headline (UNDERSTAFFING_METRIC) in v2?**
a) Yes, Chicago first via GTFS-realtime vs scheduled ⭐  b) Defer  c) All metros
→ A

**L2. GTFS-realtime ingestion?**
a) Chicago only in v2, design for multi-metro ⭐  b) All metros  c) Skip
→ A

**L3. True ACCESS_SCORE (transit-leg, schedule-aware)?**
a) r5py/OTP spike Chicago + 1 metro ⭐  b) Keep walk-isochrone proxy  c) All metros
→ A

**L4. ACS equity overlay (access × income/race/vehicle)?**
a) Yes — the "who has access" story ⭐  b) Defer  c) Chicago only
→ A

**L5. Per-capita access normalization?**
a) Surface deficit per-capita, not raw ⭐  b) Raw counts  c) Both ⭐
→ A

**L6. Capital-project tracker (RTAMS-style)?**
a) Chicago pilot, generalize later ⭐  b) Defer to v3  c) All metros
→ A

**L7. Funding figures requiring primary sources?**
a) NTD baseline now, primary-source dig per metro later ⭐  b) Block on primary sources  c) NTD only forever
→ A

**L8. Forecasting (ridership/vacancy trend)?**
a) Simple trend/heuristic first, ML only if it beats it ⭐  b) ML now  c) None in v2
→ A

**L9. Cross-metro normalization for compare page?**
a) Per-capita + per-revenue-mile normalized metrics ⭐  b) Raw  c) Percentile ranks
→ A

**L10. Confidence/caveat surfacing?**
a) Per-metric caveat + method link (keep v1 rigor) ⭐  b) Footnote  c) None
→ A

**L11. Nightly wires funding/hiring/access (v1 gap)?**
a) Yes — regenerate, reload gold, redeploy ⭐  b) Keep committed JSON  c) Weekly
→ A

**L12. Equity overlay data cadence?**
a) ACS annual, cache ⭐  b) Nightly  c) Static
→ A

**L13. New metric → which doc?**
a) New `modeling/<METRIC>.md` + DATA_SOURCES rows ⭐  b) Inline  c) Skip
→ A

**L14. Headline metric per metro on cards?**
a) Job-access score (the signature) ⭐  b) Ridership  c) Funding  d) Per-metro choice
→ A

---

## M · Reliability, QA & monitoring (M1–M10)

**M1. Per-metro QA gate before publish?**
a) Automated checks + visual QA (gstack/browse) ⭐  b) Build only  c) Manual spot-check
→ A

**M2. Data-integrity tests?**
a) Row→source traceability + freshness floors in CI ⭐  b) Schema only  c) None
→ A

**M3. Sentry across metros?**
a) Tag errors by metro ⭐  b) Global  c) None
→ A

**M4. Visual regression?**
a) Lighthouse + screenshot diff key pages ⭐  b) Lighthouse only  c) None
→ A

**M5. Broken-link / sitemap check?**
a) CI crawl on PR ⭐  b) Manual  c) None
→ A

**M6. Nightly health canary?**
a) Post-deploy canary (gstack /canary) per metro ⭐  b) Manual  c) None
→ A

**M7. Alert on data staleness?**
a) Freshness floor breach → issue/alert ⭐  b) Silent  c) Log only
→ A

**M8. Accessibility?**
a) a11y checks in CI (keep v1 bar) ⭐  b) Manual  c) Skip
→ A

**M9. Rollback strategy?**
a) Revert PR + redeploy; gold upsert is reversible ⭐  b) Restore DB  c) None
→ A

**M10. Definition of Done for a metro?**
a) DEFINITION_OF_DONE + parity checklist, evidence attached ⭐  b) "It builds"  c) PR merged
→ A

---

_End — 200 questions. Mark answers inline after each `→`, then we graduate the
survivors into `docs/phases/v2/` (overview + per-segment plans), new ADRs
(multi-tenancy, RSS, autonomous-loop orchestration), and `design-system/` updates._
