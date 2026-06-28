#!/usr/bin/env python3
"""Pipeline self-test — the ETL harness gate (GATE #1).

Runs fast, no network, no external state. Exercises the bronze receipt
contract: deterministic hashing, parquet write, idempotency, and re-ingest on
change. Grows a check per pipeline capability as segments land.

Run: `python pipeline/selftest.py` (inside the project venv).
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import bronze
import census
import funding
import gtfs
import hiring


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

    # Census LODES WAC parse — Cook County filter + bg_geoid derivation. Two extra
    # trailing C-columns prove we index by header name, not position.
    lodes = census.parse_lodes_wac(
        b"w_geocode,C000,CA01,CE01\n"
        b"170310001001000,5,1,4\n"   # Cook (17031) — kept
        b"170010001001000,9,2,7\n"   # Adams (17001) — dropped
    )
    rows = [r for r in lodes.decode().splitlines()]
    assert rows[0] == "w_geocode,bg_geoid,jobs", rows
    assert rows[1] == "170310001001000,170310001001,5" and len(rows) == 2, rows
    passed.append("parse_lodes_wac keeps Cook blocks + derives bg_geoid + jobs")

    # Census Centers-of-Population parse — BOM + '+' coords + Cook filter.
    cenpop = census.parse_cenpop_bg(
        "﻿STATEFP,COUNTYFP,TRACTCE,BLKGRPCE,POPULATION,LATITUDE,LONGITUDE\n"
        "17,031,000100,1,1135,+41.880000,-087.630000\n"   # Cook — kept
        "17,001,000100,2,745,+39.940000,-091.360000\n"     # Adams — dropped
        .encode()
    )
    crows = cenpop.decode().splitlines()
    assert crows[0] == "bg_geoid,population,lat,lon", crows
    assert crows[1] == "170310001001,1135,41.880000,-087.630000" and len(crows) == 2, crows
    passed.append("parse_cenpop_bg assembles bg_geoid, strips BOM/+, filters Cook")

    # NTD parse — Chicago reporters only; Pace's two reports fold into one line;
    # foreign agencies dropped; numeric fields summed.
    ntd = funding.parse_ntd(json.dumps([
        {"ntd_id": "50066", "report_year": "2024", "sum_total_operating_expenses": "1918053610",
         "sum_fare_revenues_earned": "354907822", "sum_unlinked_passenger_trips": "309197026"},
        {"ntd_id": "50113", "report_year": "2024", "sum_total_operating_expenses": "267529288",
         "sum_fare_revenues_earned": "21353765", "sum_unlinked_passenger_trips": "17906275"},
        {"ntd_id": "50182", "report_year": "2024", "sum_total_operating_expenses": "219913374",
         "sum_fare_revenues_earned": "8805608", "sum_unlinked_passenger_trips": "3215055"},
        {"ntd_id": "00001", "report_year": "2024", "sum_total_operating_expenses": "999"},  # not Chicago
    ]).encode())
    nrows = ntd.decode().splitlines()
    assert nrows[0] == "authority_id,fiscal_year,operating_expense,fare_revenue,unlinked_trips", nrows
    assert nrows[1] == "cta,2024,1918053610,354907822,309197026", nrows
    # Pace = 50113 + 50182 summed; foreign reporter dropped → exactly 2 data rows.
    assert nrows[2] == "pace,2024,487442662,30159373,21121330" and len(nrows) == 3, nrows
    passed.append("parse_ntd keeps Chicago boards, folds Pace's two reports, drops others")

    # RTA budget parse — thousands→dollars, ADA folds into Pace, kind preserved.
    rta = funding.parse_rta_budget(
        b"authority_id,fiscal_year,kind,amount_thousands\n"
        b"cta,2025,budget,2156522\n"
        b"metra,2025,budget,1135000\n"
        b"pace,2025,budget,339297\n"
        b"ada,2025,budget,281231\n"
    )
    brows = rta.decode().splitlines()
    assert brows[0] == "authority_id,fiscal_year,kind,amount", brows
    assert "cta,2025,budget,2156522000" in brows, brows
    assert "pace,2025,budget,620528000" in brows, brows  # 339,297 + 281,231 (ADA) → dollars
    passed.append("parse_rta_budget folds ADA into Pace, converts thousands→dollars")

    # Reconciliation guard: a transcription fat-finger must fail loudly.
    try:
        funding.parse_rta_budget(
            b"authority_id,fiscal_year,kind,amount_thousands\n"
            b"cta,2025,budget,2156522\nmetra,2025,budget,1135000\n"
            b"pace,2025,budget,339297\nada,2025,budget,281999\n"  # ADA off by 768k
        )
        assert False, "reconciliation should have rejected the bad total"
    except ValueError as e:
        assert "FY2025" in str(e), e
    passed.append("parse_rta_budget reconciles board sum vs Table 2 total (rejects fat-finger)")

    # Hiring: Taleo prints a total; the parser reads it out of rendered text.
    assert hiring.parse_taleo_count("...\nJob Openings 1 - 13 of 13\nPosting Date\n") == 13
    assert hiring.parse_taleo_count(b"Job Openings 1 - 25 of 1,204 ") == 1204  # commas + bytes
    passed.append("parse_taleo_count reads the printed listing total")

    # Cadient: count distinct postings, drop the generic "Apply Now" link + dups.
    assert hiring.count_cadient_titles(
        ["Carman", "Roadmaster", "Carman", "Apply Now", "  ", "Senior Architect"]
    ) == 3
    passed.append("count_cadient_titles dedups + drops generic links")

    # Oracle Recruiting REST: TotalJobsCount, with the items[0] envelope + fallback.
    assert hiring.parse_oracle_count(
        json.dumps({"items": [{"TotalJobsCount": 57, "requisitionList": [{}, {}]}]})
    ) == 57
    assert hiring.parse_oracle_count(json.dumps({"requisitionList": [{}, {}, {}]})) == 3  # fallback
    passed.append("parse_oracle_count reads TotalJobsCount (with fallback)")

    # Snapshot log is append-safe: a second same-day run replaces, never duplicates.
    base = hiring.append_snapshot(b"", [{"authority_id": "cta", "open_postings": 13,
        "source_url": "u", "method": "taleo"}], "2026-06-27")
    again = hiring.append_snapshot(base, [{"authority_id": "cta", "open_postings": 15,
        "source_url": "u", "method": "taleo"}], "2026-06-27")
    arows = again.decode().strip().splitlines()
    assert len(arows) == 2 and arows[1].startswith("cta,2026-06-27,15"), arows  # replaced, not dup'd
    grown = hiring.append_snapshot(base, [{"authority_id": "cta", "open_postings": 14,
        "source_url": "u", "method": "taleo"}], "2026-07-04")
    assert len(grown.decode().strip().splitlines()) == 3  # new date appends
    passed.append("append_snapshot replaces same-day, appends new dates")

    for c in passed:
        print(f"  ok  {c}")
    print(f"\nselftest PASS ({len(passed)} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
