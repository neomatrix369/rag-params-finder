"""Tests for Atlas Search index requirement planning and capacity assessment."""

from __future__ import annotations

import pytest

from server.core.model_registry import get_index_name
from server.core.search_index_plan import (
    SearchIndexAssessment,
    SearchIndexSnapshot,
    assess_search_index_readiness,
    format_mismatch_message,
    required_search_indexes,
    validate_vector_index_feasibility,
)
from server.db.indexes import M0_SEARCH_INDEX_LIMIT, TEXT_SEARCH_INDEX_NAME
from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
)
from server.models.enums import ChunkingMethod, RetrievalMethod


def _config(
    *,
    models: list[str] | None = None,
    provider: str = "local",
    retrieval_methods: list[RetrievalMethod] | None = None,
) -> ExperimentConfig:
    return ExperimentConfig(
        experiment_name="test",
        data_paths=["./data"],
        queries_file="./queries.json",
        embedding=EmbeddingConfig(
            provider=provider,  # type: ignore[arg-type]
            models=models or ["all-MiniLM-L6-v2"],
        ),
        chunking=ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
        ),
        retrieval=RetrievalConfig(
            methods=retrieval_methods or [RetrievalMethod.DENSE],
        ),
        execution=ExecutionConfig(),
    )


def _snapshot(
    *,
    chunks_ready: frozenset[str] = frozenset(),
    chunks_building: frozenset[str] = frozenset(),
    cluster_total: int = 0,
    cluster_limit: int = M0_SEARCH_INDEX_LIMIT,
    unknown_count: int = 0,
) -> SearchIndexSnapshot:
    return SearchIndexSnapshot(
        chunks_ready=chunks_ready,
        chunks_building=chunks_building,
        cluster_total=cluster_total,
        cluster_limit=cluster_limit,
        unknown_count=unknown_count,
    )


class TestRequiredSearchIndexes:
    def test_dense_only_local_needs_single_vector_index(self) -> None:
        config = _config(retrieval_methods=[RetrievalMethod.DENSE])
        assert required_search_indexes(config) == frozenset({"vector_index_384"})

    def test_sparse_local_needs_vector_and_text_indexes(self) -> None:
        config = _config(retrieval_methods=[RetrievalMethod.SPARSE])
        assert required_search_indexes(config) == frozenset(
            {"vector_index_384", TEXT_SEARCH_INDEX_NAME}
        )

    def test_hybrid_voyage_needs_vector_and_text_indexes(self) -> None:
        config = _config(
            provider="voyage",
            models=["voyage-3.5-lite"],
            retrieval_methods=[RetrievalMethod.HYBRID],
        )
        assert required_search_indexes(config) == frozenset(
            {"vector_index_1024", TEXT_SEARCH_INDEX_NAME}
        )

    def test_multiple_models_same_dimension_deduplicate_vector_index(self) -> None:
        config = _config(
            models=["all-MiniLM-L6-v2", "all-MiniLM-L6-v2"],
            retrieval_methods=[RetrievalMethod.DENSE, RetrievalMethod.SPARSE],
        )
        required = required_search_indexes(config)
        vector_names = {name for name in required if name.startswith("vector_index_")}
        assert vector_names == {get_index_name("all-MiniLM-L6-v2")}
        assert TEXT_SEARCH_INDEX_NAME in required


class TestValidateVectorIndexFeasibility:
    def test_given_oversized_vector_index_when_validated_then_returns_error(self) -> None:
        message = validate_vector_index_feasibility(frozenset({"vector_index_30522"}))
        assert message is not None
        assert "4096" in message
        assert "vector_index_30522" in message

    def test_given_m0_footprint_when_validated_then_no_error(self) -> None:
        required = frozenset({"vector_index_1024", TEXT_SEARCH_INDEX_NAME})
        assert validate_vector_index_feasibility(required) is None


