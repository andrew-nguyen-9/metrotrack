"""GTFS static loader — CTA / Pace / Metra → content-hashed bronze parquet.

Downloads each authority's GTFS zip, extracts the tables we need (stops, routes,
trips, shapes) and lands them in bronze via the content-hashed ingest contract
(idempotent: unchanged bytes → no rewrite, see pipeline/bronze.py). Routes get
their geometry in silver by stitching `shapes` into lines; `trips` links
route_id ↔ shape_id.

A committed *sample* — a few routes per authority with their shapes, plus a head
of stops — keeps `dbt build` reproducible with no network. Refresh it with:

    python pipeline/gtfs.py --sample          # trimmed sample (committed)
    python pipeline/gtfs.py                    # full feeds (not committed)

The sample is route-coherent (sampled routes → their trips → their shapes) so the
map renders real geometry; stops are a head slice (decoupled from route sampling,
which would need stop_times — out of scope for the foundation).
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import urllib.parse
import zipfile

import requests

try:  # dual-mode: `python -m pipeline.gtfs` vs `python pipeline/gtfs.py`
    from . import bronze, cli
except ImportError:  # pragma: no cover
    import bronze
    import cli

GTFS_TABLES = ("stops", "routes", "trips", "shapes")
UA = {"User-Agent": "MetroTrack/1.0 (+https://transit.an9.dev)"}


# ── pure CSV helpers (no network — exercised by selftest) ───────────────
def _rows(data: bytes) -> tuple[list[str], list[list[str]]]:
    reader = csv.reader(io.StringIO(data.decode("utf-8-sig")))
    header = next(reader)
    return header, list(reader)


def _to_bytes(header: list[str], rows: list[list[str]]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def normalize_csv(data: bytes) -> bytes:
    """Strip whitespace from every header and cell.

    Some feeds (Metra) pad columns with leading spaces — ` shape_id`, ` 1` — which
    breaks column lookups and cross-table joins (trips.shape_id vs shapes.shape_id).
    Normalizing at ingest keeps bronze joinable and silver free of trim() noise.
    """
    header, rows = _rows(data)
    return _to_bytes([h.strip() for h in header], [[c.strip() for c in r] for r in rows])


def subset_routes(data: bytes, n: int) -> tuple[bytes, set[str]]:
    """First n routes *per route_type* + the set of their route_ids.

    Stratifying by route_type guarantees every mode a feed carries lands in the
    committed sample: CTA ships bus + rail ('L') in one feed and lists all bus
    routes before the eight rail lines, so a flat head slice would drop rail
    entirely. Feeds with no route_type column fall back to a flat first-n.
    """
    header, rows = _rows(data)
    idx = header.index("route_id")
    if "route_type" not in header:
        rows = rows[:n]
        return _to_bytes(header, rows), {r[idx] for r in rows}
    tidx = header.index("route_type")
    per_type: dict[str, int] = {}
    kept = []
    for r in rows:
        t = r[tidx]
        if per_type.get(t, 0) >= n:
            continue
        per_type[t] = per_type.get(t, 0) + 1
        kept.append(r)
    return _to_bytes(header, kept), {r[idx] for r in kept}


def subset_trips(data: bytes, route_ids: set[str],
                 max_shapes_per_route: int = 2) -> tuple[bytes, set[str], set[str]]:
    """Trips for the kept routes, capped to a few shapes per route.

    Returns (trips_bytes, shape_ids, trip_ids). We keep at most
    `max_shapes_per_route` distinct shapes per route (≈ the two directions) — that
    keeps a long-bus-route feed like CTA from exploding the committed sample. The
    kept trip_ids drive route-coherent stop sampling (see stop_ids_for_trips).
    Tolerates feeds whose trips.txt has no shape_id (keeps one trip per route).
    """
    header, rows = _rows(data)
    ridx = header.index("route_id")
    tid = header.index("trip_id") if "trip_id" in header else None
    trip_ids: set[str] = set()
    if "shape_id" not in header:
        seen: set[str] = set()
        kept = []
        for r in rows:
            if r[ridx] in route_ids and r[ridx] not in seen:
                seen.add(r[ridx])
                kept.append(r)
                if tid is not None:
                    trip_ids.add(r[tid])
        return _to_bytes(header, kept), set(), trip_ids

    sidx = header.index("shape_id")
    per_route: dict[str, set[str]] = {}
    kept = []
    shape_ids: set[str] = set()
    for r in rows:
        rid, sh = r[ridx], r[sidx]
        if rid not in route_ids:
            continue
        bucket = per_route.setdefault(rid, set())
        if sh in bucket or len(bucket) >= max_shapes_per_route:
            continue
        bucket.add(sh)
        kept.append(r)
        if sh:
            shape_ids.add(sh)
        if tid is not None:
            trip_ids.add(r[tid])
    return _to_bytes(header, kept), shape_ids, trip_ids


def subset_shapes(data: bytes, shape_ids: set[str]) -> bytes:
    header, rows = _rows(data)
    sidx = header.index("shape_id")
    return _to_bytes(header, [r for r in rows if r[sidx] in shape_ids])


def stop_ids_for_trips(data: bytes, trip_ids: set[str]) -> set[str]:
    """stop_ids visited by the kept trips — the route-coherent stop set.

    stop_times.txt is the only GTFS link from a trip to its stops; we read it
    (streaming, never persisted — it is millions of rows) purely to select which
    stops the committed sample keeps. This pulls CTA's rail *stations* into the
    sample, not just the head-slice of bus stops. ids are stripped so a
    space-padded feed (Metra) still joins to the normalized trips.
    """
    if not trip_ids:
        return set()
    reader = csv.reader(io.StringIO(data.decode("utf-8-sig")))
    header = [h.strip() for h in next(reader)]
    tidx, sidx = header.index("trip_id"), header.index("stop_id")
    return {row[sidx].strip() for row in reader
            if row and row[tidx].strip() in trip_ids}


def subset_stops_by_id(data: bytes, stop_ids: set[str]) -> bytes:
    header, rows = _rows(data)
    idx = header.index("stop_id")
    return _to_bytes(header, [r for r in rows if r[idx] in stop_ids])


def subset_head(data: bytes, m: int) -> bytes:
    header, rows = _rows(data)
    return _to_bytes(header, rows[:m])


# ── network ─────────────────────────────────────────────────────────────
def discover_gtfs_url(page_url: str) -> str:
    """Scrape a GTFS.zip link off a feed page (rotating dated paths, e.g. Pace)."""
    html = requests.get(page_url, headers=UA, timeout=30).text
    m = re.search(r'href="([^"]*GTFS\.zip)"', html, re.I)
    if not m:
        raise RuntimeError(f"GTFS .zip link not found on {page_url}")
    return urllib.parse.urljoin(page_url, m.group(1))


def feed_url(agency) -> str:
    """Resolve one agency's GTFS zip URL from its metro config (static or discovered)."""
    if agency.gtfs_url:
        return agency.gtfs_url
    page = agency.raw.get("gtfs_discover_url")
    if not page:
        raise RuntimeError(f"agency {agency.id!r} has neither gtfs_url nor gtfs_discover_url")
    return discover_gtfs_url(page)


