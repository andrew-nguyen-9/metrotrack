"""Census bronze loaders — jobs (LODES) + population (Centers of Population).

Two key-free Census sources feed the v1.1 mapping overlay (docs/architecture/
DATA_SOURCES.md):

  • LEHD **LODES8** WAC (`S000 JT00`) — block-level jobs at the *workplace*.
    `w_geocode` is the 15-digit block GEOID; `C000` is total jobs.
  • 2020 **Centers of Population** (block-group) — one file carries block-group
    `POPULATION` *and* its centroid lat/lng, so binning needs no TIGER/ACS key.

The pure `parse_*` functions trim each source to Cook County and to the columns
silver needs, returning clean CSV bytes; `bronze.ingest_csv` then content-hashes
them to parquet (idempotent, the reproducibility receipt). `fetch_*` does the
network I/O and stays out of the no-network selftest. See docs/phases/v1/v1.1/PLAN.md.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import sys
import urllib.request

try:  # dual-mode: `python -m pipeline.census` vs `python pipeline/census.py`
    from . import bronze, cli
except ImportError:  # pragma: no cover
    import bronze
    import cli

# Default scope = Cook County, Illinois (state FIPS 17, county FIPS 031). The
# pipeline path overrides these from metros/<slug>.toml [census]; the defaults only
# keep the no-network parse selftest (which feeds Cook fixtures) self-contained.
COOK_STATE = "17"
COOK_COUNTY = "031"
LODES_DEFAULT_YEAR = 2022

# ACS 5-year change (v3.9). The Census *Data API* now requires a key; the
# **table-based Summary File** is the equivalent key-free source — one pipe-delimited
# `.dat` per detail table, carrying every geography (nation → block group). We keep
# the tract (summary level 140) + county (050) rows for the in-scope counties. Two
# vintages that share the same census-tract geography give a valid per-tract change;
# 2021 & 2023 both sit on 2020 tracts (100% GEOID overlap for Cook). Line 001 is the
# table total (population / median household income). See docs/architecture/DATA_SOURCES.md.
ACS_DEFAULT_YEARS = (2021, 2023)
ACS_TABLES = {"population": "b01003", "median_income": "b19013"}  # both: _E001 = total


def acs_sf_url(year: int, table: str) -> str:
    """Key-free ACS 5-year table-based Summary File `.dat` for one detail table."""
    return (
        f"https://www2.census.gov/programs-surveys/acs/summary_file/{year}/"
        f"table-based-SF/data/5YRData/acsdt5y{year}-{table}.dat"
    )


def parse_acs_table(raw: bytes, state_fips: str = COOK_STATE,
                    county_fips: tuple[str, ...] = (COOK_COUNTY,)) -> dict[str, tuple[str, str]]:
    """Trim a table-based SF `.dat` → `{geoid: (geo_level, estimate)}` for the in-scope counties.

    Pipe-delimited; header is `GEO_ID|<TABLE>_E001|<TABLE>_M001|…`. We read the
    estimate column *by name* (ends `_E001`), not by position. Keeps tract rows
    (`1400000US<state><county><tract>`, geoid = 11-digit state+county+tract) and the
    county rollup (`0500000US<state><county>`, geoid = 5-digit state+county).
    """
    tract_prefixes = tuple("1400000US" + state_fips + c for c in county_fips)
    county_ids = {"0500000US" + state_fips + c: state_fips + c for c in county_fips}
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig")), delimiter="|")
    header = [c.strip() for c in next(reader)]
    est = next(i for i, c in enumerate(header) if c.endswith("_E001"))

    out: dict[str, tuple[str, str]] = {}
    for row in reader:
        if not row:
            continue
        gid = row[0].strip()
        if gid in county_ids:
            out[county_ids[gid]] = ("county", row[est].strip())
        elif gid.startswith(tract_prefixes):
            out[gid[9:]] = ("tract", row[est].strip())
    return out


def build_acs_rows(population: dict[str, tuple[str, str]],
                   income: dict[str, tuple[str, str]]) -> bytes:
    """Merge the population + median-income maps → `geoid,geo_level,population,median_income` CSV."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["geoid", "geo_level", "population", "median_income"])
    for geoid in sorted(population):
        level, pop = population[geoid]
        inc = income.get(geoid, ("", ""))[1]
        w.writerow([geoid, level, pop, inc])
    return out.getvalue().encode()


def fetch_acs(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": cli.UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def lodes_url(state: str, year: int) -> str:
    """LEHD LODES8 WAC (`S000 JT00`) workplace-jobs file for a state + vintage."""
    return (
        f"https://lehd.ces.census.gov/data/lodes/LODES8/{state}/wac/"
        f"{state}_wac_S000_JT00_{year}.csv.gz"
    )


def cenpop_url(state_fips: str) -> str:
    """2020 Centers of Population (block-group) file for a state FIPS."""
    return (
        "https://www2.census.gov/geo/docs/reference/cenpop2020/blkgrp/"
        f"CenPop2020_Mean_BG{state_fips}.txt"
    )


def parse_lodes_wac(raw_csv: bytes, state_fips: str = COOK_STATE,
                    county_fips: tuple[str, ...] = (COOK_COUNTY,)) -> bytes:
    """Trim raw LODES WAC → `w_geocode,bg_geoid,jobs` for the in-scope counties.

    bg_geoid is the block-group GEOID (first 12 of the 15-digit block GEOID),
    the key that joins to the Centers-of-Population centroids.
    """
    prefixes = tuple(state_fips + c for c in county_fips)  # 5-digit county GEOID prefix
    reader = csv.reader(io.StringIO(raw_csv.decode("utf-8-sig")))
    header = [c.strip() for c in next(reader)]
    gi, ci = header.index("w_geocode"), header.index("C000")

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["w_geocode", "bg_geoid", "jobs"])
    for row in reader:
        if not row:
            continue
        geocode = row[gi].strip()
        if geocode[:5] not in prefixes:
            continue
        w.writerow([geocode, geocode[:12], row[ci].strip()])
    return out.getvalue().encode()


