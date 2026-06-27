"""Bronze layer — content-hashed, append-safe parquet. The reproducibility receipt.

Every external pull lands here first. Raw bytes are SHA-256'd so re-runs are
idempotent (identical bytes → no rewrite) and every served figure traces back to a
committed snapshot (see docs/DEFINITION_OF_DONE.md data-integrity checks).

DuckDB is the single data engine here and in dbt-duckdb (transform/), so bronze
needs no pandas/pyarrow. Bronze is intentionally untyped (`all_varchar`): typing,
dedup, and geometry validation happen in silver.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
BRONZE_ROOT = REPO_ROOT / "data" / "bronze"
MANIFEST = BRONZE_ROOT / "manifest.json"


def content_hash(data: bytes) -> str:
    """SHA-256 of raw bytes — the bronze receipt key."""
    return hashlib.sha256(data).hexdigest()


@dataclass
class BronzeReceipt:
    source: str
    table: str
    sha256: str
    rows: int
    parquet: str  # repo-relative path
    written_at: str


def _load_manifest() -> dict:
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}


def _save_manifest(manifest: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def ingest_csv(source: str, table: str, csv_bytes: bytes, *, header: bool = True) -> BronzeReceipt:
    """Convert raw CSV bytes → bronze parquet. Idempotent on the content hash.

    Returns the existing receipt untouched when the bytes match what's on disk, so
    a nightly re-run of an unchanged source neither rewrites nor duplicates.
    """
    key = f"{source}/{table}"
    sha = content_hash(csv_bytes)
    manifest = _load_manifest()
    out = BRONZE_ROOT / source / f"{table}.parquet"

    if manifest.get(key, {}).get("sha256") == sha and out.exists():
        return BronzeReceipt(**manifest[key])  # unchanged: no rewrite

    out.parent.mkdir(parents=True, exist_ok=True)
    hdr = "true" if header else "false"
    con = duckdb.connect()
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
            tf.write(csv_bytes)
            tmp = tf.name
        con.execute(
            f"COPY (SELECT * FROM read_csv_auto('{tmp}', header={hdr}, all_varchar=true)) "
            f"TO '{out}' (FORMAT parquet, COMPRESSION zstd)"
        )
        rows = con.execute("SELECT count(*) FROM read_parquet(?)", [str(out)]).fetchone()[0]
    finally:
        con.close()
        if tmp:
            Path(tmp).unlink(missing_ok=True)

    try:
        rel = out.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        rel = out.as_posix()  # bronze root redirected outside the repo (e.g. selftest)

    receipt = BronzeReceipt(
        source=source,
        table=table,
        sha256=sha,
        rows=rows,
        parquet=rel,
        written_at=datetime.now(timezone.utc).isoformat(),
    )
    manifest[key] = asdict(receipt)
    _save_manifest(manifest)
    return receipt
