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
from datetime import date
from pathlib import Path

import duckdb

import access
import bronze
import census
import checks
import cli
import funding
import gtfs
import hiring
import load
import metros
import tod
import psycopg.conninfo

_ALL_SOURCES = ["cta", "metra", "pace", "census", "ntd", "rta", "hiring"]
_TODAY = date(2026, 6, 28)


def _verify_fixture(root: Path, *, sources=None, authorities=("cta", "metra", "pace"),
                    null_metro: bool = False, funding_fy: int = 2024) -> tuple[Path, Path]:
    """A throwaway gold warehouse + bronze manifest for slug 'chicago'. No network."""
    sources = _ALL_SOURCES if sources is None else sources
    bronze_root = root / "bronze"
    bronze_root.mkdir(parents=True, exist_ok=True)
    manifest = {f"chicago/{s}/t": {"metro": "chicago", "source": s,
                                   "sha256": "a" * 64, "rows": 5} for s in sources}
    (bronze_root / "manifest.json").write_text(json.dumps(manifest))

    db = root / "w.duckdb"
    con = duckdb.connect(str(db))
    con.execute("create table gold_routes(metro_id text, authority_id text, route_id text)")
    for a in authorities:
        con.execute("insert into gold_routes values ('chicago', ?, '1')", [a])
    if null_metro:
        con.execute("insert into gold_routes values (NULL, 'cta', '99')")
    con.execute("create table gold_hex_metrics(metro_id text, h3 text)")
    con.execute("insert into gold_hex_metrics values ('chicago', '8a')")
    con.execute("create table gold_funding(metro_id text, authority_id text, fiscal_year int)")
    con.execute("insert into gold_funding values ('chicago', 'cta', ?)", [funding_fy])
    con.execute("create table gold_vacancy(metro_id text, authority_id text, "
                "as_of date, open_postings int)")
    con.execute("insert into gold_vacancy values ('chicago', 'cta', date '2026-06-01', 4)")
    con.close()
    return db, bronze_root


