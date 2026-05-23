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
        with patch("server.core.search_index_guard.ensure_indexes") as ensure_mock:
            assessment = validate_experiment_search_indexes(config)

    ensure_mock.assert_called_once()
    assert assessment.is_satisfied
