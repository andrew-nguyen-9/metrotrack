"""Funding bronze loaders — operating budget vs. actual per service board.

Two sources feed the funding pillar (docs/architecture/DATA_SOURCES.md), and the
hard rule (CLAUDE.md) is that every figure traces to a committed primary-source
receipt:

  • **Actual** operating expense — FTA **National Transit Database**, "Annual Data
    View — Metrics (by Agency)" (DOT Socrata `g27i-aq2u`). Key-free, structured,
    multi-year → fully reproducible. `sum_total_operating_expenses`,
    `sum_fare_revenues_earned`, `sum_unlinked_passenger_trips` by agency × year.
    CTA (ntd_id 50066), Metra (50118), Pace Suburban Bus (50113) + Regional ADA
    Paratransit (50182). Pace operates ADA paratransit, so both fold into `pace`.

  • **Budget / plan** — RTA **Adopted 2025 Operating Budget**, Table 2 "Statement of
    Regional Revenues and Expenses" (the primary-source PDF is committed beside the
    transcription; see data/bronze/rta/SOURCE.md). PDF-only — no structured export —
    so the figures are transcribed into data/bronze/rta/budget_source.csv and
    reconciled against the document's own "Total Service Board Expenses" line.

The pure `parse_*` functions trim/normalize each source to the columns silver needs,
returning clean CSV bytes; `bronze.ingest_csv` content-hashes them to parquet
(idempotent, the receipt). `fetch_ntd` does the network I/O and stays out of the
no-network selftest. See docs/phases/v1/v1.2/PLAN.md.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import urllib.parse
import urllib.request

try:  # dual-mode: `python -m pipeline.funding` vs `python pipeline/funding.py`
    from . import bronze, cli
except ImportError:  # pragma: no cover
    import bronze
    import cli

# Default NTD reporter id → authority map (Chicago). Pace runs Regional ADA
# Paratransit, so its two NTD reports fold into one `pace` line (matches the RTA
# budget treatment). The pipeline path derives this from metros/<slug>.toml agencies;
# the default keeps the no-network parse selftest self-contained.
NTD_AUTHORITY = {
    "50066": "cta",
    "50118": "metra",
    "50113": "pace",
    "50182": "pace",
}
NTD_DATASET = "g27i-aq2u"
NTD_URL = f"https://data.transportation.gov/resource/{NTD_DATASET}.json"


def ntd_authority_map(metro) -> dict[str, str]:
    """Build {ntd_id: authority_id} from a metro's agencies (multiple ids fold in)."""
    out: dict[str, str] = {}
    for a in metro.agencies:
        for nid in a.ntd_ids:
            out[str(nid)] = a.id
    return out


def budget_source(metro):
    """The transcribed RTA-style budget CSV under this metro's bronze."""
    return cli.bronze_dir(metro.slug, "rta") / "budget_source.csv"


# Adopted budget total per fiscal year ($ thousands), straight from Table 2's
# "Total Service Board Expenses" row — the reconciliation key that catches a
# transcription fat-finger in budget_source.csv.
RTA_BOARD_TOTALS = {
    2023: 3127419,
    2024: 3482722,
    2025: 3912051,
    2026: 4144418,
    2027: 4246242,
}
RTA_KINDS = {"actual", "estimate", "budget", "plan"}
# ADA Paratransit folds into Pace (Pace operates it).
RTA_FOLD = {"ada": "pace"}


def parse_ntd(raw_json: bytes, authority_map: dict[str, str] | None = None) -> bytes:
    """Socrata NTD records → `authority_id,fiscal_year,operating_expense,fare_revenue,unlinked_trips`.

    Keeps only the metro's service-board reporters (default: Chicago's), maps each to
    its authority, and sums multi-report authorities (e.g. Pace) per year. Missing
    numeric fields read as 0.
    """
    amap = NTD_AUTHORITY if authority_map is None else authority_map
    rows = json.loads(raw_json)
    agg: dict[tuple[str, int], list[int]] = {}
    for r in rows:
        ntd_id = str(r.get("ntd_id", "")).strip()
        auth = amap.get(ntd_id)
        if auth is None:
            continue
        year = int(str(r["report_year"]).strip())
        vals = agg.setdefault((auth, year), [0, 0, 0])
        vals[0] += _int(r.get("sum_total_operating_expenses"))
        vals[1] += _int(r.get("sum_fare_revenues_earned"))
        vals[2] += _int(r.get("sum_unlinked_passenger_trips"))

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["authority_id", "fiscal_year", "operating_expense", "fare_revenue", "unlinked_trips"])
    for (auth, year), v in sorted(agg.items()):
        w.writerow([auth, year, v[0], v[1], v[2]])
    return out.getvalue().encode()