def fetch_zip(url: str) -> bytes:
    r = requests.get(url, headers=UA, timeout=180)
    r.raise_for_status()
    return r.content


def load_agency(metro, agency, *, sample: int | None = None) -> list[bronze.BronzeReceipt]:
    """Pull one agency's GTFS into per-metro bronze (source = agency id)."""
    zf = zipfile.ZipFile(io.BytesIO(fetch_zip(feed_url(agency))))
    names = set(zf.namelist())
    raw = {t: normalize_csv(zf.read(f"{t}.txt")) for t in GTFS_TABLES if f"{t}.txt" in names}

    if sample:
        routes_b, ids = subset_routes(raw["routes"], sample)
        if "trips" in raw:
            trips_b, shape_ids, trip_ids = subset_trips(raw["trips"], ids)
        else:
            trips_b, shape_ids, trip_ids = b"", set(), set()
        # Route-coherent stops: keep the stops the kept trips actually visit (via
        # stop_times, read straight off the zip and discarded). Falls back to a head
        # slice if the feed omits stop_times, so the sample is never stop-empty.
        stop_ids: set[str] = set()
        if trip_ids and "stop_times.txt" in names:
            stop_ids = stop_ids_for_trips(zf.read("stop_times.txt"), trip_ids)
        stops_b = subset_stops_by_id(raw["stops"], stop_ids) if stop_ids \
            else subset_head(raw["stops"], sample * 40)
        out = {
            "routes": routes_b,
            "trips": trips_b,
            "shapes": subset_shapes(raw["shapes"], shape_ids) if "shapes" in raw else b"",
            "stops": stops_b,
        }
    else:
        out = raw

    return [bronze.ingest_csv(agency.id, t, data, metro=metro.slug)
            for t, data in out.items() if data]


def dry_run(metro, *, check_network: bool = True) -> "cli.DryRunReport":
    """Validate geo/FIPS and probe each agency's GTFS feed without writing bronze. [H20a]"""
    report = cli.DryRunReport(metro.slug, "gtfs")
    for c in cli.geo_checks(metro):
        report.checks.append(c)
    for agency in metro.agencies:
        url = agency.gtfs_url or agency.raw.get("gtfs_discover_url", "")
        name = f"gtfs:{agency.id}"
        if not check_network:
            report.add(name, "pass" if url else "fail",
                       f"{'configured' if url else 'no url'} {url}")
        else:
            report.checks.append(cli.reach(name, url))
    return report


def main(argv: list[str] | None = None) -> int:
    ap = cli.add_metro_args(argparse.ArgumentParser(description=__doc__))
    ap.add_argument("--sample", type=int, nargs="?", const=12, default=None,
                    help="Trim to N routes/agency (default 12) for a committed sample.")
    ap.add_argument("--agency", help="Load just one agency id (default: all in the metro).")
    args = ap.parse_args(argv)

    metro = cli.resolve_metro(args.metro)

    if args.dry_run:
        report = dry_run(metro)
        print(report.render())
        return 0 if report.ok else 1

    agencies = [a for a in metro.agencies if a.id == args.agency] if args.agency else list(metro.agencies)
    if args.agency and not agencies:
        sys.exit(f"agency {args.agency!r} not in metro {metro.slug!r}")
    for a in agencies:
        receipts = load_agency(metro, a, sample=args.sample)
        for r in receipts:
            print(f"  ok  {metro.slug}/{a.id}/{r.table}: {r.rows} rows  ({r.sha256[:12]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
