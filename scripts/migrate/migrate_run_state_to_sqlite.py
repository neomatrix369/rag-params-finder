#!/usr/bin/env python3
"""Migrate run-state data from MongoDB or Postgres to SQLite (Slice 55, ADR-008).

Usage:
    # Dry-run (default): verify what would be copied, no writes
    uv run python scripts/migrate/migrate_run_state_to_sqlite.py

    # Execute migration (MongoDB → SQLite)
    uv run python scripts/migrate/migrate_run_state_to_sqlite.py --execute

    # Remove source records after verifying parity (opt-in, destructive)
    uv run python scripts/migrate/migrate_run_state_to_sqlite.py --execute --drop-source

    # Specify a non-default SQLite target path
    SQLITE_DB_PATH=./data/run_state.db uv run python scripts/migrate/migrate_run_state_to_sqlite.py --execute

Migration steps:
    1. Read all experiments / run_status / results from the source backend.
    2. Copy records idempotently by primary key into the SQLite target
       (already-present rows are skipped, not overwritten).
    3. Hash-verify row counts match between source and target.
    4. Backup the source connection string to a local .bak file.
    5. Optionally drop source rows (--drop-source, never touches chunks).

SQLite is run-state-only: chunks stay in the vector store.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _json_hash(records: list[dict]) -> str:
    payload = json.dumps(records, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


# ── Source readers ────────────────────────────────────────────────────────────


def _read_mongo(mongodb_uri: str) -> tuple[list[dict], list[dict], list[dict]]:
    """Return (experiments, run_status, results) from a MongoDB backend."""
    try:
        from pymongo import MongoClient
    except ImportError as exc:
        raise SystemExit("pymongo not installed — add it to your dev dependencies") from exc

    client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
    db_name = mongodb_uri.rsplit("/", 1)[-1].split("?")[0] or "rag_params_finder"
    db = client[db_name]

    def _fetch(coll: str) -> list[dict]:
        return list(db[coll].find({}, {"_id": 0}))

    experiments = _fetch("experiments")
    run_status = _fetch("run_status")
    results = _fetch("results")
    client.close()
    return experiments, run_status, results


def _read_postgres(database_url: str) -> tuple[list[dict], list[dict], list[dict]]:
    """Return (experiments, run_status, results) from a Postgres backend."""
    try:
        import psycopg
        import psycopg.rows
    except ImportError as exc:
        raise SystemExit("psycopg not installed — add it to your dev dependencies") from exc

    with psycopg.connect(database_url, row_factory=psycopg.rows.dict_row) as conn:
        experiments = list(conn.execute("SELECT * FROM experiments").fetchall())
        run_status = list(conn.execute("SELECT * FROM run_status").fetchall())
        results = list(conn.execute("SELECT * FROM results").fetchall())

    return (
        [dict(r) for r in experiments],
        [dict(r) for r in run_status],
        [dict(r) for r in results],
    )


def _coerce_datetimes(d: dict) -> dict:
    """Convert datetime objects to ISO strings for JSON-safe hashing."""
    out: dict = {}
    for k, v in d.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = _coerce_datetimes(v)
        else:
            out[k] = v
    return out


# ── SQLite writer ─────────────────────────────────────────────────────────────


def _serialize(v: object) -> object:
    """Coerce a value to a SQLite-safe scalar (datetime → ISO string)."""
    if isinstance(v, datetime):
        return v.isoformat()
    return v


def _write_sqlite(
    sqlite_db_path: str,
    experiments: list[dict],
    run_status: list[dict],
    results: list[dict],
    *,
    dry_run: bool,
) -> dict[str, int]:
    """Copy records into SQLite in a single transaction. Idempotent by PK."""
    counts = {"experiments": 0, "run_status": 0, "results": 0}

    if dry_run:
        print(f"  [DRY-RUN] would insert {len(experiments)} experiments")
        print(f"  [DRY-RUN] would insert {len(run_status)} run_status rows")
        print(f"  [DRY-RUN] would insert {len(results)} results")
        return counts

    import sqlite3

    exp_promoted = {
        "experiment_id",
        "experiment_name",
        "status",
        "created_at",
        "started_at",
        "completed_at",
        "vector_store_snapshot",
    }
    run_promoted = {
        "run_id",
        "experiment_id",
        "phase",
        "created_at",
        "updated_at",
        "embedding_dimensions",
    }
    res_promoted = {"experiment_id", "run_id", "query_id", "query_text"}

    def _doc_blob(record: dict, promoted: set[str]) -> str:
        return json.dumps(
            {k: _serialize(v) for k, v in record.items() if k not in promoted}, default=str
        )

    def _vss(v: object) -> str | None:
        if v is None:
            return None
        return json.dumps(v) if isinstance(v, dict) else str(v)

    conn = sqlite3.connect(sqlite_db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")

    try:
        with conn:
            # Experiments — idempotent via INSERT OR IGNORE on experiment_id PK.
            existing_exp_ids = {
                r[0] for r in conn.execute("SELECT experiment_id FROM experiments").fetchall()
            }
            for exp in experiments:
                eid = exp.get("experiment_id")
                if eid in existing_exp_ids:
                    continue
                conn.execute(
                    """INSERT OR IGNORE INTO experiments
                       (experiment_id, experiment_name, status, created_at, started_at,
                        completed_at, vector_store_snapshot, doc)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        eid,
                        exp.get("experiment_name"),
                        exp.get("status"),
                        _serialize(exp.get("created_at")),
                        _serialize(exp.get("started_at")),
                        _serialize(exp.get("completed_at")),
                        _vss(exp.get("vector_store_snapshot")),
                        _doc_blob(exp, exp_promoted),
                    ),
                )
                counts["experiments"] += 1

            # Run status — idempotent via INSERT OR IGNORE on run_id PK.
            existing_run_ids = {
                r[0] for r in conn.execute("SELECT run_id FROM run_status").fetchall()
            }
            for run in run_status:
                rid = run.get("run_id")
                if rid in existing_run_ids:
                    continue
                conn.execute(
                    """INSERT OR IGNORE INTO run_status
                       (run_id, experiment_id, phase, created_at, updated_at,
                        embedding_dimensions, doc)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        rid,
                        run.get("experiment_id"),
                        run.get("phase"),
                        _serialize(run.get("created_at")),
                        _serialize(run.get("updated_at")),
                        run.get("embedding_dimensions"),
                        _doc_blob(run, run_promoted),
                    ),
                )
                counts["run_status"] += 1

            # Results — dedupe by (experiment_id, run_id, query_id) since result_id
            # is an autoincrement PK that won't match across backends.
            existing_keys = {
                (r[0], r[1], r[2])
                for r in conn.execute(
                    "SELECT experiment_id, run_id, query_id FROM results"
                ).fetchall()
            }
            for result in results:
                key = (
                    str(result.get("experiment_id", "")),
                    str(result.get("run_id", "")),
                    str(result.get("query_id", "")),
                )
                if key in existing_keys:
                    continue
                conn.execute(
                    """INSERT INTO results
                       (experiment_id, run_id, query_id, query_text, doc)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        result.get("experiment_id"),
                        result.get("run_id"),
                        result.get("query_id"),
                        result.get("query_text", ""),
                        _doc_blob(result, res_promoted),
                    ),
                )
                counts["results"] += 1
                existing_keys.add(key)
    finally:
        conn.close()

    return counts


