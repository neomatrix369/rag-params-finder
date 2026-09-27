"""Shared fixtures for pipeline/orchestrator sweep unit tests.

Author: Codex
Created: 2026-07-28
Scope: Storage mocks and RunParams/ExperimentConfig builders used by split Slice 16 suites.
"""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
    RunParams,
)
from server.models.enums import ChunkingMethod, RetrievalMethod, RetrieverType


def _fake_storage_backend() -> MagicMock:
    """MagicMock standing in for StorageBackend with iterable-safe defaults.

    Orchestrator call sites iterate over several StorageBackend query results
    (find_run_statuses, find_runs_by_phase, etc.) — a bare MagicMock() is not
    iterable, so every list-returning method defaults to an empty list here.
    Tests override individual method return values as needed.
    """
    storage = MagicMock()
    storage.find_run_statuses.return_value = []
    storage.find_runs_by_phase.return_value = []
    storage.find_completed_run_sigs.return_value = []
    storage.find_results_for_experiment.return_value = []
    storage.find_results_for_run.return_value = []
    storage.count_runs_by_phase.return_value = 0
    storage.is_experiment_cancelled.return_value = False
    return storage


def _run_param() -> RunParams:
    return RunParams(
        database_provider="mongodb",
        embedding_provider="local",
        embedding_model="all-MiniLM-L6-v2",
        chunking_method=ChunkingMethod.RECURSIVE,
        chunk_size=512,
        overlap=50,
        padding=0,
        top_k_initial=20,
        top_k_final=5,
        data_paths=["./data"],
        queries_file="./queries.json",
        retrievers=[{"type": RetrieverType.DENSE.value}],
        retrieval_method=RetrievalMethod.DENSE,
        retrieval_provider="local",
        retrieval_model=None,
    )


def _slice_config(
    parallelism: int,
    on_error: str = "continue",
) -> ExperimentConfig:
    return ExperimentConfig(
        experiment_name="slice-16-test",
        data_paths=["./data"],
        queries_file="./queries.json",
        embedding=EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
        chunking=ChunkingConfig(methods=[ChunkingMethod.RECURSIVE], params=ChunkParams()),
        retrieval=RetrievalConfig(),
        execution=ExecutionConfig(parallelism=parallelism, on_error=on_error),
    )


