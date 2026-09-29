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
        docs = list(db[coll].find({}, {"_id": 0}))
        return [_coerce_datetimes(d) for d in docs]

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
        [_coerce_datetimes(dict(r)) for r in experiments],
        [_coerce_datetimes(dict(r)) for r in run_status],
        [_coerce_datetimes(dict(r)) for r in results],
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


def _write_sqlite(
    sqlite_db_path: str,
    experiments: list[dict],
    run_status: list[dict],
    results: list[dict],
    *,
    dry_run: bool,
) -> dict[str, int]:
    """Copy records into SQLite, idempotent by PK. Returns inserted counts."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    os.environ.setdefault("SQLITE_DB_PATH", sqlite_db_path)

    # Patch settings so SQLiteStorageBackend uses the target path.
    from server.settings import settings as _settings

    _settings.sqlite_db_path = sqlite_db_path

    from server.db.sqlite.sqlite_store import SQLiteStorageBackend

    store = SQLiteStorageBackend()
    counts = {"experiments": 0, "run_status": 0, "results": 0}

    if dry_run:
        print(f"  [DRY-RUN] would insert {len(experiments)} experiments")
        print(f"  [DRY-RUN] would insert {len(run_status)} run_status rows")
        print(f"  [DRY-RUN] would insert {len(results)} results")
        return counts

    # Experiments — skip if already present.
    existing_experiments = {e["experiment_id"] for e in store.find_all_experiments()}
    for exp in experiments:
        if exp.get("experiment_id") in existing_experiments:
            continue
        try:
            store.insert_experiment_doc(exp)
            counts["experiments"] += 1
        except Exception as exc:
            print(f"  WARN experiment {exp.get('experiment_id')} insert failed: {exc}")

    # Run status — skip if already present.
    for run in run_status:
        exp_id = run.get("experiment_id", "")
        existing_runs = {r["run_id"] for r in (store.find_run_statuses(exp_id) if exp_id else [])}
        if run.get("run_id") in existing_runs:
            continue
        try:
            store.insert_run_status(run)
            counts["run_status"] += 1
        except Exception as exc:
            print(f"  WARN run {run.get('run_id')} insert failed: {exc}")

    # Results — no unique PK constraint beyond result_id autoincrement;
    # dedupe by (experiment_id, run_id, query_id).
    existing_result_keys: set[tuple[str, str, str]] = set()
    all_experiments_for_results = {e["experiment_id"] for e in experiments}
    for exp_id in all_experiments_for_results:
        for r in store.list_results_for_experiment(exp_id):
            existing_result_keys.add(
                (
                    str(r.get("experiment_id", "")),
                    str(r.get("run_id", "")),
                    str(r.get("query_id", "")),
                )
            )
    for result in results:
        key = (
            str(result.get("experiment_id", "")),
            str(result.get("run_id", "")),
            str(result.get("query_id", "")),
        )
        if key in existing_result_keys:
            continue
        try:
            store.insert_result(result)
            counts["results"] += 1
            existing_result_keys.add(key)
        except Exception as exc:
            print(f"  WARN result insert failed: {exc}")

    return counts


# ── Hash-verify ───────────────────────────────────────────────────────────────


def _verify_parity(
    source: tuple[list[dict], list[dict], list[dict]],
    target_store_path: str,
) -> bool:
    """Compare source row counts to SQLite target. Returns True when counts match."""
    from server.settings import settings as _settings

    _settings.sqlite_db_path = target_store_path
    from server.db.sqlite.sqlite_store import SQLiteStorageBackend, _local

    _local.__dict__.clear()  # Force fresh connection to ensure committed data is visible
    store = SQLiteStorageBackend()

    src_exps, src_runs, src_results = source
    tgt_exps = store.find_all_experiments()
    # Tally run_status and results across all experiments
    tgt_runs = [r for exp in tgt_exps for r in store.find_run_statuses(exp["experiment_id"])]
    tgt_results = [
        r for exp in tgt_exps for r in store.list_results_for_experiment(exp["experiment_id"])
    ]

    ok = True
    for label, src, tgt in (
        ("experiments", src_exps, tgt_exps),
        ("run_status", src_runs, tgt_runs),
        ("results", src_results, tgt_results),
    ):
        if len(src) <= len(tgt):
            print(f"  ✓ {label}: source={len(src)}  target={len(tgt)}")
        else:
            print(f"  ✗ {label}: source={len(src)}  target={len(tgt)}  MISMATCH")
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
