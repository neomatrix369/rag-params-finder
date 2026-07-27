"""Close scoped-coverage gaps so BE can share FE's 95/90/95/95 floors (#141/#142).

Author: Cursor agent
Created: 2026-07-27
Scope: results_analyzer, search_index_guard, models.config — missing lines/branches
"""

from __future__ import annotations

import warnings
from unittest.mock import patch

import pytest

from server.core.results_analyzer import analyze_results
from server.core.search_index_guard import (
    collect_postgres_index_snapshot,
    postgres_vector_extension_present,
    validate_experiment_search_indexes,
)
from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
    normalize_database_provider,
)
from server.models.enums import ChunkingMethod, RetrievalMethod


def test_given_rerank_score_when_analyze_then_rerank_path_is_used() -> None:
    """
    Scenario: _effective_score prefers rerank_score when present.
    Slice: 44 — BE coverage floor parity
    """
    # -- Given --
    run_statuses = [
        {
            "run_id": "r1",
            "embedding_model": "all-MiniLM-L6-v2",
            "chunking_method": "recursive",
            "chunk_size": 512,
            "overlap": 50,
            "retrieval_method": "dense",
            "retrievers": [{"type": "dense"}],
        }
    ]
    query_results = [
        {
            "run_id": "r1",
            "query_text": "q1",
            "results": [{"rerank_score": 0.9, "dense_score": 0.1, "chunk": {"text": "a"}}],
        }
    ]

    # -- When --
    out = analyze_results(query_results, run_statuses)

    # -- Then --
    assert out["query_count"] == 1
    assert out["best_params"] is not None


def test_given_selected_query_when_analyze_then_other_queries_are_filtered() -> None:
    """
    Scenario: selected_query filters query_results before aggregation.
    Slice: 44 — BE coverage floor parity
    """
    # -- Given --
    run_statuses = [
        {
            "run_id": "r1",
            "embedding_model": "m",
            "chunking_method": "recursive",
            "chunk_size": 256,
            "overlap": 0,
            "retrieval_method": "dense",
            "retrievers": [{"type": "dense"}],
        }
    ]
    query_results = [
        {
            "run_id": "r1",
            "query_text": "keep",
            "results": [{"dense_score": 1.0, "chunk": {"text": "a"}}],
        },
        {
            "run_id": "r1",
            "query_text": "drop",
            "results": [{"dense_score": 0.2, "chunk": {"text": "b"}}],
        },
    ]

    # -- When --
    out = analyze_results(query_results, run_statuses, selected_query="keep")

    # -- Then --
    assert out["queries"] == ["keep"]
    assert out["query_count"] == 1


def test_given_empty_inputs_when_analyze_then_best_params_is_none() -> None:
    """
    Scenario: Empty explorer input yields no best_params (tied_count branch skipped).
    Slice: 44 — BE coverage floor parity
    """
    # -- Given / When --
    out = analyze_results([], [])

    # -- Then --
    assert out["best_params"] is None
    assert out["ranked_configs"] == []


def test_given_postgres_extension_row_when_present_then_true() -> None:
    """
    Scenario: postgres_vector_extension_present reads pg_extension via fetch_one.
    Slice: 44 — BE coverage floor parity
    """
    # -- Given --
    with patch("server.core.guards.search_index_guard.fetch_one", return_value={"ok": 1}):
        # -- When / Then --
        assert postgres_vector_extension_present() is True


def test_given_empty_required_when_collect_postgres_snapshot_then_empty_ready() -> None:
    """
    Scenario: collect_postgres_index_snapshot short-circuits when required is empty.
    Slice: 44 — BE coverage floor parity
    """
    # -- Given / When --
    snap = collect_postgres_index_snapshot(frozenset())

    # -- Then --
    assert snap.chunks_ready == frozenset()
    assert snap.cluster_total == 0


def test_given_required_indexes_when_collect_postgres_snapshot_then_present_set() -> None:
    """
    Scenario: Non-empty required set queries pg_indexes and builds present frozenset.
    Slice: 44 — BE coverage floor parity
    """
    # -- Given --
    required = frozenset({"chunks_embedding_384_hnsw"})
    with patch(
        "server.core.guards.search_index_guard.fetch_all",
        return_value=[{"indexname": "chunks_embedding_384_hnsw"}],
    ):
        # -- When --
        snap = collect_postgres_index_snapshot(required)

    # -- Then --
    assert "chunks_embedding_384_hnsw" in snap.chunks_ready


def test_given_unknown_storage_backend_when_validate_then_not_applicable() -> None:
    """
    Scenario: Unknown storage_backend skips Atlas/Postgres preflight.
    Slice: 44 — BE coverage floor parity
    """
    # -- Given --
    config = ExperimentConfig(
        experiment_name="x",
        data_paths=["./d"],
        queries_file="./q.json",
        embedding=EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
        chunking=ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
        ),
        retrieval=RetrievalConfig(methods=[RetrievalMethod.DENSE]),
        execution=ExecutionConfig(),
    )
    with patch("server.settings.settings.storage_backend", "sqlite"):
        # -- When --
        assessment = validate_experiment_search_indexes(config)

    # -- Then --
    assert assessment.is_satisfied


def test_normalize_database_provider_aliases() -> None:
    """
    Scenario: supabase→postgres and mongo→mongodb aliases.
    Slice: 44 — BE coverage floor parity
    """
    # -- Given / When / Then --
    assert normalize_database_provider("supabase") == "postgres"
    assert normalize_database_provider("mongo") == "mongodb"
    assert normalize_database_provider("MongoDB") == "mongodb"


def test_retrieval_config_rejects_unknown_reranker_model() -> None:
    """
    Scenario: Old-format retrieval_model must be a known reranker.
    Slice: 44 — BE coverage floor parity
    """
    # -- Given / When / Then --
    with pytest.raises(ValueError, match="Unknown reranker model"):
        RetrievalConfig(retrieval_model="not-a-real-reranker")


def test_experiment_config_warns_on_supabase_database_provider() -> None:
    """
    Scenario: database_provider supabase normalizes and emits DeprecationWarning.
    Slice: 44 — BE coverage floor parity
    """
    # -- Given / When / Then --
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cfg = ExperimentConfig(
            experiment_name="x",
            data_paths=["./d"],
            queries_file="./q.json",
            database_provider="supabase",  # type: ignore[arg-type]
            embedding=EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
            chunking=ChunkingConfig(
                methods=[ChunkingMethod.RECURSIVE],
                params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
            ),
            retrieval=RetrievalConfig(methods=[RetrievalMethod.DENSE]),
        )
    assert cfg.database_provider == "postgres"
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)


def test_bayesian_requires_single_padding() -> None:
    """
    Scenario: Bayesian search rejects multi-value paddings.
    Slice: 44 — BE coverage floor parity
    """
    # -- Given / When / Then --
    with pytest.raises(ValueError, match="paddings"):
        ExperimentConfig(
            experiment_name="x",
            data_paths=["./d"],
            queries_file="./q.json",
            embedding=EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
            chunking=ChunkingConfig(
                methods=[ChunkingMethod.RECURSIVE],
                params=ChunkParams(chunk_sizes=[256, 512], overlaps=[0, 50], paddings=[0, 10]),
            ),
            retrieval=RetrievalConfig(methods=[RetrievalMethod.DENSE]),
            execution=ExecutionConfig(search_strategy="bayesian"),
        )
