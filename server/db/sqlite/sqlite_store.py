"""SQLite run-state adapter implementing StorageBackend (Slice 55, ADR-008).

Run-state-only: experiments, run_status, results. No chunks table — chunk/vector
data always lives in VECTOR_STORE_BACKEND. Stats methods return 0 chunks; live
chunk counts require querying the vector store separately.

Thread safety: WAL mode + busy_timeout=5000 (required — SWEEP_EXECUTOR and
HEAVY_READ_EXECUTOR both touch run state concurrently). Each thread gets its own
connection via threading.local; WAL allows multiple concurrent readers with a
single writer without SQLITE_BUSY.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from server.db.ports.stats_common import (
    assemble_experiment_db_stats,
    experiment_summary_row,
    finalize_groups,
    merge_group_totals,
    new_vector_db_group,
    normalize_stats_database_provider,
    resolve_experiment_storage_mode,
    vector_db_group_key,
)
from server.db.sqlite.sqlite_docs import (
    EXPERIMENT_COLUMNS,
    RESULT_COLUMNS,
    RUN_COLUMNS,
    experiment_row_to_doc,
    result_row_to_doc,
    run_row_to_doc,
    serialize_datetime,
    to_json,
)
from server.models.enums import ExperimentStatus
from server.utils.logger import get_logger

logger = get_logger(__name__)

_SCHEMA_SQL = Path(__file__).with_name("schema.sql").read_text()

_local = threading.local()


def _db_path() -> str:
    from server.settings import settings

    return settings.sqlite_db_path


def _connect() -> sqlite3.Connection:
    """Return a per-thread SQLite connection, creating it on first use.

    WAL mode + busy_timeout are correctness requirements (ADR-008 § Concurrency),
    not optional optimizations: the server process has at least two threads
    (SWEEP_EXECUTOR + HEAVY_READ_EXECUTOR) that touch run state concurrently.
    """
    if not hasattr(_local, "conn") or _local.conn is None:
        path = _db_path()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return cast(sqlite3.Connection, _local.conn)


def _bootstrap_schema() -> None:
    """Apply schema.sql idempotently — called once per server boot."""
    conn = _connect()
    conn.executescript(_SCHEMA_SQL)
    conn.commit()


def _fetchone(sql: str, params: tuple = ()) -> dict | None:
    conn = _connect()
    cur = conn.execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


def _fetchall(sql: str, params: tuple = ()) -> list[dict]:
    conn = _connect()
    cur = conn.execute(sql, params)
    return [dict(row) for row in cur.fetchall()]


def _fetchvalue(sql: str, params: tuple = (), *, default: Any = None) -> Any:
    row = _fetchone(sql, params)
    if not row:
        return default
    return next(iter(row.values()), default)


def _execute(sql: str, params: tuple = ()) -> int:
    conn = _connect()
    cur = conn.execute(sql, params)
    conn.commit()
    return cur.rowcount


def _executemany(sql: str, param_list: list[tuple]) -> None:
    if not param_list:
        return
    conn = _connect()
    conn.executemany(sql, param_list)
    conn.commit()


def _scalar(value: Any) -> Any:
    """Coerce enum members to their plain value for parameter binding."""
    from enum import Enum

    return value.value if isinstance(value, Enum) else value


def _update_doc_json(existing_doc_json: str | None, update: dict, promoted: tuple[str, ...]) -> str:
    """Merge an update dict into the existing JSON blob, skipping promoted columns."""
    existing = {}
    if existing_doc_json:
        try:
            existing = json.loads(existing_doc_json)
        except (json.JSONDecodeError, TypeError):
            existing = {}
    skip = set(promoted)
    for k, v in update.items():
        if k not in skip:
            existing[k] = _scalar(v)
    from server.db.sqlite.sqlite_docs import _json_default

    return json.dumps(existing, default=_json_default)


class SQLiteStorageBackend:
    """StorageBackend backed by a local SQLite file (run-state only)."""

    def __init__(self) -> None:
        _bootstrap_schema()

    # ── Experiment CRUD ───────────────────────────────────────────────────────

    def insert_experiment(self, doc: dict) -> None:
        snapshot = doc.get("vector_store_snapshot")
        snapshot_json: str | None = None
        if snapshot is not None:
            try:
                snapshot_json = json.dumps(snapshot)
            except (TypeError, ValueError):
                snapshot_json = None

        _execute(
            """
            INSERT OR IGNORE INTO experiments
                (experiment_id, experiment_name, status, created_at, started_at, completed_at,
                 vector_store_snapshot, doc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc["experiment_id"],
                doc.get("experiment_name") or "",
                _scalar(doc.get("status") or ExperimentStatus.RUNNING),
                serialize_datetime(doc.get("created_at")),
                serialize_datetime(doc.get("started_at")),
                serialize_datetime(doc.get("completed_at")),
                snapshot_json,
                to_json(doc, EXPERIMENT_COLUMNS),
            ),
        )

    def find_all_experiments(self) -> list[dict]:
        rows = _fetchall("SELECT * FROM experiments ORDER BY created_at DESC NULLS LAST")
        return [experiment_row_to_doc(row) for row in rows]

    def find_experiment_by_id(self, experiment_id: str) -> dict | None:
        row = _fetchone("SELECT * FROM experiments WHERE experiment_id = ?", (experiment_id,))
        return experiment_row_to_doc(row, include_id=True) if row else None

    def find_experiment_with_runs(self, experiment_id: str) -> dict | None:
        row = _fetchone("SELECT * FROM experiments WHERE experiment_id = ?", (experiment_id,))
        if not row:
            return None
        experiment = experiment_row_to_doc(row)
        experiment["runs"] = _runs_ordered_by_creation(experiment_id)
        return experiment

    def update_experiment(self, experiment_id: str, update: dict) -> None:
        # Fetch existing doc blob
        row = _fetchone(
            "SELECT doc, vector_store_snapshot FROM experiments WHERE experiment_id = ?",
            (experiment_id,),
        )
        existing_doc_json = row["doc"] if row else None
        new_doc_json = _update_doc_json(existing_doc_json, update, EXPERIMENT_COLUMNS)

        # Build promoted column updates
        promoted_fields: dict[str, Any] = {}
        if "experiment_name" in update:
            promoted_fields["experiment_name"] = update["experiment_name"]
        if "status" in update:
            promoted_fields["status"] = _scalar(update["status"])
        if "created_at" in update:
            promoted_fields["created_at"] = serialize_datetime(update["created_at"])
        if "started_at" in update:
            promoted_fields["started_at"] = serialize_datetime(update["started_at"])
        if "completed_at" in update:
            promoted_fields["completed_at"] = serialize_datetime(update["completed_at"])
        if "vector_store_snapshot" in update:
            snap = update["vector_store_snapshot"]
            promoted_fields["vector_store_snapshot"] = json.dumps(snap) if snap else None

        if promoted_fields:
            set_clause = ", ".join(f"{k} = ?" for k in promoted_fields)
            set_clause += ", doc = ?"
            params = (*promoted_fields.values(), new_doc_json, experiment_id)
            _execute(
                f"UPDATE experiments SET {set_clause} WHERE experiment_id = ?",  # nosec B608
                params,
            )
        else:
            _execute(
                "UPDATE experiments SET doc = ? WHERE experiment_id = ?",
                (new_doc_json, experiment_id),
            )

    def mark_experiment_cancelled(self, experiment_id: str) -> None:
        self._mark_experiment_terminal(experiment_id, ExperimentStatus.CANCELLED)

    def mark_experiment_paused(self, experiment_id: str) -> None:
        self._mark_experiment_terminal(experiment_id, ExperimentStatus.PAUSED)

    def _mark_experiment_terminal(self, experiment_id: str, status: ExperimentStatus) -> None:
        _execute(
            "UPDATE experiments SET status = ?, completed_at = ? WHERE experiment_id = ?",
            (status.value, serialize_datetime(datetime.now(UTC)), experiment_id),
        )

    def mark_experiment_running(self, experiment_id: str) -> None:
        _execute(
            "UPDATE experiments SET status = ?, completed_at = NULL WHERE experiment_id = ?",
            (ExperimentStatus.RUNNING.value, experiment_id),
        )

    def is_experiment_cancelled(self, experiment_id: str) -> bool:
        status = _fetchvalue(
            "SELECT status FROM experiments WHERE experiment_id = ?", (experiment_id,)
        )
        return bool(status == ExperimentStatus.CANCELLED.value)

    # ── Run status ────────────────────────────────────────────────────────────

    def insert_run_status(self, doc: dict) -> None:
        dims = doc.get("embedding_dimensions")
        _execute(
            """
            INSERT OR IGNORE INTO run_status
                (run_id, experiment_id, phase, created_at, updated_at, embedding_dimensions, doc)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc["run_id"],
                doc["experiment_id"],
                _scalar(doc.get("phase")),
                serialize_datetime(doc.get("created_at")),
                serialize_datetime(doc.get("updated_at")),
                int(dims) if dims is not None else None,
                to_json(doc, RUN_COLUMNS),
            ),
        )

    def update_run_phase(
        self,
        run_id: str,
        *,
        phase: str,
        updated_at: datetime,
        elapsed_ms: int,
        error_message: str | None,
    ) -> None:
        row = _fetchone("SELECT doc FROM run_status WHERE run_id = ?", (run_id,))
        existing_doc_json = row["doc"] if row else None
        new_doc = _update_doc_json(
            existing_doc_json,
            {"elapsed_ms": elapsed_ms, "error_message": error_message},
            RUN_COLUMNS,
        )
        _execute(
            "UPDATE run_status SET phase = ?, updated_at = ?, doc = ? WHERE run_id = ?",
            (_scalar(phase), serialize_datetime(updated_at), new_doc, run_id),
        )

    def find_run_status(self, run_id: str) -> dict | None:
        row = _fetchone("SELECT * FROM run_status WHERE run_id = ?", (run_id,))
        return run_row_to_doc(row) if row else None

    def find_run_statuses(self, experiment_id: str) -> list[dict]:
        rows = _fetchall("SELECT * FROM run_status WHERE experiment_id = ?", (experiment_id,))
        return [run_row_to_doc(row) for row in rows]

    def find_completed_run_sigs(self, experiment_id: str) -> list[dict]:
        return self._runs_in_phase(experiment_id, "complete")

    def count_runs_by_phase(self, experiment_id: str, phase: str) -> int:
        return int(
            _fetchvalue(
                "SELECT count(*) FROM run_status WHERE experiment_id = ? AND phase = ?",
                (experiment_id, _scalar(phase)),
                default=0,
            )
        )

    def find_runs_by_phase(self, experiment_id: str, phase: str, limit: int) -> list[dict]:
        return self._runs_in_phase(experiment_id, phase, limit=limit)

    def _runs_in_phase(
        self, experiment_id: str, phase: str, *, limit: int | None = None
    ) -> list[dict]:
        if limit is not None:
            rows = _fetchall(
                "SELECT * FROM run_status WHERE experiment_id = ? AND phase = ? LIMIT ?",
                (experiment_id, _scalar(phase), limit),
            )
        else:
            rows = _fetchall(
                "SELECT * FROM run_status WHERE experiment_id = ? AND phase = ?",
                (experiment_id, _scalar(phase)),
            )
        return [run_row_to_doc(row) for row in rows]

    def mark_runs_interrupted(
        self,
        run_ids: list[str],
        *,
        updated_at: datetime,
        error_message: str,
    ) -> None:
        if not run_ids:
            return
        for run_id in run_ids:
            row = _fetchone("SELECT doc FROM run_status WHERE run_id = ?", (run_id,))
            existing_doc_json = row["doc"] if row else None
            new_doc = _update_doc_json(
                existing_doc_json,
                {"error_message": error_message},
                RUN_COLUMNS,
            )
            _execute(
                "UPDATE run_status SET phase = 'interrupted', updated_at = ?, doc = ? "
                "WHERE run_id = ?",
                (serialize_datetime(updated_at), new_doc, run_id),
            )

    # ── Results ───────────────────────────────────────────────────────────────

    def insert_result(self, doc: dict) -> None:
        _execute(
            """
            INSERT INTO results (experiment_id, run_id, query_id, query_text, doc)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                doc["experiment_id"],
                doc["run_id"],
                doc["query_id"],
                doc.get("query_text") or "",
                to_json(doc, RESULT_COLUMNS),
            ),
        )

    def find_results_for_experiment(self, experiment_id: str) -> list[dict]:
        rows = _fetchall("SELECT * FROM results WHERE experiment_id = ?", (experiment_id,))
        return [result_row_to_doc(row) for row in rows]

    def find_results_for_run(self, experiment_id: str, run_id: str) -> list[dict]:
        rows = _fetchall(
            "SELECT * FROM results WHERE experiment_id = ? AND run_id = ?",
            (experiment_id, run_id),
        )
        return [result_row_to_doc(row) for row in rows]

    def delete_results_for_experiment(self, experiment_id: str) -> int:
        return _execute("DELETE FROM results WHERE experiment_id = ?", (experiment_id,))

    # ── Cascade delete ────────────────────────────────────────────────────────

    def delete_experiment_data(self, experiment_id: str) -> dict[str, int]:
        logger.info("delete started — experiment %s", experiment_id)
        counts = {
            "chunks": 0,  # SQLite has no chunks (run-state-only)
            "results": self.delete_results_for_experiment(experiment_id),
            "run_status": _execute(
                "DELETE FROM run_status WHERE experiment_id = ?", (experiment_id,)
            ),
            "experiments": _execute(
                "DELETE FROM experiments WHERE experiment_id = ?", (experiment_id,)
            ),
        }
        logger.info("delete complete — experiment %s, counts=%s", experiment_id, counts)
        return counts

    # ── Boot reconciliation ───────────────────────────────────────────────────

    def find_running_experiments(self) -> list[dict]:
        rows = _fetchall(
            "SELECT * FROM experiments WHERE status = ?", (ExperimentStatus.RUNNING.value,)
        )
        return [experiment_row_to_doc(row, include_id=True) for row in rows]

    def update_experiment_reconciled(
        self,
        experiment_id: str,
        *,
        status: object,
        failed_count: int,
        completion_reason: str,
        completed_at: datetime,
    ) -> None:
        self.update_experiment(
            experiment_id,
            {
                "status": status,
                "failed_count": failed_count,
                "completion_reason": completion_reason,
                "completed_at": completed_at,
            },
        )

    # ── Stats / explore ────────────────────────────────────────────────────────

    def load_explore_source(self, experiment_id: str) -> tuple[dict | None, list[dict], list[dict]]:
        row = _fetchone("SELECT * FROM experiments WHERE experiment_id = ?", (experiment_id,))
        if not row:
            return None, [], []
        results = _fetchall("SELECT * FROM results WHERE experiment_id = ?", (experiment_id,))
        runs = _fetchall("SELECT * FROM run_status WHERE experiment_id = ?", (experiment_id,))
        return (
            experiment_row_to_doc(row),
            [result_row_to_doc(r) for r in results],
            [run_row_to_doc(r) for r in runs],
        )

    def list_results_for_experiment(self, experiment_id: str) -> list[dict]:
        rows = _fetchall("SELECT * FROM results WHERE experiment_id = ?", (experiment_id,))
        return [result_row_to_doc(row) for row in rows]

    def get_experiment_db_stats(self, experiment_id: str) -> dict:
        """Per-experiment stats. Chunks are in the vector store, not SQLite — total_chunks=0."""
        logger.debug("computing sqlite db stats — experiment %s", experiment_id)
        exp_row = _fetchone("SELECT * FROM experiments WHERE experiment_id = ?", (experiment_id,))
        experiment = experiment_row_to_doc(exp_row) if exp_row else None

        # Derive embedding_models from run_status docs (no chunks table)
        run_rows = _fetchall("SELECT doc FROM run_status WHERE experiment_id = ?", (experiment_id,))
        embedding_models: list[str] = []
        for rrow in run_rows:
            import json as _json

            rdoc = {}
            try:
                rdoc = _json.loads(rrow["doc"] or "{}")
            except (ValueError, TypeError):
                pass
            model = rdoc.get("embedding_model")
            if model and model not in embedding_models:
                embedding_models.append(model)

        result_row = _fetchone(
            "SELECT count(*) AS total_results, count(DISTINCT query_id) AS unique_queries "
            "FROM results WHERE experiment_id = ?",
            (experiment_id,),
        ) or {"total_results": 0, "unique_queries": 0}

        run_breakdown_rows = _fetchall(
            "SELECT run_id, count(*) AS results FROM results WHERE experiment_id = ? "
            "GROUP BY run_id",
            (experiment_id,),
        )
        run_breakdown = [
            {"run_id": r["run_id"], "chunks": 0, "results": int(r["results"])}
            for r in run_breakdown_rows
        ]

        sweep = (experiment or {}).get("sweep_summary") or {}
        return assemble_experiment_db_stats(
            experiment,
            database_provider=normalize_stats_database_provider(
                sweep.get("database_provider"),
                fallback="sqlite",
            ),
            collection_name="run_status",
            cluster_host=None,
            index_names=[],
            total_chunks=0,
            embedding_models=embedding_models,
            chunking_breakdown={},
            total_results=int(result_row["total_results"] or 0),
            unique_queries=int(result_row["unique_queries"] or 0),
            runs_with_data=len(run_breakdown),
            run_breakdown=run_breakdown,
        )

    def get_vector_db_stats_grouped(self) -> dict:
        """Grouped stats for SQLite run-state store. Chunks are in the vector store."""
        logger.debug("computing sqlite grouped vector db stats")
        experiments = self.find_all_experiments()
        try:
            from server.core.guards.health_check import resolve_storage_mode

            fallback_mode = resolve_storage_mode()
        except Exception:
            fallback_mode = "sqlite-local"

        groups: dict[str, dict] = {}
        for exp in experiments:
            experiment_id = exp.get("experiment_id", "")
            try:
                stats = self.get_experiment_db_stats(experiment_id)
            except Exception:
                logger.warning("sqlite grouped stats — skip experiment %s", experiment_id)
                continue

            storage_mode = resolve_experiment_storage_mode(exp, fallback_mode=fallback_mode)
            group_key = vector_db_group_key(storage_mode, stats.get("cluster_host"))

            if group_key not in groups:
                groups[group_key] = new_vector_db_group(group_key, stats)

            merge_group_totals(groups[group_key], stats)
            groups[group_key]["experiments"].append(
                experiment_summary_row(exp, experiment_id, stats)
            )

        return {"groups": finalize_groups(groups, {})}


def _runs_ordered_by_creation(experiment_id: str) -> list[dict]:
    rows = _fetchall(
        "SELECT * FROM run_status WHERE experiment_id = ? ORDER BY created_at ASC NULLS LAST",
        (experiment_id,),
    )
    return [run_row_to_doc(row) for row in rows]


# ── Singleton accessor ────────────────────────────────────────────────────────

_storage: SQLiteStorageBackend | None = None


def get_sqlite_storage() -> SQLiteStorageBackend:
    global _storage
    if _storage is None:
        _storage = SQLiteStorageBackend()
    return _storage