def _verify_metro_checks(passed: list[str]) -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)

        db, br = _verify_fixture(root / "ok")
        rep = checks.verify_metro("chicago", duckdb_path=db, bronze_root=br, today=_TODAY)
        assert rep.ok, rep.render()
        passed.append("verify_metro passes a complete fixture (sources + 3 operators + fresh)")

        # A configured agency with no bronze receipt → coverage fails (untraceable figure).
        db, br = _verify_fixture(root / "noagency",
                                 sources=[s for s in _ALL_SOURCES if s != "cta"])
        rep = checks.verify_metro("chicago", duckdb_path=db, bronze_root=br, today=_TODAY)
        assert not rep.ok and any(c.name == "agency coverage" and c.status == "fail"
                                  for c in rep.checks), rep.render()
        passed.append("verify_metro fails when a configured agency has no bronze receipt")

        # Only one operator with routes → a feed went dark, freshness floor fails loud.
        db, br = _verify_fixture(root / "dark", authorities=("cta",))
        rep = checks.verify_metro("chicago", duckdb_path=db, bronze_root=br, today=_TODAY)
        assert not rep.ok and any(c.name == "freshness: operators" and c.status == "fail"
                                  for c in rep.checks), rep.render()
        passed.append("verify_metro fails the freshness floor when a GTFS feed goes dark")

        # A null metro_id row → an untenanted figure, tenant-key integrity fails.
        db, br = _verify_fixture(root / "null", null_metro=True)
        rep = checks.verify_metro("chicago", duckdb_path=db, bronze_root=br, today=_TODAY)
        assert not rep.ok and any(c.name.startswith("tenant-key") and c.status == "fail"
                                  for c in rep.checks), rep.render()
        passed.append("verify_metro fails on a null metro_id (untenanted row)")

        # No receipts at all → nothing the figures could trace to, hard fail.
        empty = root / "empty" / "bronze"
        empty.mkdir(parents=True)
        (empty / "manifest.json").write_text("{}")
        db, _ = _verify_fixture(root / "norcpt")
        rep = checks.verify_metro("chicago", duckdb_path=db, bronze_root=empty, today=_TODAY)
        assert not rep.ok, rep.render()
        passed.append("verify_metro fails when the metro has no bronze receipts")


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
        r1 = bronze.ingest_csv("selftest", "stops", csv, metro="chicago")
        assert r1.rows == 2 and r1.metro == "chicago", r1
        # Bronze is namespaced per metro: data/bronze/<metro>/<source>/<table>.parquet.
        parquet = bronze.BRONZE_ROOT / "chicago" / "selftest" / "stops.parquet"
        assert parquet.exists()
        passed.append("ingest_csv writes per-metro parquet (data/bronze/<metro>/…)")

        # A different metro with the same source slug must not collide.
        other = bronze.ingest_csv("selftest", "stops", csv, metro="othertown")
        assert (bronze.BRONZE_ROOT / "othertown" / "selftest" / "stops.parquet").exists()
        assert other.parquet != r1.parquet, (other.parquet, r1.parquet)
        passed.append("ingest_csv namespaces bronze by metro (no cross-metro collision)")

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

    # Access: ORS isochrone parse — rings sorted by cutoff, geometry kept.
    iso = access.parse_isochrone(json.dumps({
        "type": "FeatureCollection",
        "features": [
            {"properties": {"value": 1800.0}, "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}},
            {"properties": {"value": 900.0}, "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 0]]]}},
        ],
    }))
    assert [r["value_s"] for r in iso] == [900, 1800], iso  # sorted ascending
    assert iso[0]["geometry"]["type"] == "Polygon"
    passed.append("parse_isochrone sorts rings by cutoff + keeps geometry")

    # An ORS error body (no features) must fail loudly, not yield zero rings silently.
    try:
        access.parse_isochrone(json.dumps({"error": {"code": 2003, "message": "quota"}}))
        assert False, "parse_isochrone should reject a non-FeatureCollection body"
    except ValueError:
        pass
    passed.append("parse_isochrone rejects an ORS error body")

    # The committed sample fixture parses to its three rings (per-metro bronze path).
    sample = access.parse_isochrone(access.sample_path("chicago").read_bytes())
    assert [r["value_s"] for r in sample] == [900, 1800, 2700], sample
    passed.append("isochrone sample fixture parses to 15/30/45-min rings")

    # Metro registry: the real committed chicago.toml parses + validates, and the
    # invariants reject a bad slug / degenerate bbox / modeless agency. [v2.0.1]
    assert "chicago" in metros.list_metros()
    chi = metros.load_metro("chicago")
    assert chi.metro_id == "chicago" and chi.tz == "America/Chicago", chi
    assert chi.bbox[0] < chi.bbox[2] and chi.bbox[1] < chi.bbox[3], chi.bbox
    assert {a.id for a in chi.agencies} == {"cta", "metra", "pace"}, chi.agencies
    assert next(a for a in chi.agencies if a.id == "pace").ntd_ids == ("50113", "50182")
    passed.append("load_metro(chicago) parses + validates the authored config")

    _ok = {"slug": "x", "name": "X", "tz": "UTC", "status": "live",
           "bbox": [-1, -1, 1, 1], "census": {"state_fips": "17", "lodes_state": "il"},
           "agencies": [{"id": "a", "name": "A", "mode": "bus", "url": "u"}]}
    assert metros.parse_metro("x", _ok).slug == "x"  # the happy path is accepted
    for bad, why in [
        ({**_ok, "slug": "Bad_Slug"}, "bad slug"),
        ({**_ok, "bbox": [1, 1, -1, -1]}, "degenerate bbox"),
        ({**_ok, "status": "maybe"}, "bad status"),
        ({**_ok, "agencies": []}, "no agencies"),
        ({**_ok, "agencies": [{"id": "a", "name": "A", "mode": "plane", "url": "u"}]}, "bad mode"),
    ]:
        try:
            metros.parse_metro(bad["slug"], bad)
            assert False, f"validator should reject: {why}"
        except ValueError:
            pass
    passed.append("metro validators reject bad slug/bbox/status/mode + empty agencies")

    # ── v3.10 TOD: the CBD anchor list → CSV is pure (no network) + multi-CBD-
    # ready; a metro with no [[cbd]] fails loud (time-to-CBD needs an anchor).
    trows = tod.cbds_csv(chi).decode().splitlines()
    assert trows[0] == "cbd_id,name,lat,lon", trows
    assert trows[1].startswith("loop,The Loop,41.8786"), trows
    _nocbd = metros.Metro(slug="x", name="X", tz="UTC", status="live",
                          bbox=(0.0, 0.0, 1.0, 1.0), agencies=(), raw={})
    try:
        tod.cbds_csv(_nocbd)
        assert False, "cbds_csv should reject a metro with no CBD anchor"
    except ValueError:
        pass
    passed.append("tod.cbds_csv emits sorted CBD rows + rejects a metro with no anchor")

    # ── v2.0.3: parametrized pipeline (`--metro`) ──────────────────────────
    # The shared CLI helper resolves the real Chicago config and exits loud on a
    # bogus slug (a typo must fail, never silently no-op).
    chi_cfg = cli.resolve_metro("chicago")
    assert chi_cfg.slug == "chicago"
    try:
        cli.resolve_metro("definitely-not-a-metro")
        assert False, "resolve_metro should reject an unknown slug"
    except SystemExit:
        pass
    passed.append("cli.resolve_metro loads chicago + exits loud on a bogus slug")

    # Per-metro bronze path composition is the same for every source.
    assert cli.bronze_dir("chicago", "cta").as_posix().endswith("data/bronze/chicago/cta")
    assert cli.bronze_dir("sf", "bart").as_posix().endswith("data/bronze/sf/bart")
    passed.append("cli.bronze_dir composes data/bronze/<metro>/<source>")

    # geo_checks pass on a valid metro and flag a degenerate bbox / missing FIPS.
    assert all(c.status == "pass" for c in cli.geo_checks(chi_cfg))
    bad_geo = metros.Metro(slug="x", name="X", tz="UTC", status="live",
                           bbox=(0.0, 0.0, 1.0, 1.0), agencies=(), raw={})
    statuses = {c.name: c.status for c in cli.geo_checks(bad_geo)}
    assert statuses["census FIPS"] == "fail", statuses  # no [census] block
    passed.append("cli.geo_checks passes chicago + fails a metro missing census FIPS")

    # Every feed entrypoint resolves the Chicago config + its bronze path and returns
    # a pass/fail dry-run struct (no-network: geo + config validity only). [H20a]
    entrypoints = {
        "gtfs": gtfs, "census": census, "funding": funding,
        "hiring": hiring, "access": access,
    }
    for name, mod in entrypoints.items():
        report = mod.dry_run(chi_cfg, check_network=False)
        assert isinstance(report, cli.DryRunReport), (name, report)
        assert report.entrypoint == name and report.metro == "chicago", (name, report)
        assert report.ok, f"{name} dry-run should pass for chicago: {report.render()}"
        assert report.checks, f"{name} dry-run produced no checks"
    passed.append("each entrypoint resolves chicago + returns a passing dry-run struct")

    # The dry-run struct reports failure (non-zero verdict) when a check fails.
    failing = cli.DryRunReport("chicago", "demo")
    failing.add("ok-check", "pass")
    failing.add("bad-check", "fail", "boom")
    assert not failing.ok and "FAIL" in failing.render()
    passed.append("DryRunReport.ok is false when any check fails")

    # load.build_conninfo — a raw '%' in the DB password must survive (libpq's URI
    # parser would choke on "%2U…"); we hand it keyword params, undecoded. [v3.0]
    ci = load.build_conninfo(
        "postgresql://postgres:%2Uab,.Za@db.example.co:5432/postgres?sslmode=require")
    d = psycopg.conninfo.conninfo_to_dict(ci)
    assert d["password"] == "%2Uab,.Za" and d["host"] == "db.example.co", d
    assert d["dbname"] == "postgres" and d["sslmode"] == "require", d
    assert load.build_conninfo("host=x dbname=y") == "host=x dbname=y"  # non-URL passthrough
    passed.append("load.build_conninfo tolerates a raw '%' password (no URI percent-decode)")

    # verify_metro — the data-integrity gate the loop reuses (v2.0.6). Exercise it
    # no-network against fixture gold warehouses + bronze manifests: a complete
    # metro passes; a missing source, a dark feed, or a null tenant key fail loud.
    _verify_metro_checks(passed)

    for c in passed:
        print(f"  ok  {c}")
    print(f"\nselftest PASS ({len(passed)} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