def parse_cenpop_bg(raw: bytes, state_fips: str = COOK_STATE,
                    county_fips: tuple[str, ...] = (COOK_COUNTY,)) -> bytes:
    """Trim raw Centers-of-Population BG → `bg_geoid,population,lat,lon` for the counties.

    bg_geoid = STATEFP+COUNTYFP+TRACTCE+BLKGRPCE (2+3+6+1 = 12). The source file
    has a UTF-8 BOM and `+`-prefixed coordinates; both are normalized here.
    """
    counties = set(county_fips)
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig")))
    header = [c.strip() for c in next(reader)]
    idx = {name: header.index(name) for name in
           ("STATEFP", "COUNTYFP", "TRACTCE", "BLKGRPCE", "POPULATION", "LATITUDE", "LONGITUDE")}

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["bg_geoid", "population", "lat", "lon"])
    for row in reader:
        if not row:
            continue
        st, co = row[idx["STATEFP"]].strip(), row[idx["COUNTYFP"]].strip()
        if st != state_fips or co not in counties:
            continue
        bg = st + co + row[idx["TRACTCE"]].strip() + row[idx["BLKGRPCE"]].strip()
        lat = row[idx["LATITUDE"]].strip().lstrip("+")
        lon = row[idx["LONGITUDE"]].strip().lstrip("+")
        w.writerow([bg, row[idx["POPULATION"]].strip(), lat, lon])
    return out.getvalue().encode()


def _census_cfg(metro) -> tuple[str, tuple[str, ...], str, int]:
    """(state_fips, county_fips, lodes_state, lodes_year) from a metro's [census]."""
    c = metro.raw.get("census") or {}
    return (
        str(c["state_fips"]),
        tuple(str(x) for x in c["county_fips"]),
        str(c["lodes_state"]),
        int(c.get("lodes_year", LODES_DEFAULT_YEAR)),
    )


def _acs_years(metro) -> tuple[int, ...]:
    """The ACS 5-year vintages to pull for change-over-time (≥2). From [census].acs_years."""
    c = metro.raw.get("census") or {}
    return tuple(int(y) for y in c.get("acs_years", ACS_DEFAULT_YEARS))


def fetch_lodes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as r:
        return gzip.decompress(r.read())


def fetch_cenpop(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def dry_run(metro, *, check_network: bool = True) -> "cli.DryRunReport":
    """Validate geo/FIPS and probe the LODES + Centers-of-Population URLs. [H20a]"""
    report = cli.DryRunReport(metro.slug, "census")
    for c in cli.geo_checks(metro):
        report.checks.append(c)
    state, _counties, lstate, lyear = _census_cfg(metro)
    urls = {"lodes_wac": lodes_url(lstate, lyear), "cenpop_bg": cenpop_url(state)}
    for y in _acs_years(metro):
        urls[f"acs_pop_{y}"] = acs_sf_url(y, ACS_TABLES["population"])
    for name, url in urls.items():
        report.checks.append(cli.reach(name, url) if check_network
                             else cli.Check(name, "pass", url))
    return report


def ingest(metro) -> int:
    """Fetch both sources, trim to the metro's counties, write per-metro bronze."""
    state, counties, lstate, lyear = _census_cfg(metro)
    lodes = bronze.ingest_csv(
        "census", "lodes_wac",
        parse_lodes_wac(fetch_lodes(lodes_url(lstate, lyear)), state, counties),
        metro=metro.slug,
    )
    cenpop = bronze.ingest_csv(
        "census", "cenpop_bg",
        parse_cenpop_bg(fetch_cenpop(cenpop_url(state)), state, counties),
        metro=metro.slug,
    )
    print(f"  ok  {metro.slug}/census/lodes_wac.parquet ({lodes.rows} blocks)")
    print(f"  ok  {metro.slug}/census/cenpop_bg.parquet ({cenpop.rows} block groups)")

    # ACS 5-year change vintages (v3.9): one bronze table per year, tract + county rows.
    for year in _acs_years(metro):
        pop = parse_acs_table(fetch_acs(acs_sf_url(year, ACS_TABLES["population"])), state, counties)
        inc = parse_acs_table(fetch_acs(acs_sf_url(year, ACS_TABLES["median_income"])), state, counties)
        r = bronze.ingest_csv("census", f"acs_{year}", build_acs_rows(pop, inc), metro=metro.slug)
        print(f"  ok  {metro.slug}/census/acs_{year}.parquet ({r.rows} tract+county rows)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = cli.add_metro_args(argparse.ArgumentParser(description=__doc__))
    args = ap.parse_args(argv)
    metro = cli.resolve_metro(args.metro)
    if args.dry_run:
        report = dry_run(metro)
        print(report.render())
        return 0 if report.ok else 1
    return ingest(metro)


if __name__ == "__main__":
    sys.exit(main())