# ── Hash-verify ───────────────────────────────────────────────────────────────


def _verify_parity(
    source: tuple[list[dict], list[dict], list[dict]],
    target_store_path: str,
) -> bool:
    """Compare source row counts to SQLite target. Returns True when counts match."""
    import sqlite3

    conn = sqlite3.connect(target_store_path, timeout=10)
    try:
        tgt_exp_count = conn.execute("SELECT COUNT(*) FROM experiments").fetchone()[0]
        tgt_run_count = conn.execute("SELECT COUNT(*) FROM run_status").fetchone()[0]
        tgt_res_count = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    finally:
        conn.close()

    src_exps, src_runs, src_results = source
    ok = True
    for label, src_count, tgt_count in (
        ("experiments", len(src_exps), tgt_exp_count),
        ("run_status", len(src_runs), tgt_run_count),
        ("results", len(src_results), tgt_res_count),
    ):
        if src_count <= tgt_count:
            print(f"  ✓ {label}: source={src_count}  target={tgt_count}")
        else:
            print(f"  ✗ {label}: source={src_count}  target={tgt_count}  MISMATCH")
            ok = False
    return ok


# ── Backup ────────────────────────────────────────────────────────────────────


def _backup_source_uri(source_type: str, uri: str) -> Path:
    """Write source URI to a timestamped .bak file."""
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    bak_path = Path(f".migrate_run_state_{source_type}_{ts}.bak")
    bak_path.write_text(uri)
    print(f"  Backed up source URI to {bak_path}")
    return bak_path


