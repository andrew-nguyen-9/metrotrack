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
