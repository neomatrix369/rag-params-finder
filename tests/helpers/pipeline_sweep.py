"""Shared fixtures for pipeline/orchestrator sweep unit tests.

Author: Codex
Created: 2026-07-28
Scope: Storage mocks and RunParams/ExperimentConfig builders used by split Slice 16 suites.
"""

from __future__ import annotations

from unittest.mock import MagicMock

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
