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

    for c in passed:
        print(f"  ok  {c}")
    print(f"\nselftest PASS ({len(passed)} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