@pytest.mark.parametrize(
    (
        "scenario",
        "required",
        "snapshot",
        "expect_satisfied",
        "reason_fragment",
    ),
    [
        (
            "all_required_present",
            frozenset({"vector_index_384", TEXT_SEARCH_INDEX_NAME}),
            _snapshot(
                chunks_ready=frozenset({"vector_index_384", TEXT_SEARCH_INDEX_NAME}),
                cluster_total=2,
            ),
            True,
            None,
        ),
        (
            "dense_only_one_index_present",
            frozenset({"vector_index_384"}),
            _snapshot(chunks_ready=frozenset({"vector_index_384"}), cluster_total=1),
            True,
            None,
        ),
        (
            "missing_with_available_slots",
            frozenset({"vector_index_384", TEXT_SEARCH_INDEX_NAME}),
            _snapshot(chunks_ready=frozenset({"vector_index_384"}), cluster_total=1),
            False,
            "missing on chunks",
        ),
        (
            "cluster_full_unknown_indexes_block_creation",
            frozenset({"vector_index_384", TEXT_SEARCH_INDEX_NAME}),
            _snapshot(cluster_total=3, unknown_count=3),
            False,
            "only 0 available",
        ),
        (
            "partial_unknown_still_blocks_when_no_slots",
            frozenset({"vector_index_1024", TEXT_SEARCH_INDEX_NAME}),
            _snapshot(
                chunks_ready=frozenset({"vector_index_1024"}),
                cluster_total=3,
                unknown_count=1,
            ),
            False,
            "only 0 available",
        ),
        (
            "one_slot_left_can_create_text_index",
            frozenset({"vector_index_384", TEXT_SEARCH_INDEX_NAME}),
            _snapshot(
                chunks_ready=frozenset({"vector_index_384"}),
                cluster_total=2,
                unknown_count=1,
            ),
            False,
            "missing on chunks",
        ),
        (
            "required_index_still_building",
            frozenset({"vector_index_384", TEXT_SEARCH_INDEX_NAME}),
            _snapshot(
                chunks_ready=frozenset({"vector_index_384"}),
                chunks_building=frozenset({TEXT_SEARCH_INDEX_NAME}),
                cluster_total=2,
            ),
            False,
            "still building",
        ),
        (
            "empty_cluster_missing_both_indexes_has_slots",
            frozenset({"vector_index_384", TEXT_SEARCH_INDEX_NAME}),
            _snapshot(cluster_total=0),
            False,
            "missing on chunks",
        ),
        (
            "max_m0_footprint_missing_all_but_slots_available",
            frozenset({"vector_index_384", "vector_index_1024", TEXT_SEARCH_INDEX_NAME}),
            _snapshot(cluster_total=0, cluster_limit=3),
            False,
            "missing on chunks",
        ),
        (
            "impossible_requirement_exceeds_tier_limit",
            frozenset({"vector_index_384", "vector_index_1024", TEXT_SEARCH_INDEX_NAME}),
            _snapshot(cluster_total=0, cluster_limit=2),
            False,
            "requires 3 search indexes but this cluster tier allows 2",
        ),
    ],
)
def test_assess_search_index_readiness_scenarios(
    scenario: str,
    required: frozenset[str],
    snapshot: SearchIndexSnapshot,
    expect_satisfied: bool,
    reason_fragment: str | None,
) -> None:
    assessment = assess_search_index_readiness(required=required, snapshot=snapshot)
    assert assessment.is_satisfied is expect_satisfied, scenario
    if reason_fragment:
        assert assessment.failure_reason is not None
        assert reason_fragment in assessment.failure_reason, scenario


def test_format_mismatch_message_includes_reset_hint_for_unknown_indexes() -> None:
    assessment = SearchIndexAssessment(
        required=frozenset({"vector_index_384", TEXT_SEARCH_INDEX_NAME}),
        present_ready=frozenset({"vector_index_384"}),
        present_building=frozenset(),
        missing=frozenset({TEXT_SEARCH_INDEX_NAME}),
        cluster_total=3,
        cluster_limit=3,
        available_slots=0,
        unknown_count=2,
        is_satisfied=False,
        failure_reason="Cannot create required search index(es): text_search_index.",
    )
    message = format_mismatch_message(assessment)
    assert "indexes reset --unknown-only" in message
    assert "text_search_index" in message
