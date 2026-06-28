# Metro config contract (`metros/<slug>.toml`)

**Adding a metro = author one of these files + one `--metro=<slug>` pipeline run**
`[B13a]`. This file is the authored source of truth; `sync_metros()` mirrors the
serving subset into `public.metros`. Validated by `pipeline/metros.py` (loud on a
bad config) and exercised by `pipeline/selftest.py`. See
[`docs/phases/v2/v2.0/PLAN.md`](../docs/phases/v2/v2.0/PLAN.md).

## Top-level keys

| Key | Type | Req | Meaning |
|-----|------|-----|---------|
| `slug` | string | ✅ | Short stable kebab id. **= `metro_id`, the URL path, the filename stem.** `^[a-z0-9]+(-[a-z0-9]+)*$` `[E16a]` |
| `name` | string | ✅ | Display name (e.g. `Chicago`). |
| `region` | string | — | The whole metro region (e.g. `Chicagoland`, `Bay Area`) `[B16a]`. |
| `tz` | string | ✅ | IANA tz (e.g. `America/Chicago`). Store UTC, render here `[B15a]`. |
| `status` | string | ✅ | `live` or `soon`. `soon` = greyed "coming soon" `[C12a]`. |
| `bbox` | float[4] | ✅ | `[minLon, minLat, maxLon, maxLat]` WGS84. Map viewport + `metros.bbox` envelope. Must be `minLon < maxLon`, `minLat < maxLat`, within world range. |

## `[census]`

| Key | Type | Req | Meaning |
|-----|------|-----|---------|
| `state_fips` | string | ✅ | 2-digit state FIPS. |
| `county_fips` | string[] | ✅ | County FIPS (3-digit) in scope. |
| `lodes_state` | string | ✅ | LEHD LODES8 state slug (e.g. `il`). |
| `lodes_year` | int | ✅ | LODES8 vintage. |

## `[[agencies]]` (one or more)

| Key | Type | Req | Meaning |
|-----|------|-----|---------|
| `id` | string | ✅ | Authority code, unique within the metro (`cta`, `metra`, `pace`). |
| `name` | string | ✅ | Display name. |
| `mode` | string | ✅ | `bus` \| `rail` \| `multi`. |
| `url` | string | ✅ | Agency homepage. |
| `gtfs_url` | string | ✅ | GTFS-static zip. `""` if discovered — see `gtfs_discover_url`. |
| `gtfs_discover_url` | string | — | Page to scrape the GTFS link from (rotating dated paths, e.g. Pace). |
| `ntd_ids` | string[] | — | FTA NTD reporter ids; multiple fold into one authority. |
| `hiring` | table | — | `{ method, url }`. `method`: `taleo` \| `cadient` \| `oracle`. |
| `license` | string | — | GTFS license / terms (or a `DATA_SOURCES.md` reference). Optional. |

## Invariants enforced by `metros.py`

- `slug` matches the kebab pattern **and** equals the filename stem.
- `status` ∈ {`live`, `soon`}.
- `bbox` is 4 numbers, non-degenerate, within `[-180,180]×[-90,90]`.
- ≥ 1 agency; each `mode` ∈ {`bus`, `rail`, `multi`}.
- `tz`, `name`, `census.state_fips`, `census.lodes_state` non-empty.