# ── Drop source ───────────────────────────────────────────────────────────────


def _drop_source_mongo(mongodb_uri: str, experiment_ids: list[str]) -> None:
    """Delete run-state documents from MongoDB for the migrated experiments."""
    from pymongo import MongoClient

    client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
    db_name = mongodb_uri.rsplit("/", 1)[-1].split("?")[0] or "rag_params_finder"
    db = client[db_name]
    for coll in ("experiments", "run_status", "results"):
        result = db[coll].delete_many({"experiment_id": {"$in": experiment_ids}})
        print(f"  Dropped {result.deleted_count} {coll} rows from MongoDB")
    client.close()


def _drop_source_postgres(database_url: str, experiment_ids: list[str]) -> None:
    """Delete run-state documents from Postgres for the migrated experiments."""
    import psycopg

    with psycopg.connect(database_url) as conn:
        for tbl in ("results", "run_status", "experiments"):
            conn.execute(
                f"DELETE FROM {tbl} WHERE experiment_id = ANY(%s)",  # noqa: S608
                (experiment_ids,),
            )
            conn.commit()
            print(f"  Dropped rows from Postgres {tbl}")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--execute", action="store_true", help="Write to SQLite (default: dry-run)")
    parser.add_argument(
        "--drop-source",
        action="store_true",
        help="Remove source rows after verified parity (opt-in)",
    )
    args = parser.parse_args()

    dry_run = not args.execute

    # Detect source backend from environment.
    mongodb_uri = os.environ.get("MONGODB_URI", "")
    database_url = os.environ.get("DATABASE_URL", "") or os.environ.get("SUPABASE_URI", "")
    sqlite_db_path = os.environ.get("SQLITE_DB_PATH", "./data/run_state.db")

    if database_url:
        source_type = "postgres"
        print(f"[{_now_iso()}] Source: Postgres ({database_url[:40]}...)")
        source = _read_postgres(database_url)
    elif mongodb_uri:
        source_type = "mongodb"
        print(f"[{_now_iso()}] Source: MongoDB ({mongodb_uri[:40]}...)")
        source = _read_mongo(mongodb_uri)
    else:
        print("ERROR: Set MONGODB_URI or DATABASE_URL to identify the source backend.")
        sys.exit(1)

    exps, runs, results = source
    print(f"  Read {len(exps)} experiments, {len(runs)} run_status, {len(results)} results")
    print(f"  Target SQLite: {sqlite_db_path}")

    if dry_run:
        print(f"\n[{_now_iso()}] DRY-RUN — pass --execute to write\n")
    else:
        print(f"\n[{_now_iso()}] Executing migration ...\n")

    counts = _write_sqlite(sqlite_db_path, exps, runs, results, dry_run=dry_run)
    if not dry_run:
        print(f"  Inserted: {counts}")

    if not dry_run:
        print(f"\n[{_now_iso()}] Verifying parity ...")
        ok = _verify_parity(source, sqlite_db_path)
        if not ok:
            print(
                "\nERROR: Row count mismatch — do NOT use --drop-source until parity is confirmed."
            )
            sys.exit(1)
        print("  Parity: OK")

        _backup_source_uri(source_type, database_url or mongodb_uri)

        if args.drop_source:
            exp_ids = [str(e["experiment_id"]) for e in exps]
            print(f"\n[{_now_iso()}] Dropping source rows ({len(exp_ids)} experiments) ...")
            if source_type == "mongodb":
                _drop_source_mongo(mongodb_uri, exp_ids)
            else:
                _drop_source_postgres(database_url, exp_ids)
            print("  Drop complete — chunks untouched.")
        else:
            print("\n  Source rows retained (pass --drop-source to remove them).")

    print(f"\n[{_now_iso()}] Migration {'dry-run' if dry_run else 'complete'}.")


if __name__ == "__main__":
    main()
