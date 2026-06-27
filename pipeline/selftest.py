#!/usr/bin/env python3
"""Pipeline self-test — the ETL harness gate (GATE #1).

Runs fast, no network, no external state. Exercises the bronze receipt
contract: deterministic hashing, parquet write, idempotency, and re-ingest on
change. Grows a check per pipeline capability as segments land.

Run: `python pipeline/selftest.py` (inside the project venv).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import bronze
import gtfs


def main() -> int:
    passed: list[str] = []

    # 1. content_hash is deterministic and collision-sensitive.
    assert bronze.content_hash(b"abc") == bronze.content_hash(b"abc")
    assert bronze.content_hash(b"abc") != bronze.content_hash(b"abd")
    passed.append("content_hash deterministic + sensitive")

    with tempfile.TemporaryDirectory() as d:
        # Redirect bronze at a throwaway root so the test never touches data/bronze.
        bronze.BRONZE_ROOT = Path(d) / "bronze"
        bronze.MANIFEST = bronze.BRONZE_ROOT / "manifest.json"

        csv = b"stop_id,stop_name\n00501,Howard\n30374,Clark/Lake\n"
        r1 = bronze.ingest_csv("selftest", "stops", csv)
        assert r1.rows == 2, r1
        parquet = bronze.BRONZE_ROOT / "selftest" / "stops.parquet"
        assert parquet.exists()
        passed.append("ingest_csv writes parquet (2 rows)")

        # Idempotent: identical bytes must not rewrite the file.
        before = parquet.stat().st_mtime_ns
        r2 = bronze.ingest_csv("selftest", "stops", csv)
        after = parquet.stat().st_mtime_ns
        assert r2.sha256 == r1.sha256 and before == after, "re-run rewrote unchanged bronze"
        passed.append("ingest_csv idempotent on identical bytes")

        # Changed bytes: new hash, re-ingest, row count reflects the change.
        r3 = bronze.ingest_csv("selftest", "stops", csv + b"35450,Belmont\n")
        assert r3.rows == 3 and r3.sha256 != r1.sha256, r3
        passed.append("ingest_csv re-ingests on changed bytes (3 rows)")

    # GTFS subset/normalize logic — pure, no network.
    assert gtfs.normalize_csv(b"route_id, shape_id\nA, sA1 \n") == b"route_id,shape_id\nA,sA1\n"
    passed.append("normalize_csv strips header + value whitespace")

    routes_b, ids = gtfs.subset_routes(b"route_id,route_short_name\nA,1\nB,2\nC,3\n", 2)
    assert ids == {"A", "B"} and routes_b.count(b"\n") == 3  # header + 2 rows
    passed.append("subset_routes keeps first N + their ids")

    trips = b"route_id,shape_id\nA,sA1\nA,sA1\nA,sA2\nA,sA3\nB,sB1\nC,sC1\n"
    _, shape_ids = gtfs.subset_trips(trips, {"A", "B"}, max_shapes_per_route=2)
    assert shape_ids == {"sA1", "sA2", "sB1"}, shape_ids  # A capped at 2 shapes, C dropped
    passed.append("subset_trips caps shapes/route + collects shape_ids")

    _, no_shapes = gtfs.subset_trips(b"route_id,trip_id\nA,1\nA,2\nB,3\n", {"A", "B"})
    assert no_shapes == set()
    passed.append("subset_trips tolerates trips.txt without shape_id")

    shapes = b"shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\nsA1,1,2,1\nsA1,1,3,2\nsZ,0,0,1\n"
    assert gtfs.subset_shapes(shapes, {"sA1"}).count(b"\n") == 3  # header + 2 sA1 rows
    passed.append("subset_shapes keeps only referenced shape_ids")

    assert gtfs.subset_head(b"stop_id\na\nb\nc\n", 1) == b"stop_id\na\n"
    passed.append("subset_head keeps header + first M rows")

    for c in passed:
        print(f"  ok  {c}")
    print(f"\nselftest PASS ({len(passed)} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
