"""Access — openrouteservice walk-isochrone loader (ADR-003).

The signature job-access score (docs/modeling/ACCESS_SCORE.md) wants network walk
isochrones from each origin. ORS needs a free `ORS_API_KEY`; when it is absent the
published ambient metric falls back to a straight-line walkshed computed in dbt
(gold_hex_access) — no synthetic isochrone figure is ever published. This module
carries the ORS integration so it activates the moment a key is configured:

  • `parse_isochrone` (pure, selftested) turns an ORS isochrones FeatureCollection
    into `[{value_s, geometry}]` sorted by cutoff — tested against the committed
    schema fixture data/bronze/ors/isochrone_sample.geojson.
  • `fetch_isochrone` POSTs to ORS foot-walking isochrones (key from env).

See docs/phases/v1/v1.4/PLAN.md.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE = REPO_ROOT / "data" / "bronze" / "ors" / "isochrone_sample.geojson"

ORS_ISOCHRONE_URL = "https://api.openrouteservice.org/v2/isochrones/foot-walking"
# ACCESS_SCORE cutoffs (G2) in seconds — three rings.
CUTOFFS_S = [900, 1800, 2700]  # 15 / 30 / 45 min


def parse_isochrone(raw_geojson: str | bytes) -> list[dict]:
    """ORS isochrones FeatureCollection → [{value_s, geometry}] sorted by cutoff.

    Each feature's `properties.value` is the isochrone's cutoff in seconds and its
    geometry is the reachable Polygon. Raises if the payload isn't the expected shape
    (an ORS error body must fail loudly, never silently yield zero rings).
    """
    fc = json.loads(raw_geojson)
    if fc.get("type") != "FeatureCollection" or "features" not in fc:
        raise ValueError("not an ORS isochrone FeatureCollection")
    out = []
    for f in fc["features"]:
        geom = f.get("geometry") or {}
        if geom.get("type") not in ("Polygon", "MultiPolygon"):
            raise ValueError(f"unexpected isochrone geometry {geom.get('type')!r}")
        out.append({"value_s": int(f["properties"]["value"]), "geometry": geom})
    if not out:
        raise ValueError("isochrone response had no rings")
    return sorted(out, key=lambda r: r["value_s"])


def fetch_isochrone(lon: float, lat: float, cutoffs_s: list[int] | None = None) -> bytes:
    """POST a foot-walking isochrone request to ORS (requires ORS_API_KEY)."""
    import urllib.request
    key = os.environ.get("ORS_API_KEY", "")
    if not key:
        sys.exit("ORS_API_KEY not set — cannot fetch live isochrones (use the committed sample)")
    body = json.dumps({
        "locations": [[lon, lat]],
        "range": cutoffs_s or CUTOFFS_S,
        "range_type": "time",
    }).encode()
    req = urllib.request.Request(
        ORS_ISOCHRONE_URL, data=body,
        headers={"Authorization": key, "Content-Type": "application/json",
                 "Accept": "application/geo+json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


if __name__ == "__main__":
    # Smoke: parse the committed sample (works with no key) and report the rings.
    rings = parse_isochrone(SAMPLE.read_bytes())
    for r in rings:
        print(f"  ring {r['value_s']}s  {r['geometry']['type']}")
    print(f"ok  {len(rings)} isochrone rings parsed from the sample fixture")