def parse_rta_budget(raw_csv: bytes) -> bytes:
    """Transcribed RTA budget CSV → `authority_id,fiscal_year,kind,amount` (dollars).

    Input columns: `authority_id,fiscal_year,kind,amount_thousands`. Folds ADA into
    Pace, converts thousands → dollars, validates `kind`, and reconciles each year's
    service-board sum against Table 2's printed total (±2 thousand for rounding).
    """
    reader = csv.DictReader(io.StringIO(raw_csv.decode("utf-8-sig")))
    agg: dict[tuple[str, int, str], int] = {}
    year_totals: dict[int, int] = {}
    for row in reader:
        kind = row["kind"].strip().lower()
        if kind not in RTA_KINDS:
            raise ValueError(f"unknown budget kind {kind!r}")
        raw_auth = row["authority_id"].strip().lower()
        auth = RTA_FOLD.get(raw_auth, raw_auth)
        year = int(row["fiscal_year"].strip())
        thousands = int(row["amount_thousands"].strip())
        agg[(auth, year, kind)] = agg.get((auth, year, kind), 0) + thousands
        year_totals[year] = year_totals.get(year, 0) + thousands

    for year, expected in RTA_BOARD_TOTALS.items():
        got = year_totals.get(year)
        if got is None:
            continue
        if abs(got - expected) > 2:
            raise ValueError(
                f"FY{year} transcription off: rows sum to {got}k, Table 2 says {expected}k"
            )

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["authority_id", "fiscal_year", "kind", "amount"])
    for (auth, year, kind), thousands in sorted(agg.items()):
        w.writerow([auth, year, kind, thousands * 1000])
    return out.getvalue().encode()


def _int(v) -> int:
    """Socrata sends numbers as strings; tolerate blanks/None/decimals."""
    if v is None or v == "":
        return 0
    return round(float(v))


def fetch_ntd(ntd_ids) -> bytes:
    ids = ",".join(f"'{i}'" for i in ntd_ids)
    query = urllib.parse.urlencode({
        "$select": "ntd_id,report_year,sum_total_operating_expenses,"
                   "sum_fare_revenues_earned,sum_unlinked_passenger_trips",
        "$where": f"ntd_id in ({ids})",
        "$limit": "5000",
    })
    with urllib.request.urlopen(f"{NTD_URL}?{query}", timeout=120) as r:
        return r.read()


def dry_run(metro, *, check_network: bool = True) -> "cli.DryRunReport":
    """Validate geo/FIPS, probe NTD, and confirm the budget transcription is present. [H20a]"""
    report = cli.DryRunReport(metro.slug, "funding")
    for c in cli.geo_checks(metro):
        report.checks.append(c)
    report.checks.append(cli.reach("ntd", NTD_URL) if check_network
                         else cli.Check("ntd", "pass", NTD_URL))
    src = budget_source(metro)
    report.add("budget_source", "pass" if src.exists() else "fail",
               src.as_posix() if src.exists() else f"missing {src.as_posix()}")
    return report


def ingest(metro) -> int:
    """Fetch NTD actuals + read the transcribed budget → per-metro content-hashed bronze."""
    amap = ntd_authority_map(metro)
    if not amap:
        sys.exit(f"{metro.slug}: no NTD ids configured on any agency")
    ntd = bronze.ingest_csv("ntd", "operating",
                            parse_ntd(fetch_ntd(amap), amap), metro=metro.slug)
    budget = bronze.ingest_csv("rta", "budget",
                               parse_rta_budget(budget_source(metro).read_bytes()),
                               metro=metro.slug)
    print(f"  ok  {metro.slug}/ntd/operating.parquet ({ntd.rows} agency-years)")
    print(f"  ok  {metro.slug}/rta/budget.parquet ({budget.rows} board-year-kind rows)")
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
