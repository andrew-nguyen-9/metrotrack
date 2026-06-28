# Hiring — primary-source receipts + methodology

`postings.csv` is the append-only weekly snapshot log of **open job postings** per
service board. Each row is one authority on one date; the cron appends a new dated
row each week. Every count is taken from the authority's own public job listing and
the rendered listing is saved under `samples/` as the receipt.

## Per-authority source + count methodology (accessed 2026-06-27)

| Authority | Source (ATS) | Count method | Seed (2026-06-27) | Receipt |
|---|---|---|---|---|
| CTA | Taleo — `chicagotransit.taleo.net/careersection/ex/jobsearch.ftl` | the listing's printed total: "Job Openings 1 – 13 of **13**" | 13 | `samples/cta_taleo.txt` |
| Metra | Cadient — `cta.cadienttalent.com` (`MetraKTMDReqExt`, All Open Jobs) | count of distinct job-detail postings (generic "Apply Now" link excluded) | 21 | `samples/metra_cadient_titles.txt` |
| Pace | Oracle Recruiting Cloud — `iaymqy.fa.ocs.oraclecloud.com` (`CX_1`) | the JSON API's `TotalJobsCount` | 57 | `samples/pace_oracle.json` |

Methodology differs per source because each ATS exposes a different reliable signal
(Taleo prints a total; Oracle's REST API returns one; Cadient lists requisitions).
The published figure is "open postings listed," **not** a vacancy rate or an
understaffing measure — see [`docs/modeling/UNDERSTAFFING_METRIC.md`](../../../docs/modeling/UNDERSTAFFING_METRIC.md).

## robots.txt / ToS

- CTA `transitchicago.com/robots.txt` allows `/careers/`; the Taleo host is a separate
  public candidate portal.
- Pace `pacebus.com/robots.txt` allows `/careers`; the Oracle CX site is the public
  candidate portal (public REST endpoint).
- Metra `metra.com` returns 403 to generic clients; recruiting is on the public Cadient
  portal. The scrape is polite (descriptive UA, weekly cadence, single request/source).
