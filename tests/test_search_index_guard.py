"""Tests for search-index preflight guard (I/O boundary mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from server.core.search_index_guard import (
    collect_search_index_snapshot,
    validate_experiment_search_indexes,
)
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


class TestCollectSearchIndexSnapshot:
    """collect_search_index_snapshot builds a snapshot from live cluster rows.

    Exercises lines 36-53 (snapshot builder) and 125-130 (_is_ready) which
    were unreachable while higher-level tests mocked collect_search_index_snapshot
    directly at the boundary.
    """

    def _make_row(
        self,
        *,
        name: str,
        status: str | bool,
        database: str = "rag_params_finder",
        collection: str = "chunks",
        known: bool = True,
    ) -> dict:
        return {
            "database": database,
            "collection": collection,
            "name": name,
            "index_type": "vectorSearch",
            "status": status,
            "known": known,
        }

    def test_ready_and_building_rows_are_bucketed_correctly(self) -> None:
        """
        Scenario: mix of READY and building rows on the chunks collection.

        Given two index rows — one READY, one PENDING — for the target database/collection
        When collect_search_index_snapshot is called
        Then chunks_ready contains the READY index and chunks_building the PENDING one.
        """
        ### Given
        rows = [
            self._make_row(name="vector_index_384", status="READY"),
            self._make_row(name="text_search_index", status="PENDING"),
        ]
        db_mock = MagicMock()
        db_mock.name = "rag_params_finder"

        ### When
        with patch("server.core.search_index_guard.get_database", return_value=db_mock):
            with patch(
                "server.core.search_index_guard.list_cluster_search_indexes",
                return_value=rows,
            ):
                snapshot = collect_search_index_snapshot()

        ### Then
        assert "vector_index_384" in snapshot.chunks_ready
        assert "text_search_index" in snapshot.chunks_building
        assert snapshot.cluster_total == 2
        assert snapshot.unknown_count == 0

    def test_rows_for_other_databases_are_excluded(self) -> None:
        """
        Scenario: cluster rows from a different database are filtered out.

        Given a row for a different database and one for the target database
        When collect_search_index_snapshot is called
        Then only the target-database row appears in chunks_ready.
        """
        ### Given
        rows = [
            self._make_row(name="vector_index_384", status="READY"),
            self._make_row(
                name="other_index",
                status="READY",
                database="other_db",
                collection="chunks",
            ),
        ]
        db_mock = MagicMock()
        db_mock.name = "rag_params_finder"

        ### When
        with patch("server.core.search_index_guard.get_database", return_value=db_mock):
            with patch(
                "server.core.search_index_guard.list_cluster_search_indexes",
                return_value=rows,
            ):
                snapshot = collect_search_index_snapshot()

        ### Then
        assert snapshot.chunks_ready == frozenset({"vector_index_384"})
        assert snapshot.cluster_total == 2

    def test_lowercase_ready_status_is_treated_as_ready(self) -> None:
        """
        Scenario: Atlas occasionally returns lowercase "ready" status string.

        Given a row whose status is the lowercase string "ready"
        When collect_search_index_snapshot is called
        Then the index is bucketed as ready (defensive upper() fallback, line 129).
        """
        ### Given
        rows = [self._make_row(name="vector_index_384", status="ready")]
        db_mock = MagicMock()
        db_mock.name = "rag_params_finder"

        ### When
        with patch("server.core.search_index_guard.get_database", return_value=db_mock):
            with patch(
                "server.core.search_index_guard.list_cluster_search_indexes",
                return_value=rows,
            ):
                snapshot = collect_search_index_snapshot()

        ### Then
        assert "vector_index_384" in snapshot.chunks_ready

    def test_unknown_rows_increment_unknown_count(self) -> None:
        """
        Scenario: unknown (unrecognised) cluster indexes are counted but not bucketed.

        Given a row marked known=False
        When collect_search_index_snapshot is called
        Then unknown_count reflects the unknown row.
        """
        ### Given
        rows = [self._make_row(name="mystery_index", status="READY", known=False)]
        db_mock = MagicMock()
        db_mock.name = "rag_params_finder"

        ### When
        with patch("server.core.search_index_guard.get_database", return_value=db_mock):
            with patch(
                "server.core.search_index_guard.list_cluster_search_indexes",
                return_value=rows,
            ):
                snapshot = collect_search_index_snapshot()

        ### Then — unknown_count incremented; row still bucketed by readiness
        assert snapshot.unknown_count == 1
        assert "mystery_index" in snapshot.chunks_ready


class TestValidateExperimentSearchIndexesAdditionalPaths:
    """validate_experiment_search_indexes sub-paths not covered by the original four tests."""

    def test_already_satisfied_returns_immediately_without_reconcile(self) -> None:
        """
        Scenario: initial snapshot already satisfies requirements — no repair needed.

        Given a snapshot where all required indexes are already READY
        When validate_experiment_search_indexes is called
        Then it returns the satisfied assessment without calling reconcile or ensure.
        """
        ### Given
        config = _local_sparse_config()
        satisfied = SearchIndexSnapshot(
            chunks_ready=frozenset({"vector_index_384", "text_search_index"}),
            chunks_building=frozenset(),
            cluster_total=2,
            cluster_limit=3,
            unknown_count=0,
        )

        ### When
        with patch(
            "server.core.search_index_guard.collect_search_index_snapshot",
            return_value=satisfied,
        ):
            with patch(
                "server.core.search_index_guard.reconcile_chunks_search_indexes"
            ) as reconcile_mock:
                assessment = validate_experiment_search_indexes(config)

        ### Then
        assert assessment.is_satisfied
        reconcile_mock.assert_not_called()

    def test_reconcile_satisfies_returns_before_ensure(self) -> None:
        """
        Scenario: reconcile frees a slot and re-snapshot shows all indexes ready.

        Given an initial unsatisfied snapshot and a reconcile that drops one index,
        and a re-snapshot that becomes satisfied
        When validate_experiment_search_indexes is called
        Then it returns after reconcile without calling ensure.
        """
        ### Given
        config = _local_sparse_config()
        before = SearchIndexSnapshot(
            chunks_ready=frozenset({"vector_index_384"}),
            chunks_building=frozenset(),
            cluster_total=2,
            cluster_limit=3,
            unknown_count=0,
        )
        after_reconcile = SearchIndexSnapshot(
            chunks_ready=frozenset({"vector_index_384", "text_search_index"}),
            chunks_building=frozenset(),
            cluster_total=2,
            cluster_limit=3,
            unknown_count=0,
        )

        ### When
        with patch(
            "server.core.search_index_guard.collect_search_index_snapshot",
            side_effect=[before, after_reconcile],
        ):
            with patch(
                "server.core.search_index_guard.reconcile_chunks_search_indexes",
                return_value=["stale_index"],
            ):
                with patch(
                    "server.core.search_index_guard.ensure_required_search_indexes"
                ) as ensure_mock:
                    assessment = validate_experiment_search_indexes(config)

        ### Then
        assert assessment.is_satisfied
        ensure_mock.assert_not_called()

    def test_prune_unknown_indexes_when_missing_exceeds_available_slots(self) -> None:
        """
        Scenario: cluster is at capacity with unknowns blocking creation.

        Given missing indexes exceed available slots and pruning unknowns frees space,
        and a re-snapshot after pruning shows indexes are now creatable
        When validate_experiment_search_indexes is called
        Then prune_unknown_search_indexes is called and ensure runs after pruning.
        """
        ### Given
        config = _local_sparse_config()
        # cluster_total == cluster_limit → available_slots = 0 → missing (2) > slots (0)
        full = SearchIndexSnapshot(
            chunks_ready=frozenset(),
            chunks_building=frozenset(),
            cluster_total=3,
            cluster_limit=3,
            unknown_count=2,
        )
        after_prune = SearchIndexSnapshot(
            chunks_ready=frozenset(),
            chunks_building=frozenset(),
            cluster_total=1,
            cluster_limit=3,
            unknown_count=0,
        )
        after_ensure = SearchIndexSnapshot(
            chunks_ready=frozenset({"vector_index_384", "text_search_index"}),
            chunks_building=frozenset(),
            cluster_total=3,
            cluster_limit=3,
            unknown_count=0,
        )

        ### When
        with patch(
            "server.core.search_index_guard.collect_search_index_snapshot",
            side_effect=[full, after_prune, after_ensure],
        ):
            with patch(
                "server.core.search_index_guard.reconcile_chunks_search_indexes",
                return_value=[],
            ):
                with patch(
                    "server.core.search_index_guard.prune_unknown_search_indexes",
                    return_value=["unknown_1", "unknown_2"],
                ) as prune_mock:
                    with patch("server.core.search_index_guard.ensure_required_search_indexes"):
                        assessment = validate_experiment_search_indexes(config)

        ### Then
        prune_mock.assert_called_once()
        assert assessment.is_satisfied

    def test_prune_returns_empty_skips_re_snapshot_and_falls_through_to_ensure(self) -> None:
        """
        Scenario: missing > slots but prune finds nothing to drop — falls through to ensure.

        Given a cluster at capacity and prune_unknown_search_indexes returns []
        When validate_experiment_search_indexes is called
        Then the prune re-snapshot is skipped, can_create remains False, and
        SearchIndexMismatchError is raised (no slots available for creation).
        """
        ### Given
        config = _local_sparse_config()
        full = SearchIndexSnapshot(
            chunks_ready=frozenset(),
            chunks_building=frozenset(),
            cluster_total=3,
            cluster_limit=3,
            unknown_count=0,
        )

        ### When / Then
        with patch(
            "server.core.search_index_guard.collect_search_index_snapshot",
            return_value=full,
        ):
            with patch(
                "server.core.search_index_guard.reconcile_chunks_search_indexes",
                return_value=[],
            ):
                with patch(
                    "server.core.search_index_guard.prune_unknown_search_indexes",
                    return_value=[],
                ):
                    with pytest.raises(SearchIndexMismatchError):
                        validate_experiment_search_indexes(config)

    def test_raises_when_ensure_does_not_satisfy_requirements(self) -> None:
        """
        Scenario: ensure runs but indexes are still not ready afterward.

        Given a snapshot with a slot available but ensure leaves indexes unsatisfied
        When validate_experiment_search_indexes is called
        Then SearchIndexMismatchError is raised with the mismatch message.
        """
        ### Given
        config = _local_sparse_config()
        before = SearchIndexSnapshot(
            chunks_ready=frozenset({"vector_index_384"}),
            chunks_building=frozenset(),
            cluster_total=1,
            cluster_limit=3,
            unknown_count=0,
        )
        # After ensure, text_search_index is still only building (not ready)
        still_building = SearchIndexSnapshot(
            chunks_ready=frozenset({"vector_index_384"}),
            chunks_building=frozenset({"text_search_index"}),
            cluster_total=2,
            cluster_limit=3,
            unknown_count=0,
        )

        ### When / Then
        with patch(
            "server.core.search_index_guard.collect_search_index_snapshot",
            side_effect=[before, still_building],
        ):
            with patch(
                "server.core.search_index_guard.reconcile_chunks_search_indexes",
                return_value=[],
            ):
                with patch("server.core.search_index_guard.ensure_required_search_indexes"):
                    with pytest.raises(SearchIndexMismatchError):
                        validate_experiment_search_indexes(config)


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
