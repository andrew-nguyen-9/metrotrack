"""Metro registry — load + validate `metros/<slug>.toml`, the authored truth. [B2c]

A metro is defined once, in `metros/<slug>.toml`; this module parses + validates it
into a `Metro` the pipeline reads (v2.0.3 wires `--metro` through it) and that
`sync_metros()` (pipeline/load.py) mirrors into `public.metros` for serving/joins.

Pure + no network, so `pipeline/selftest.py` exercises it against the real committed
config. `tomllib` is stdlib (Python 3.12) — no new dependency. Contract +
field reference: metros/_schema.md. See docs/phases/v2/v2.0/PLAN.md.
"""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
METROS_DIR = REPO / "metros"

# Kebab: safe as a URL path, a filename stem, and a Postgres text key at once.
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MODES = {"bus", "rail", "multi"}
STATUSES = {"live", "soon"}


@dataclass(frozen=True)
class Agency:
    id: str
    name: str
    mode: str
    url: str
    gtfs_url: str
    ntd_ids: tuple[str, ...] = ()
    raw: dict = field(default_factory=dict, repr=False)  # full agency table (hiring, discover, …)


@dataclass(frozen=True)
class Metro:
    slug: str
    name: str
    tz: str
    status: str
    bbox: tuple[float, float, float, float]  # (minLon, minLat, maxLon, maxLat)
    agencies: tuple[Agency, ...]
    raw: dict = field(default_factory=dict, repr=False)  # full parsed toml (census, region, …)

    @property
    def metro_id(self) -> str:
        return self.slug


def parse_metro(slug: str, data: dict) -> Metro:
    """Build + validate a Metro from a parsed toml dict. Raises ValueError on a bad config."""
    def need(d: dict, key: str, where: str):
        if key not in d or d[key] in ("", None):
            raise ValueError(f"{slug}: missing required key {where}{key!r}")
        return d[key]

    if not SLUG_RE.match(slug):
        raise ValueError(f"{slug!r} is not a valid kebab slug")
    if data.get("slug") != slug:
        raise ValueError(f"{slug}: toml slug={data.get('slug')!r} must equal filename stem {slug!r}")

    status = need(data, "status", "")
    if status not in STATUSES:
        raise ValueError(f"{slug}: status {status!r} not in {sorted(STATUSES)}")

    bbox = tuple(float(x) for x in need(data, "bbox", ""))
    if len(bbox) != 4:
        raise ValueError(f"{slug}: bbox needs 4 numbers, got {len(bbox)}")
    minx, miny, maxx, maxy = bbox
    if not (minx < maxx and miny < maxy):
        raise ValueError(f"{slug}: degenerate bbox {bbox} (need minLon<maxLon, minLat<maxLat)")
    if not (-180 <= minx <= 180 and -180 <= maxx <= 180 and -90 <= miny <= 90 and -90 <= maxy <= 90):
        raise ValueError(f"{slug}: bbox {bbox} out of world range")

    raw_agencies = data.get("agencies") or []
    if not raw_agencies:
        raise ValueError(f"{slug}: needs at least one agency")
    agencies = []
    for a in raw_agencies:
        mode = need(a, "mode", "agency.")
        if mode not in MODES:
            raise ValueError(f"{slug}: agency {a.get('id')!r} mode {mode!r} not in {sorted(MODES)}")
        agencies.append(Agency(
            id=need(a, "id", "agency."), name=need(a, "name", "agency."), mode=mode,
            url=need(a, "url", "agency."), gtfs_url=a.get("gtfs_url", ""),
            ntd_ids=tuple(a.get("ntd_ids", ())), raw=a,
        ))

    census = data.get("census") or {}
    need(census, "state_fips", "census.")
    need(census, "lodes_state", "census.")

    return Metro(
        slug=slug, name=need(data, "name", ""), tz=need(data, "tz", ""),
        status=status, bbox=bbox, agencies=tuple(agencies), raw=data,
    )


def load_metro(slug: str) -> Metro:
    """Read + validate metros/<slug>.toml."""
    with (METROS_DIR / f"{slug}.toml").open("rb") as f:
        return parse_metro(slug, tomllib.load(f))


def list_metros() -> list[str]:
    """All metro slugs with a config file, sorted."""
    return sorted(p.stem for p in METROS_DIR.glob("*.toml"))
