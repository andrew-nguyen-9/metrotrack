"""Data-integrity gate — `verify_metro(slug)`: no published figure without a source. [K6a]

The loop's reusable proof that a metro's pages are honest. A "published figure" is
whatever the frontend renders, and for this SSG site that means the per-metro gold
exports (`frontend/src/data/<slug>/*.json` + the PMTiles), built from the dbt gold
warehouse. So the chain we verify is:

    bronze receipt (content-hashed source)  →  gold row (metro_id)  →  exported figure

`verify_metro` walks that chain backwards: every gold pillar that has rows for the
metro must trace to a bronze receipt for one of its feeding sources, every configured
agency must have actually ingested something, no gold row may carry a null `metro_id`,
and the freshness floor must hold (a GTFS feed going dark fails loud, [H13a]).

A pillar with *no* rows is **degraded, not failed** — a metro may legitimately lack a
source and the UI hides that pillar `[A7a]`. Only a figure shown *without* provenance,
a dark feed, or a null tenant key is a hard fail.

No network: reads the local DuckDB + the bronze manifest, so `pipeline/selftest.py`
exercises it against a fixture. See docs/phases/v2/v2.0/PLAN.md (v2.0.6).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import duckdb

try:  # dual-mode: `python -m pipeline.checks` vs `python pipeline/checks.py`
    from . import cli, metros
except ImportError:  # pragma: no cover
    import cli
    import metros

REPO = Path(__file__).resolve().parent.parent
DUCKDB = REPO / "transform" / "metrotrack.duckdb"
BRONZE_ROOT = REPO / "data" / "bronze"

MIN_AUTHORITIES = 3         # ≥3 operators with routes, else a GTFS feed went dark [H13a]
FUNDING_MAX_AGE_YEARS = 5   # audited NTD funding older than this is stale (warn)
_SHA256 = 64                # hex digest length, used to sanity-check a receipt

# Each gold pillar → (table, feeding bronze sources). The sentinel "agency" means
# "any of this metro's configured GTFS agency ids" (cta/metra/pace for chicago),
# resolved from config so the map stays generic across metros.
GOLD_PILLARS: dict[str, tuple[str, tuple[str, ...]]] = {
    "routes": ("gold_routes", ("agency",)),
    "hex": ("gold_hex_metrics", ("census",)),
    "funding": ("gold_funding", ("ntd", "rta")),
    "vacancy": ("gold_vacancy", ("hiring",)),
}


@dataclass
class VerifyReport:
    """Pass/fail integrity result for one metro. `ok` iff no hard fail (blocked = degrade)."""
    metro: str
    checks: list[cli.Check] = field(default_factory=list)

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.checks.append(cli.Check(name, status, detail))

    @property
    def ok(self) -> bool:
        return all(c.status != "fail" for c in self.checks)

    def render(self) -> str:
        glyph = {"pass": "ok  ", "fail": "FAIL", "blocked": "----"}
        lines = [f"verify_metro  metro={self.metro}"]
        for c in self.checks:
            lines.append(f"  {glyph.get(c.status, c.status)}  {c.name}: {c.detail}")
        lines.append(f"  → {'PASS' if self.ok else 'FAIL'}")
        return "\n".join(lines)


def _load_receipts(bronze_root: Path, slug: str) -> dict[str, dict]:
    """Bronze manifest entries for this metro, keyed `<slug>/<source>/<table>`."""
    manifest = bronze_root / "manifest.json"
    if not manifest.exists():
        return {}
    data = json.loads(manifest.read_text())
    return {k: v for k, v in data.items() if k.startswith(f"{slug}/")}


def _count(con: duckdb.DuckDBPyConnection, sql: str, params: list) -> int | None:
    """Run a scalar count; None if the table is missing (pillar absent → degrade)."""
    try:
        return con.execute(sql, params).fetchone()[0]
    except duckdb.CatalogException:
        return None


def verify_metro(
    slug: str,
    *,
    duckdb_path: Path = DUCKDB,
    bronze_root: Path = BRONZE_ROOT,
    today: date | None = None,
) -> VerifyReport:
    """Prove every published figure for `slug` traces to a source + the freshness floor holds."""
    today = today or date.today()
    rep = VerifyReport(slug)
    metro = metros.load_metro(slug)  # raises on a bad slug — a real misconfiguration
    agency_ids = {a.id for a in metro.agencies}

    if not duckdb_path.exists():
        rep.add("gold warehouse", "fail", f"missing {duckdb_path} — run dbt build")
        return rep

    # 1. Source receipts: the metro ingested *something*, every receipt is well-formed.
    receipts = _load_receipts(bronze_root, slug)
    if not receipts:
        rep.add("source receipts", "fail",
                f"no bronze receipts for {slug!r} — published figures would be untraceable")
        return rep
    bad = [k for k, v in receipts.items()
           if len(str(v.get("sha256", ""))) != _SHA256 or (v.get("rows") or 0) <= 0]
    rep.add("source receipts", "fail" if bad else "pass",
            f"{len(bad)} malformed: {bad}" if bad else f"{len(receipts)} receipts, all hashed")
    sources_present = {v.get("source") for v in receipts.values()}

    # 2. Agency coverage: every configured GTFS operator actually produced bronze.
    missing_agencies = sorted(agency_ids - sources_present)
    rep.add("agency coverage", "fail" if missing_agencies else "pass",
            f"no bronze for {missing_agencies}" if missing_agencies
            else f"all {len(agency_ids)} agencies ingested")

    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        # 3. Per-pillar traceability + tenant-key integrity.
        for name, (table, srcs) in GOLD_PILLARS.items():
            n = _count(con, f"select count(*) from {table} where metro_id = ?", [slug])
            if n is None:
                rep.add(f"pillar:{name}", "blocked", f"{table} absent — pillar degraded")
                continue
            if n == 0:
                rep.add(f"pillar:{name}", "blocked", "no gold rows — pillar hidden [A7a]")
                continue
            required = agency_ids if srcs == ("agency",) else set(srcs)
            if required & sources_present:
                rep.add(f"pillar:{name}", "pass", f"{n} rows ← {sorted(required & sources_present)}")
            else:
                rep.add(f"pillar:{name}", "fail",
                        f"{n} rows but no source receipt in {sorted(required)} — figure without provenance")
            nulls = _count(con, f"select count(*) from {table} where metro_id is null", [])
            if nulls:
                rep.add(f"tenant-key:{name}", "fail", f"{nulls} rows with null metro_id in {table}")

        # 4. Freshness floor — a dark GTFS feed fails loud [H13a].
        auths = _count(con,
                       "select count(distinct authority_id) from gold_routes where metro_id = ?",
                       [slug])
        rep.add("freshness: operators", "fail" if (auths or 0) < MIN_AUTHORITIES else "pass",
                f"{auths} operators with routes (floor {MIN_AUTHORITIES})")

        max_fy = _count(con,
                        "select max(fiscal_year) from gold_funding where metro_id = ?", [slug])
        if max_fy is not None:
            floor = today.year - FUNDING_MAX_AGE_YEARS
            rep.add("freshness: funding", "blocked" if max_fy < floor else "pass",
                    f"latest audited FY {max_fy} (floor {floor})")
    finally:
        con.close()
    return rep


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = cli.add_metro_args(argparse.ArgumentParser(description=__doc__), dry_run=False)
    metro = cli.resolve_metro(ap.parse_args(argv).metro)
    rep = verify_metro(metro.slug)
    print(rep.render())
    return 0 if rep.ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
