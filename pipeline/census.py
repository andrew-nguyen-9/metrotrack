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

import csv
import gzip
import io
import sys
import urllib.request

import bronze

# Latest stable LODES8 vintage; bump when Census publishes a newer year.
LODES_YEAR = 2022
LODES_URL = (
    "https://lehd.ces.census.gov/data/lodes/LODES8/il/wac/"
    f"il_wac_S000_JT00_{LODES_YEAR}.csv.gz"
)
CENPOP_URL = (
    "https://www2.census.gov/geo/docs/reference/cenpop2020/blkgrp/"
    "CenPop2020_Mean_BG17.txt"
)

# Cook County, Illinois — state FIPS 17, county FIPS 031.
COOK_STATE = "17"
COOK_COUNTY = "031"
COOK_PREFIX = COOK_STATE + COOK_COUNTY  # "17031" — first 5 of a block/bg GEOID


def parse_lodes_wac(raw_csv: bytes) -> bytes:
    """Trim raw LODES WAC → `w_geocode,bg_geoid,jobs` for Cook County only.

    bg_geoid is the block-group GEOID (first 12 of the 15-digit block GEOID),
    the key that joins to the Centers-of-Population centroids.
    """
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
        if geocode[:5] != COOK_PREFIX:
            continue
        w.writerow([geocode, geocode[:12], row[ci].strip()])
    return out.getvalue().encode()


def parse_cenpop_bg(raw: bytes) -> bytes:
    """Trim raw Centers-of-Population BG → `bg_geoid,population,lat,lon` for Cook.

    bg_geoid = STATEFP+COUNTYFP+TRACTCE+BLKGRPCE (2+3+6+1 = 12). The source file
    has a UTF-8 BOM and `+`-prefixed coordinates; both are normalized here.
    """
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
        if st != COOK_STATE or co != COOK_COUNTY:
            continue
        bg = st + co + row[idx["TRACTCE"]].strip() + row[idx["BLKGRPCE"]].strip()
        lat = row[idx["LATITUDE"]].strip().lstrip("+")
        lon = row[idx["LONGITUDE"]].strip().lstrip("+")
        w.writerow([bg, row[idx["POPULATION"]].strip(), lat, lon])
    return out.getvalue().encode()


def fetch_lodes() -> bytes:
    with urllib.request.urlopen(LODES_URL, timeout=120) as r:
        return gzip.decompress(r.read())


def fetch_cenpop() -> bytes:
    with urllib.request.urlopen(CENPOP_URL, timeout=120) as r:
        return r.read()


def ingest() -> int:
    """Fetch both sources, trim to Cook County, write content-hashed bronze."""
    lodes = bronze.ingest_csv("census", "lodes_wac", parse_lodes_wac(fetch_lodes()))
    cenpop = bronze.ingest_csv("census", "cenpop_bg", parse_cenpop_bg(fetch_cenpop()))
    print(f"  ok  census/lodes_wac.parquet ({lodes.rows} Cook blocks)")
    print(f"  ok  census/cenpop_bg.parquet ({cenpop.rows} Cook block groups)")
    return 0


if __name__ == "__main__":
    sys.exit(ingest())
