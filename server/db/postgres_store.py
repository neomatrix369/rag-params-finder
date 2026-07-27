"""Postgres/pgvector adapter implementing StorageBackend.

All psycopg-specific CRUD lives here; orchestrator, experiments API, and startup
reconciliation import from store_factory, not from this module directly.

Document ↔ row mapping lives in ``server.db.postgres_docs`` and stats/explore
queries in ``server.db.postgres_stats``, mirroring the Mongo adapter's split.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pgvector import Vector
from psycopg import sql

from server.core.retrieval import retriever_postgres
from server.db import postgres_stats
from server.db.postgres import execute, execute_many, fetch_all, fetch_one, fetch_value
from server.db.postgres_docs import (
    EXPERIMENT_COLUMNS,
    RESULT_COLUMNS,
    RUN_COLUMNS,
    experiment_row_to_doc,
    result_row_to_doc,
    run_row_to_doc,
    to_jsonb,
    vector_column_for,
)
from server.models.enums import ExperimentStatus, RetrievalMethod
from server.models.results import SearchResult
from server.utils.logger import get_logger

logger = get_logger(__name__)

_CHUNK_COLUMNS = (
    "chunk_id",
    "experiment_id",
    "run_id",
    "text",
    "chunk_index",
    "embedding_model",
    "chunk_method",
    "chunk_size",
    "overlap",
    "padding",
)


def _scalar(value: Any) -> Any:
    """Coerce enum members to their plain value for parameter binding."""
    return value.value if isinstance(value, Enum) else value


def _update_statement(table: str, key_column: str, promoted: tuple[str, ...], update: dict):
    """Build an UPDATE that writes promoted columns and merges the rest into doc."""
    assignments: list[sql.Composable] = [
        sql.SQL("{} = %s").format(sql.Identifier(column))
        for column in promoted
        if column != key_column and column in update
    ]
    params: list[Any] = [
        _scalar(update[column]) for column in promoted if column != key_column and column in update
    ]
    assignments.append(sql.SQL("doc = doc || %s"))
    params.append(to_jsonb(update, promoted))
    statement = sql.SQL("UPDATE {} SET {} WHERE {} = %s").format(
        sql.Identifier(table),
        sql.SQL(", ").join(assignments),
        sql.Identifier(key_column),
    )
    return statement, params


def _chunk_insert_statement(vector_column: str):
    columns = [*_CHUNK_COLUMNS, vector_column]
    return sql.SQL("INSERT INTO chunks ({}) VALUES ({})").format(
        sql.SQL(", ").join(sql.Identifier(c) for c in columns),
        sql.SQL(", ").join(sql.Placeholder() * len(columns)),
    )


def _chunk_params(doc: dict) -> list[Any]:
    return [
        doc["chunk_id"],
        doc["experiment_id"],
        doc["run_id"],
        doc["text"],
        doc["index"],
        doc["embedding_model"],
        doc["chunk_method"],
        doc.get("chunk_size"),
        doc.get("overlap"),
        doc.get("padding"),
        Vector(doc["embedding"]),
    ]


class PostgresStorageBackend:
    """StorageBackend backed by Supabase (hosted Postgres) or local pgvector."""

    # ── Experiment CRUD ───────────────────────────────────────────────────────

    def insert_experiment(self, doc: dict) -> None:
        execute(
            """
            INSERT INTO experiments
                (experiment_id, experiment_name, status, created_at, started_at, completed_at, doc)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                doc["experiment_id"],
                doc.get("experiment_name") or "",
                _scalar(doc.get("status") or ExperimentStatus.RUNNING),
                doc.get("created_at"),
                doc.get("started_at"),
                doc.get("completed_at"),
                to_jsonb(doc, EXPERIMENT_COLUMNS),
            ),
        )

    def find_all_experiments(self) -> list[dict]:
        rows = fetch_all("SELECT * FROM experiments ORDER BY created_at DESC NULLS LAST")
        return [experiment_row_to_doc(row) for row in rows]

    def find_experiment_by_id(self, experiment_id: str) -> dict | None:
        row = fetch_one("SELECT * FROM experiments WHERE experiment_id = %s", (experiment_id,))
        return experiment_row_to_doc(row, include_id=True) if row else None

    def find_experiment_with_runs(self, experiment_id: str) -> dict | None:
        row = fetch_one("SELECT * FROM experiments WHERE experiment_id = %s", (experiment_id,))
        if not row:
            return None
        experiment = experiment_row_to_doc(row)
        experiment["runs"] = self._runs_ordered_by_creation(experiment_id)
        return experiment

    def _runs_ordered_by_creation(self, experiment_id: str) -> list[dict]:
        rows = fetch_all(
            "SELECT * FROM run_status WHERE experiment_id = %s ORDER BY created_at ASC NULLS LAST",
            (experiment_id,),
        )
        return [run_row_to_doc(row) for row in rows]

    def update_experiment(self, experiment_id: str, update: dict) -> None:
        statement, params = _update_statement(
            "experiments", "experiment_id", EXPERIMENT_COLUMNS, update
        )
        execute(statement, [*params, experiment_id])

    def mark_experiment_cancelled(self, experiment_id: str) -> None:
        self._mark_experiment_terminal(experiment_id, ExperimentStatus.CANCELLED)

    def mark_experiment_paused(self, experiment_id: str) -> None:
        self._mark_experiment_terminal(experiment_id, ExperimentStatus.PAUSED)

    def _mark_experiment_terminal(self, experiment_id: str, status: ExperimentStatus) -> None:
        execute(
            "UPDATE experiments SET status = %s, completed_at = %s WHERE experiment_id = %s",
            (status.value, datetime.now(UTC), experiment_id),
        )

    def mark_experiment_running(self, experiment_id: str) -> None:
        execute(
            "UPDATE experiments SET status = %s, completed_at = NULL WHERE experiment_id = %s",
            (ExperimentStatus.RUNNING.value, experiment_id),
        )

    def is_experiment_cancelled(self, experiment_id: str) -> bool:
        status = fetch_value(
            "SELECT status FROM experiments WHERE experiment_id = %s", (experiment_id,)
        )
        return bool(status == ExperimentStatus.CANCELLED.value)

    # ── Run status ────────────────────────────────────────────────────────────

    def insert_run_status(self, doc: dict) -> None:
        execute(
            """
            INSERT INTO run_status (run_id, experiment_id, phase, created_at, updated_at, doc)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                doc["run_id"],
                doc["experiment_id"],
                _scalar(doc.get("phase")),
                doc.get("created_at"),
                doc.get("updated_at"),
                to_jsonb(doc, RUN_COLUMNS),
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
        execute(
            """
            UPDATE run_status
               SET phase = %s,
                   updated_at = %s,
                   doc = doc || jsonb_build_object('elapsed_ms', %s::int,
                                                   'error_message', %s::text)
             WHERE run_id = %s
            """,
            (_scalar(phase), updated_at, elapsed_ms, error_message, run_id),
        )

    def find_run_status(self, run_id: str) -> dict | None:
        row = fetch_one("SELECT * FROM run_status WHERE run_id = %s", (run_id,))
        return run_row_to_doc(row) if row else None

    def find_run_statuses(self, experiment_id: str) -> list[dict]:
        rows = fetch_all("SELECT * FROM run_status WHERE experiment_id = %s", (experiment_id,))
        return [run_row_to_doc(row) for row in rows]

    def find_completed_run_sigs(self, experiment_id: str) -> list[dict]:
        return self._runs_in_phase(experiment_id, "complete")

    def count_runs_by_phase(self, experiment_id: str, phase: str) -> int:
        return int(
            fetch_value(
                "SELECT count(*) FROM run_status WHERE experiment_id = %s AND phase = %s",
                (experiment_id, _scalar(phase)),
                default=0,
            )
        )

    def find_runs_by_phase(self, experiment_id: str, phase: str, limit: int) -> list[dict]:
        return self._runs_in_phase(experiment_id, phase, limit=limit)

    def _runs_in_phase(
        self, experiment_id: str, phase: str, *, limit: int | None = None
    ) -> list[dict]:
        rows = fetch_all(
            "SELECT * FROM run_status WHERE experiment_id = %s AND phase = %s LIMIT %s",
            (experiment_id, _scalar(phase), limit),
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
        execute(
            """
            UPDATE run_status
               SET phase = 'interrupted',
                   updated_at = %s,
                   doc = doc || jsonb_build_object('error_message', %s::text)
             WHERE run_id = ANY(%s)
            """,
            (updated_at, error_message, run_ids),
        )

    # ── Chunks ────────────────────────────────────────────────────────────────

    def insert_chunks(self, docs: list[dict]) -> None:
        """Insert chunks, routing each embedding to the column for its dimension."""
        if not docs:
            return
        by_column: dict[str, list[dict]] = defaultdict(list)
        for doc in docs:
            by_column[vector_column_for(len(doc["embedding"]))].append(doc)
        for vector_column, group in by_column.items():
            execute_many(
                _chunk_insert_statement(vector_column),
                [_chunk_params(doc) for doc in group],
            )

    def delete_chunks_for_experiment(self, experiment_id: str) -> int:
        return execute("DELETE FROM chunks WHERE experiment_id = %s", (experiment_id,))

    # ── Results ───────────────────────────────────────────────────────────────

    def insert_result(self, doc: dict) -> None:
        execute(
            """
            INSERT INTO results (experiment_id, run_id, query_id, query_text, doc)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                doc["experiment_id"],
                doc["run_id"],
                doc["query_id"],
                doc.get("query_text") or "",
                to_jsonb(doc, RESULT_COLUMNS),
            ),
        )

    def find_results_for_experiment(self, experiment_id: str) -> list[dict]:
        rows = fetch_all("SELECT * FROM results WHERE experiment_id = %s", (experiment_id,))
        return [result_row_to_doc(row) for row in rows]

    def find_results_for_run(self, experiment_id: str, run_id: str) -> list[dict]:
        rows = fetch_all(
            "SELECT * FROM results WHERE experiment_id = %s AND run_id = %s",
            (experiment_id, run_id),
        )
        return [result_row_to_doc(row) for row in rows]

    def delete_results_for_experiment(self, experiment_id: str) -> int:
        return execute("DELETE FROM results WHERE experiment_id = %s", (experiment_id,))

    # ── Cascade delete ────────────────────────────────────────────────────────

    def delete_experiment_data(self, experiment_id: str) -> dict[str, int]:
        """Delete an experiment and its children, reporting per-table counts.

        Children are removed explicitly rather than relying on the FK cascade so
        the response carries the same counts the Mongo adapter reports.
        """
        logger.info("delete started — experiment %s", experiment_id)
        counts = {
            "chunks": self.delete_chunks_for_experiment(experiment_id),
            "results": self.delete_results_for_experiment(experiment_id),
            "run_status": execute(
                "DELETE FROM run_status WHERE experiment_id = %s", (experiment_id,)
            ),
            "experiments": execute(
                "DELETE FROM experiments WHERE experiment_id = %s", (experiment_id,)
            ),
        }
        logger.info("delete complete — experiment %s, counts=%s", experiment_id, counts)
        return counts

    # ── Boot reconciliation ───────────────────────────────────────────────────

    def find_running_experiments(self) -> list[dict]:
        rows = fetch_all(
            "SELECT * FROM experiments WHERE status = %s", (ExperimentStatus.RUNNING.value,)
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

    # ── Stats / explore (delegated to postgres_stats) ─────────────────────────

    def load_explore_source(self, experiment_id: str) -> tuple[dict | None, list[dict], list[dict]]:
        return postgres_stats.load_explore_source(experiment_id)

    def list_results_for_experiment(self, experiment_id: str) -> list[dict]:
        return postgres_stats.list_results_for_experiment(experiment_id)

    def get_experiment_db_stats(self, experiment_id: str) -> dict:
        return postgres_stats.get_experiment_db_stats(experiment_id)

    def get_vector_db_stats_grouped(self) -> dict:
        return postgres_stats.get_vector_db_stats_grouped(self.find_all_experiments)


class PostgresRetrieverBackend:
    """RetrieverBackend backed by pgvector (Supabase / local Postgres)."""

    def search(
        self,
        method: RetrievalMethod,
        query_text: str,
        experiment_id: str,
        embedding_model: str,
        run_id: str,
        top_k: int,
        query_embedding: list[float] | None,
    ) -> list[SearchResult]:
        return retriever_postgres.search(
            method,
            query_text,
            experiment_id,
            embedding_model,
            run_id,
            top_k,
            query_embedding,
        )


# ── Singleton accessors ───────────────────────────────────────────────────────
_storage: PostgresStorageBackend | None = None
_retriever: PostgresRetrieverBackend | None = None


def get_postgres_storage() -> PostgresStorageBackend:
    global _storage
    if _storage is None:
        _storage = PostgresStorageBackend()
    return _storage


def get_postgres_retriever() -> PostgresRetrieverBackend:
    global _retriever
    if _retriever is None:
        _retriever = PostgresRetrieverBackend()
    return _retriever
