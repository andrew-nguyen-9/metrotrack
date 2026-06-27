# Modeling: The Understaffing Metric

The hiring pillar's headline number. How we define "understaffed" decides what we
scrape, what the gold `vacancy_trend` table stores, and what the chart claims.
There are several valid definitions and they are NOT interchangeable — pick
deliberately and write it down here.

## Why this is a real choice

| Definition | Formula (sketch) | Needs | Honest about |
|---|---|---|---|
| **Posting-based vacancy rate** | `open_reqs / budgeted_headcount` | scrape open reqs + a budgeted-headcount source | hiring *intent*, not actual gaps |
| **Filled-vs-budgeted gap** | `(budgeted − filled) / budgeted` | actual filled headcount (often FOIA/board docs, not scrapeable) | the *true* gap, but data is slow/sparse |
| **Service-shortfall proxy** | `(scheduled − delivered) service-hours` | GTFS scheduled vs. realtime delivered | rider-felt impact, but conflates staffing with other causes |

The laziest scrapeable option is posting-based; the most truthful is filled-vs-
budgeted; the most rider-relevant is the service-shortfall proxy. They can coexist
(show one headline, others as context) but the headline must be one clear thing.

## Decision — Service-shortfall proxy (DECIDED 2026-06-26)

The headline is the **rider-felt** definition: staffing shortage shows up as
service the authority *scheduled but didn't deliver*. It's the most honest about
impact and — crucially — it's measurable on free tiers from GTFS we already ingest,
without FOIA-ing headcount.

```
Headline metric:  Service Delivery Shortfall
Formula:          shortfall% = (scheduled_trips − delivered_trips) / scheduled_trips
                  over a period, per authority (and per route family where data allows)
Source:           GTFS static (scheduled) vs GTFS-realtime / published "delivered
                  service" reports (delivered). Both already in DATA_SOURCES.md.
Unit:             percentage (comparable across authorities) + absolute trips/hours lost
Granularity:      authority-wide headline; route-level + mode (bus/rail) drill-down
Snapshot row:     {authority, period_start, period_end, mode, scheduled, delivered,
                   shortfall_pct, source, as_of}  — append-only weekly
Caveat shown:     "Shortfall reflects service NOT delivered for ANY reason (staffing,
                   maintenance, weather), not staffing alone. We attribute it to
                   staffing only where the authority states a labor cause."
```

### Why this over the alternatives
- **Honest + obtainable:** derived from feeds we already pull; no scraping budgeted
  vs filled headcount (slow, sparse, FOIA-bound).
- **Rider-relevant:** measures what people experience, which is the site's point.

### The known weakness — and how we handle it
Service shortfall conflates staffing with maintenance/weather/other causes. So:
- **Don't claim it IS understaffing.** Label it "service delivered vs scheduled."
- **Corroborate** with the lighter **posting-based vacancy rate** (`open_reqs /
  budgeted_headcount`) as a *secondary* series scraped weekly — when shortfall and
  vacancy postings rise together, the staffing story is credible. This is the v1.3
  scrape target; it is context, not the headline.

This drives the `v1.3` plan, the `db/` `service_shortfall` + `vacancy_postings`
tables, and the chart copy. The scrape still feeds the secondary vacancy series.
