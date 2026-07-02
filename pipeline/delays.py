"""Delay + crowding-proxy aggregation over the E11 live-feed samples (v3.e11).

The e4a sampler appends every `/api/live/<metro>` snapshot to an append-only NDJSON
log (`data/bronze/<metro>/cta_live/<utc-day>.ndjson`, one `LiveFeed` per line). This
module rolls that growing time series into the small JSON the delays page renders —
mirroring `ridership_export.py`: aggregation lives here (not the client) so the served
artifact stays tiny, and every figure is honest about what the free feed can support.

What the free CTA feed *can* support (and what it can't):
  • DELAY — CTA's own `delayed` flag per vehicle (BusTracker `dly` / TrainTracker
    `isDly`). This is the operator's delay signal, NOT a computed schedule deviation:
    the prediction feed carries no scheduled time, so true "scheduled − observed"
    minutes aren't derivable from this source. We report the delayed *share* by mode
    and the next-arrival wait distribution, and say so plainly.
  • CROWDING — no load data on the free feed, so we use a BUNCHING proxy: when two
    same-route vehicles are predicted to reach one stop within `BUNCH_GAP_MIN`, the
    headway has collapsed (leader packed, trailer empty). `bunch_rate` = share of
    multi-vehicle (route, stop, direction) observations that are bunched.

# ponytail: reads the NDJSON append log directly — no dbt model, because the samples
# are a gitignored live-feed log that never exists at `dbt build` time (it'd break the
# build). This reuses the export machinery (ridership_export) instead. Honest DataState
# on the page when the log is thin/empty (sample accumulation is time-bounded).
Run after samples accumulate:  python pipeline/delays.py export [--metro chicago]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

try:  # dual-mode (package vs. script), same as the other exporters
    from . import cli
    from .live import BRONZE_ROOT
except ImportError:  # pragma: no cover
    import cli
    from live import BRONZE_ROOT

REPO = Path(__file__).resolve().parent.parent

# Two same-route vehicles predicted at one stop within this many minutes = bunched
# (the scheduled headway has collapsed). CTA bus base headways run ~8–15 min, so a
# ≤2-min gap between successive buses is unambiguous bunching, not normal spacing.
BUNCH_GAP_MIN = 2

# Next-arrival wait buckets (minutes). DUE = countdown 0.
COUNTDOWN_BUCKETS = ("DUE", "1–5", "6–10", "11–15", "16+")

SOURCE = {
    "label": "CTA Bus Tracker + Train Tracker (live feed, sampled) — MetroTrack E11 append log",
    "url": "https://www.transitchicago.com/developers/",
    "note": ("Delay = CTA's own delayed flag (not a schedule deviation — the free "
             "prediction feed carries no scheduled time). Crowding = a bunching proxy "
             "from arrival-prediction headways."),
}


def bucket_countdown(countdown_min: int) -> str:
    """Map a next-arrival countdown (minutes, 0 = DUE) to a wait bucket."""
    if countdown_min <= 0:
        return "DUE"
    if countdown_min <= 5:
        return "1–5"
    if countdown_min <= 10:
        return "6–10"
    if countdown_min <= 15:
        return "11–15"
    return "16+"


def delayed_breakdown(feeds: list[dict]) -> dict:
    """Delayed-vehicle share by mode across every sampled vehicle observation.

    One vehicle in one snapshot = one observation (a vehicle seen in N snapshots
    counts N times — that's the point: it's a share of *observations over time*).
    """
    obs: dict[str, int] = defaultdict(int)
    dly: dict[str, int] = defaultdict(int)
    for feed in feeds:
        for v in feed.get("vehicles", []):
            mode = v.get("mode") or "unknown"
            obs[mode] += 1
            if v.get("delayed"):
                dly[mode] += 1
    modes = sorted(obs)
    by_mode = [
        {"mode": m, "observations": obs[m], "delayed": dly[m],
         "delayedShare": round(dly[m] / obs[m], 4) if obs[m] else 0.0}
        for m in modes
    ]
    total_obs = sum(obs.values())
    total_dly = sum(dly.values())
    return {
        "byMode": by_mode,
        "observations": total_obs,
        "delayed": total_dly,
        "delayedShare": round(total_dly / total_obs, 4) if total_obs else 0.0,
    }


def countdown_histogram(feeds: list[dict]) -> list[dict]:
    """Distribution of next-arrival countdowns across every arrival observation."""
    counts: dict[str, int] = defaultdict(int)
    for feed in feeds:
        for a in feed.get("arrivals", []):
            c = a.get("countdown_min")
            if c is None:
                continue
            counts[bucket_countdown(int(c))] += 1
    return [{"bucket": b, "count": counts[b]} for b in COUNTDOWN_BUCKETS]


def bunching(feeds: list[dict], *, gap_min: int = BUNCH_GAP_MIN) -> dict:
    """Headway-collapse (bunching) proxy from arrival predictions.

    For each snapshot, group arrivals by (route, stop, direction). A group with ≥2
    *distinct* vehicles is one observation; it is bunched when its two soonest
    predicted arrivals fall within `gap_min` minutes — the scheduled gap has
    collapsed. `bunchRate` is bunched ÷ multi-vehicle observations.
    """
    observations = 0
    bunched = 0
    route_obs: dict[str, int] = defaultdict(int)
    route_bunched: dict[str, int] = defaultdict(int)
    for feed in feeds:
        groups: dict[tuple, dict[str, int]] = defaultdict(dict)
        for a in feed.get("arrivals", []):
            c = a.get("countdown_min")
            if c is None:
                continue
            key = (a.get("route_id"), a.get("stop_id"), a.get("direction"))
            veh = a.get("vehicle_id") or f"_{len(groups[key])}"
            # Keep the soonest prediction per distinct vehicle in this group.
            if veh not in groups[key] or int(c) < groups[key][veh]:
                groups[key][veh] = int(c)
        for (route, _stop, _dir), veh_counts in groups.items():
            if len(veh_counts) < 2:
                continue  # need ≥2 vehicles to have a headway at all
            observations += 1
            route_obs[route] += 1
            soonest = sorted(veh_counts.values())
            if soonest[1] - soonest[0] <= gap_min:
                bunched += 1
                route_bunched[route] += 1
    top = sorted(
        ({"route": r, "observations": route_obs[r], "bunched": route_bunched[r],
          "bunchRate": round(route_bunched[r] / route_obs[r], 4)}
         for r in route_obs),
        key=lambda d: (-d["bunched"], -d["observations"], str(d["route"])),
    )
    return {
        "observations": observations,
        "bunched": bunched,
        "bunchRate": round(bunched / observations, 4) if observations else 0.0,
        "gapMin": gap_min,
        "topRoutes": top[:12],
    }


def aggregate(feeds: list[dict]) -> dict:
    """Full delays payload from a list of sampled LiveFeed snapshots."""
    gens = sorted(f.get("generated") for f in feeds if f.get("generated"))
    vehicle_obs = sum(len(f.get("vehicles", [])) for f in feeds)
    arrival_obs = sum(len(f.get("arrivals", [])) for f in feeds)
    return {
        "source": SOURCE,
        "meta": {
            "samples": len(feeds),
            "firstGenerated": gens[0] if gens else None,
            "lastGenerated": gens[-1] if gens else None,
            "vehicleObservations": vehicle_obs,
            "arrivalObservations": arrival_obs,
        },
        "delay": delayed_breakdown(feeds),
        "countdown": countdown_histogram(feeds),
        "bunching": bunching(feeds),
    }


def read_samples(slug: str, *, root: Path = BRONZE_ROOT) -> list[dict]:
    """Load every sampled LiveFeed snapshot for a metro from its NDJSON logs."""
    log_dir = root / slug / "cta_live"
    feeds: list[dict] = []
    if not log_dir.exists():
        return feeds
    for path in sorted(log_dir.glob("*.ndjson")):
        for line in path.read_text().splitlines():
            if line.strip():
                feeds.append(json.loads(line))
    return feeds


def out_path(slug: str) -> Path:
    return REPO / "frontend" / "src" / "data" / slug / "delays.json"


def export(slug: str) -> None:
    """Roll the metro's live-feed samples into delays.json (always written — an
    empty log yields an honest zero-sample payload the page renders as DataState)."""
    feeds = read_samples(slug)
    payload = aggregate(feeds)
    out = out_path(slug)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    m = payload["meta"]
    print(f"  ok  {out.relative_to(REPO)} "
          f"({m['samples']} samples, {m['vehicleObservations']} vehicle obs, "
          f"{payload['bunching']['observations']} bunching obs)")


def main(argv: list[str] | None = None) -> int:
    ap = cli.add_metro_args(argparse.ArgumentParser(description=__doc__), dry_run=False)
    export(cli.resolve_metro(ap.parse_args(argv).metro).slug)
    return 0


if __name__ == "__main__":
    sys.exit(main())
