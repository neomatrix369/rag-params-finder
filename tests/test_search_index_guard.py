"""Tests for search-index preflight guard (I/O boundary mocked)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from server.core.search_index_guard import validate_experiment_search_indexes
from server.core.search_index_plan import SearchIndexMismatchError, SearchIndexSnapshot
from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
)
from server.models.enums import ChunkingMethod, RetrievalMethod


def _local_sparse_config() -> ExperimentConfig:
    return ExperimentConfig(
        experiment_name="guard-test",
        data_paths=["./data"],
        queries_file="./queries.json",
        embedding=EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
        chunking=ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
        ),
        retrieval=RetrievalConfig(methods=[RetrievalMethod.SPARSE]),
        execution=ExecutionConfig(),
    )


def test_validate_raises_when_indexes_missing_and_no_slots() -> None:
    config = _local_sparse_config()
    blocked = SearchIndexSnapshot(
        chunks_ready=frozenset(),
        chunks_building=frozenset(),
        cluster_total=3,
        cluster_limit=3,
        unknown_count=3,
    )

    with patch(
        "server.core.search_index_guard.collect_search_index_snapshot",
        return_value=blocked,
    ):
        with pytest.raises(SearchIndexMismatchError) as exc_info:
            validate_experiment_search_indexes(config, attempt_ensure=False)

    assert "text_search_index" in str(exc_info.value)
    assert "only 0 available" in str(exc_info.value)


def test_validate_attempts_ensure_when_slots_available() -> None:
    config = _local_sparse_config()
    before = SearchIndexSnapshot(
        chunks_ready=frozenset({"vector_index_384"}),
        chunks_building=frozenset(),
        cluster_total=1,
        cluster_limit=3,
        unknown_count=0,
    )
    after = SearchIndexSnapshot(
        chunks_ready=frozenset({"vector_index_384", "text_search_index"}),
        chunks_building=frozenset(),
        cluster_total=2,
        cluster_limit=3,
        unknown_count=0,
    )

    with patch(
        "server.core.search_index_guard.collect_search_index_snapshot",
        side_effect=[before, after],
    ):
        with patch(
            "server.core.search_index_guard.reconcile_chunks_search_indexes",
            return_value=[],
        ):
            with patch(
                "server.core.search_index_guard.ensure_required_search_indexes"
            ) as ensure_mock:
                assessment = validate_experiment_search_indexes(config)

    ensure_mock.assert_called_once_with(frozenset({"vector_index_384", "text_search_index"}))
    assert assessment.is_satisfied


def test_validate_reconciles_surplus_indexes_before_ensure() -> None:
    """Auto-drop surplus vector_index_384 so vector_index_1024 can be created."""
    config = ExperimentConfig(
        experiment_name="sie-reconcile",
        data_paths=["./data"],
        queries_file="./queries.json",
        embedding=EmbeddingConfig(provider="sie", models=["bge-m3"]),
        chunking=ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
        ),
        retrieval=RetrievalConfig(methods=[RetrievalMethod.SPARSE]),
        execution=ExecutionConfig(),
    )
    blocked = SearchIndexSnapshot(
        chunks_ready=frozenset({"vector_index_384", "text_search_index"}),
        chunks_building=frozenset(),
        cluster_total=3,
        cluster_limit=3,
        unknown_count=1,
    )
    after_reconcile = SearchIndexSnapshot(
        chunks_ready=frozenset({"text_search_index"}),
        chunks_building=frozenset(),
        cluster_total=2,
        cluster_limit=3,
        unknown_count=1,
    )
    after_ensure = SearchIndexSnapshot(
        chunks_ready=frozenset({"vector_index_1024", "text_search_index"}),
        chunks_building=frozenset(),
        cluster_total=2,
        cluster_limit=3,
        unknown_count=1,
    )

    with patch(
        "server.core.search_index_guard.collect_search_index_snapshot",
        side_effect=[blocked, after_reconcile, after_ensure],
    ):
        with patch(
            "server.core.search_index_guard.reconcile_chunks_search_indexes",
            return_value=["vector_index_384 (surplus)"],
        ) as reconcile_mock:
            with patch(
                "server.core.search_index_guard.ensure_required_search_indexes"
            ) as ensure_mock:
                assessment = validate_experiment_search_indexes(config)

    reconcile_mock.assert_called_once()
    ensure_mock.assert_called_once()
    assert assessment.is_satisfied


def test_validate_rejects_splade_before_reconcile() -> None:
    config = ExperimentConfig(
        experiment_name="splade-blocked",
        data_paths=["./data"],
        queries_file="./queries.json",
        embedding=EmbeddingConfig(provider="sie", models=["splade-v3"]),
        chunking=ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
        ),
        retrieval=RetrievalConfig(methods=[RetrievalMethod.DENSE]),
        execution=ExecutionConfig(),
    )

    with pytest.raises(SearchIndexMismatchError, match="4096"):
        validate_experiment_search_indexes(config, attempt_ensure=False)