class FakeRunStateStore:
    """Stateful in-memory ``StorageBackend`` double — run state only.

    Author: Claude (Stream 1)
    Created: 2026-09-27
    Scope: SLICE-49B split-store E2E test infrastructure. Unlike
    ``_fake_storage_backend()`` (a bare MagicMock with iterable-safe
    defaults, used by orchestration-unit tests that stub out storage
    entirely), this fake holds real dict-backed state for experiments,
    run_status rows, and results — the split-store acceptance test polls
    experiment/run status across a real background-thread sweep
    (``schedule_sweep`` -> ``SWEEP_EXECUTOR``), so it needs persistence
    across calls, not just call-count assertions.

    Still implements ``insert_chunks`` / ``delete_chunks_for_experiment``
    (the deprecated 49A chunk methods) so today's wiring — which still
    calls them — has somewhere to write; the split-store test's whole
    point is asserting this store stays *empty* of chunks once the vector
    store owns that data path (Slice 49B GREEN). Pre-GREEN (49A), it
    receives the misrouted chunks, which is exactly the defect being
    proven RED.
    """

    def __init__(self) -> None:
        self.experiments: dict[str, dict] = {}
        self.run_status: dict[str, dict] = {}
        self.results: list[dict] = []
        self.chunks: list[dict] = []  # legacy path — should stay empty post-GREEN

    # ── Experiment CRUD ───────────────────────────────────────────────────────

    def insert_experiment(self, doc: dict) -> None:
        self.experiments[doc["experiment_id"]] = dict(doc)

    def find_all_experiments(self) -> list[dict]:
        return list(self.experiments.values())

    def find_experiment_by_id(self, experiment_id: str) -> dict | None:
        doc = self.experiments.get(experiment_id)
        return dict(doc) if doc is not None else None

    def find_experiment_with_runs(self, experiment_id: str) -> dict | None:
        doc = self.find_experiment_by_id(experiment_id)
        if doc is None:
            return None
        doc["runs"] = self.find_run_statuses(experiment_id)
        return doc

    def update_experiment(self, experiment_id: str, update: dict) -> None:
        self.experiments.setdefault(experiment_id, {}).update(update)

    def mark_experiment_cancelled(self, experiment_id: str) -> None:
        self.update_experiment(experiment_id, {"status": "cancelled"})

    def mark_experiment_paused(self, experiment_id: str) -> None:
        self.update_experiment(experiment_id, {"status": "paused"})

    def mark_experiment_running(self, experiment_id: str) -> None:
        self.update_experiment(experiment_id, {"status": "running", "completed_at": None})

    def is_experiment_cancelled(self, experiment_id: str) -> bool:
        doc = self.experiments.get(experiment_id)
        return bool(doc and doc.get("status") == "cancelled")

    # ── Run status ────────────────────────────────────────────────────────────

    def insert_run_status(self, doc: dict) -> None:
        self.run_status[doc["run_id"]] = dict(doc)

    def update_run_phase(
        self,
        run_id: str,
        *,
        phase: str,
        updated_at: object,
        elapsed_ms: int,
        error_message: str | None,
    ) -> None:
        row = self.run_status.setdefault(run_id, {})
        row.update(
            {
                "phase": phase,
                "updated_at": updated_at,
                "elapsed_ms": elapsed_ms,
                "error_message": error_message,
            }
        )

    def find_run_status(self, run_id: str) -> dict | None:
        row = self.run_status.get(run_id)
        return dict(row) if row is not None else None

    def find_run_statuses(self, experiment_id: str) -> list[dict]:
        return [
            dict(row)
            for row in self.run_status.values()
            if row.get("experiment_id") == experiment_id
        ]

    def find_completed_run_sigs(self, experiment_id: str) -> list[dict]:
        return [
            row for row in self.find_run_statuses(experiment_id) if row.get("phase") == "complete"
        ]

    def count_runs_by_phase(self, experiment_id: str, phase: str) -> int:
        return sum(1 for row in self.find_run_statuses(experiment_id) if row.get("phase") == phase)

    def find_runs_by_phase(self, experiment_id: str, phase: str, limit: int) -> list[dict]:
        return [row for row in self.find_run_statuses(experiment_id) if row.get("phase") == phase][
            :limit
        ]

    def mark_runs_interrupted(
        self,
        run_ids: list[str],
        *,
        updated_at: object,
        error_message: str,
    ) -> None:
        for run_id in run_ids:
            row = self.run_status.setdefault(run_id, {})
            row.update(
                {"phase": "interrupted", "updated_at": updated_at, "error_message": error_message}
            )

    # ── Chunks (legacy 49A path — see class docstring) ─────────────────────────

    def insert_chunks(self, docs: list[dict]) -> None:
        self.chunks.extend(docs)

    def delete_chunks_for_experiment(self, experiment_id: str) -> int:
        before = len(self.chunks)
        self.chunks = [doc for doc in self.chunks if doc.get("experiment_id") != experiment_id]
        return before - len(self.chunks)

    # ── Results ───────────────────────────────────────────────────────────────

    def insert_result(self, doc: dict) -> None:
        self.results.append(dict(doc))

    def find_results_for_experiment(self, experiment_id: str) -> list[dict]:
        return [row for row in self.results if row.get("experiment_id") == experiment_id]

    def find_results_for_run(self, experiment_id: str, run_id: str) -> list[dict]:
        return [
            row
            for row in self.results
            if row.get("experiment_id") == experiment_id and row.get("run_id") == run_id
        ]

    def delete_results_for_experiment(self, experiment_id: str) -> int:
        before = len(self.results)
        self.results = [row for row in self.results if row.get("experiment_id") != experiment_id]
        return before - len(self.results)

    # ── Cascade delete ────────────────────────────────────────────────────────

    def delete_experiment_data(self, experiment_id: str) -> dict[str, int]:
        chunks_deleted = self.delete_chunks_for_experiment(experiment_id)
        results_deleted = self.delete_results_for_experiment(experiment_id)
        run_ids = [
            run_id
            for run_id, row in self.run_status.items()
            if row.get("experiment_id") == experiment_id
        ]
        for run_id in run_ids:
            del self.run_status[run_id]
        experiment_deleted = 1 if self.experiments.pop(experiment_id, None) is not None else 0
        return {
            "experiments": experiment_deleted,
            "run_status": len(run_ids),
            "chunks": chunks_deleted,
            "results": results_deleted,
        }

    # ── Boot reconciliation ───────────────────────────────────────────────────

    def find_running_experiments(self) -> list[dict]:
        return [doc for doc in self.experiments.values() if doc.get("status") == "running"]

    def update_experiment_reconciled(
        self,
        experiment_id: str,
        *,
        status: object,
        failed_count: int,
        completion_reason: str,
        completed_at: object,
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

    # ── Stats / explore ───────────────────────────────────────────────────────

    def load_explore_source(self, experiment_id: str) -> tuple[dict | None, list[dict], list[dict]]:
        return (
            self.find_experiment_by_id(experiment_id),
            self.find_results_for_experiment(experiment_id),
            self.find_run_statuses(experiment_id),
        )

    def list_results_for_experiment(self, experiment_id: str) -> list[dict]:
        return self.find_results_for_experiment(experiment_id)

    def get_experiment_db_stats(self, experiment_id: str) -> dict:
        chunks = [doc for doc in self.chunks if doc.get("experiment_id") == experiment_id]
        return {
            "database_provider": "run-state-fake",
            "collection_name": "chunks",
            "cluster_host": "in-process",
            "total_chunks": len(chunks),
            "unique_documents": len({doc.get("index") for doc in chunks}),
            "embedding_models": sorted({doc.get("embedding_model", "") for doc in chunks}),
            "embedding_dimensions": sorted({len(doc.get("embedding", [])) for doc in chunks}),
            "index_names": [],
            "retrieval_methods": [],
            "chunking_methods": sorted({doc.get("chunk_method", "") for doc in chunks}),
            "chunking_breakdown": {},
            "estimated_storage_mb": 0.0,
            "estimated_embedding_mb": 0.0,
            "estimated_metadata_mb": 0.0,
            "runs_with_data": len({doc.get("run_id") for doc in chunks}),
            "avg_chunks_per_run": 0.0,
            "total_results": len(self.find_results_for_experiment(experiment_id)),
            "unique_queries": len(
                {row.get("query_id") for row in self.find_results_for_experiment(experiment_id)}
            ),
            "run_breakdown": {},
        }

    def get_vector_db_stats_grouped(self) -> dict:
        return {
            "groups": [{"database_provider": "run-state-fake", "total_chunks": len(self.chunks)}]
        }


def _fake_run_state_store() -> FakeRunStateStore:
    """Stateful run-state ``StorageBackend`` double — see ``FakeRunStateStore``."""
    return FakeRunStateStore()


@contextmanager
def _patch_backends(
    *,
    storage: Any,
    vector_store: Any,
    retriever: Any = None,
):
    """Patch ``get_storage_backend`` / ``get_vector_store`` / ``get_retriever_backend``
    together, everywhere today's call sites import them directly.

    Author: Claude (Stream 1)
    Created: 2026-09-27
    Scope: SLICE-49B "Test infrastructure" — the ~11 test files that patch
    the storage/retriever factories one call site at a time migrate to this
    single helper in Slice 49B Stream 2. It patches both the pre-49B chunk
    path (``get_storage_backend().insert_chunks(...)``, still wired today)
    and the post-49B path (``get_vector_store()``), so the same test fixture
    works unmodified whether it is exercising today's (defective) wiring or
    Slice 49B's rewired call sites — only the *assertions* about which
    fake received the chunks need to differ, not the patch targets.

    Args:
        storage: a ``StorageBackend`` double (e.g. ``FakeRunStateStore()``)
            for run-state calls.
        vector_store: a ``VectorStore`` double (e.g. ``MemoryVectorStore()``)
            for chunk write/delete/stats/index-planning calls.
        retriever: optional explicit ``RetrieverBackend`` double; defaults to
            ``vector_store.retriever()`` (matches
            ``get_retriever_backend()``'s real delegation contract).
    """
    retriever_double = retriever if retriever is not None else vector_store.retriever()
    storage_call_sites = [
        "server.db.ports.store_factory.get_storage_backend",
        "server.core.pipeline.orchestrator.get_storage_backend",
        "server.api.experiments_shared.get_storage_backend",
    ]
    retriever_call_sites = [
        "server.db.ports.store_factory.get_retriever_backend",
        "server.core.pipeline.search.get_retriever_backend",
    ]
    with ExitStack() as stack:
        for target in storage_call_sites:
            stack.enter_context(patch(target, return_value=storage))
        stack.enter_context(
            patch("server.db.ports.store_factory.get_vector_store", return_value=vector_store)
        )
        for target in retriever_call_sites:
            stack.enter_context(patch(target, return_value=retriever_double))
        yield
