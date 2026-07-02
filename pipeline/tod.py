"""TOD — central-business-district anchors → bronze. [v3.10]

The transit-oriented-development pillar measures each hex's straight-line time to
its nearest **central business district**. CBDs are declared per metro in
`metros/<slug>.toml` `[[cbd]]` blocks (data-driven + multi-district: adding a
district is config, not code). This module mirrors that authored list into a
content-hashed bronze table so dbt reads it the same way it reads every other
source (`read_parquet`), keeping the CBD set a single source of truth.

The pure `cbds_csv` is selftested no-network; `ingest` writes the bronze receipt.
Run:  python pipeline/tod.py --metro chicago
"""
from __future__ import annotations

import argparse
import csv
import io
import sys

try:  # dual-mode: `python -m pipeline.tod` vs `python pipeline/tod.py`
    from . import bronze, cli
except ImportError:  # pragma: no cover
    import bronze
    import cli


def cbds_csv(metro) -> bytes:
    """A metro's `[[cbd]]` list → `cbd_id,name,lat,lon` CSV bytes (sorted by id).

    Pure: no network, no disk. Raises if the metro declares no CBD (the TOD metric
    has no anchor without one — fail loud rather than emit an empty table).
    """
    if not metro.cbds:
        raise ValueError(f"{metro.slug}: no [[cbd]] declared — TOD time-to-CBD needs ≥1 anchor")
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["cbd_id", "name", "lat", "lon"])
    for c in sorted(metro.cbds, key=lambda x: x.id):
        w.writerow([c.id, c.name, f"{c.lat:.6f}", f"{c.lon:.6f}"])
    return out.getvalue().encode()


def ingest(metro) -> int:
    """Write the metro's CBD anchors to per-metro bronze (idempotent, content-hashed)."""
    receipt = bronze.ingest_csv("tod", "cbds", cbds_csv(metro), metro=metro.slug)
    print(f"  ok  {metro.slug}/tod/cbds.parquet ({receipt.rows} CBD anchor(s))")
    return 0


def dry_run(metro) -> "cli.DryRunReport":
    """Validate geo/FIPS + confirm the metro declares a parseable CBD set (no network)."""
    report = cli.DryRunReport(metro.slug, "tod")
    for c in cli.geo_checks(metro):
        report.checks.append(c)
    try:
        n = len(cbds_csv(metro).splitlines()) - 1  # minus header
        report.add("cbd anchors", "pass", f"{n} CBD(s) declared in metros/{metro.slug}.toml")
    except ValueError as e:
        report.add("cbd anchors", "fail", str(e))
    return report


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
