"""Shared `--metro` CLI surface for the extract entrypoints. [H1a, H20a]

Every metro-parametrized entrypoint (gtfs, census, funding, hiring, access, …)
parses `--metro` + `--dry-run` the same way and resolves bronze paths through the
same helper, so "add a metro = one config file + one `--metro` run" holds without
each script reinventing arg parsing or path composition.

  • `add_metro_args` / `resolve_metro` — uniform parse + loud failure on a bad slug.
  • `bronze_dir` — the per-metro bronze root: `data/bronze/<metro>/<source>/...`. [H2a]
  • `geo_checks` / `reach` / `DryRunReport` — the `--dry-run` smoke contract: validate
    bbox + census FIPS (no network) and probe feed reachability, returning a pass/fail
    struct instead of writing anything. Network errors are caught and reported as
    "blocked", never raised, so a sandboxed run still produces a report.

Pure except for `reach` (the only network touch), so `pipeline/selftest.py` exercises
the whole surface no-network. See docs/phases/v2/v2.0/PLAN.md (v2.0.3).
"""
from __future__ import annotations

import argparse
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

try:  # dual-mode: `python -m pipeline.<x>` (package) vs `python pipeline/<x>.py` (script)
    from . import metros
except ImportError:  # pragma: no cover - exercised only under direct-script execution
    import metros

DEFAULT_METRO = "chicago"
REPO = Path(__file__).resolve().parent.parent
BRONZE_ROOT = REPO / "data" / "bronze"
UA = "MetroTrackBot/0.1 (+https://transit.an9.dev; civic accountability data)"


def bronze_dir(metro: str, source: str) -> Path:
    """The per-metro bronze directory for one source: data/bronze/<metro>/<source>. [H2a]"""
    return BRONZE_ROOT / metro / source


def add_metro_args(parser: argparse.ArgumentParser, *, dry_run: bool = True) -> argparse.ArgumentParser:
    """Attach the shared `--metro` (+ optional `--dry-run`) flags. One parse for all."""
    parser.add_argument(
        "--metro", default=DEFAULT_METRO, metavar="SLUG",
        help=f"Metro slug, names metros/<slug>.toml (default: {DEFAULT_METRO}).",
    )
    if dry_run:
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Validate feed reachability + bbox/FIPS without writing any bronze.",
        )
    return parser


def resolve_metro(slug: str) -> "metros.Metro":
    """Load + validate metros/<slug>.toml. Exits loud + non-zero on a bad/missing slug."""
    try:
        return metros.load_metro(slug)
    except FileNotFoundError:
        raise SystemExit(
            f"unknown metro {slug!r}: no metros/{slug}.toml "
            f"(known: {', '.join(metros.list_metros()) or 'none'})"
        )
    except ValueError as e:
        raise SystemExit(f"invalid metro config {slug!r}: {e}")


# ── dry-run report struct ────────────────────────────────────────────────
@dataclass
class Check:
    name: str
    status: str  # "pass" | "fail" | "blocked"
    detail: str = ""


@dataclass
class DryRunReport:
    """A pass/fail smoke result for one entrypoint × metro. `ok` iff no hard fail."""
    metro: str
    entrypoint: str
    checks: list[Check] = field(default_factory=list)

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.checks.append(Check(name, status, detail))

    @property
    def ok(self) -> bool:
        return all(c.status != "fail" for c in self.checks)

    @property
    def blocked(self) -> bool:
        return any(c.status == "blocked" for c in self.checks)

    def render(self) -> str:
        glyph = {"pass": "ok  ", "fail": "FAIL", "blocked": "----"}
        lines = [f"dry-run  {self.entrypoint}  metro={self.metro}"]
        for c in self.checks:
            lines.append(f"  {glyph.get(c.status, c.status)}  {c.name}: {c.detail}")
        verdict = "PASS" if self.ok else "FAIL"
        if self.ok and self.blocked:
            verdict = "PASS (some checks network-blocked)"
        lines.append(f"  → {verdict}")
        return "\n".join(lines)


def geo_checks(metro: "metros.Metro") -> list[Check]:
    """No-network validity checks: bbox ordering/range + census FIPS presence."""
    out: list[Check] = []
    minx, miny, maxx, maxy = metro.bbox
    bbox_ok = (
        minx < maxx and miny < maxy
        and -180 <= minx <= 180 and -180 <= maxx <= 180
        and -90 <= miny <= 90 and -90 <= maxy <= 90
    )
    out.append(Check("bbox", "pass" if bbox_ok else "fail", f"{metro.bbox}"))

    census = metro.raw.get("census") or {}
    state = str(census.get("state_fips") or "")
    counties = census.get("county_fips") or []
    lodes_state = str(census.get("lodes_state") or "")
    fips_ok = bool(state) and bool(counties) and bool(lodes_state)
    out.append(Check(
        "census FIPS",
        "pass" if fips_ok else "fail",
        f"state={state or '?'} counties={list(counties) or '?'} lodes={lodes_state or '?'}",
    ))
    return out


def reach(name: str, url: str, *, timeout: int = 10) -> Check:
    """Probe a feed URL without downloading it. Network errors → 'blocked', not raised."""
    if not url:
        return Check(name, "fail", "no url configured")
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return Check(name, "pass", f"HTTP {r.status} (HEAD) {url}")
    except urllib.error.HTTPError as e:
        if e.code in (403, 405, 501):  # HEAD refused — try a 1-byte ranged GET
            try:
                g = urllib.request.Request(
                    url, headers={"User-Agent": UA, "Range": "bytes=0-0"})
                with urllib.request.urlopen(g, timeout=timeout) as r:
                    return Check(name, "pass", f"HTTP {r.status} (GET) {url}")
            except urllib.error.HTTPError as e2:
                return Check(name, "fail", f"HTTP {e2.code} {url}")
            except Exception as e2:  # noqa: BLE001 - network blocked, not a feed fault
                return Check(name, "blocked", f"unreachable (network blocked): {e2}")
        return Check(name, "fail", f"HTTP {e.code} {url}")
    except Exception as e:  # noqa: BLE001 - DNS/connection failure ≈ sandbox network block
        return Check(name, "blocked", f"unreachable (network blocked): {e}")
