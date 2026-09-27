"""Tests for the dual-store preflight entry point — Slice 49B (site 10).

Author: Claude (crafter, slice-49b-vector-store-data-path-rewire)
Created: 2026-09-27
Scope: SLICE-49B-VECTOR-STORE-DATA-PATH-REWIRE.md "Spec (GWT)":
  - "Vector store unreachable" — preflight fails on the vector store and the
    run-state store's health is never consulted (DECISIONS #253 step order).
  - "A vector store without an index plan fails preflight closed" — the
    `preflight_not_applicable()` skip path is gone (walkthrough G3); an
    adapter that raises on `plan_indexes` fails 422 naming the store,
    instead of passing silently.
  - `preflight_stores()` wiring: single-store mode never reaches the
    run-state step (characterization); split mode reaches it once the
    vector step is satisfied.

These exercise `server.core.guards.search_index_guard.validate_experiment_search_indexes`
(vector step) and `preflight_stores` (both steps) directly, with the vector
store's factory patched to a small in-file double — no live Mongo/Postgres/
Elasticsearch involved.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from server.core.guards.search_index_guard import (
    SearchIndexMismatchError,
    preflight_stores,
    validate_experiment_search_indexes,
)
from server.db.ports.vector_store import VectorCapabilities
from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
    RetrieverConfig,
)
from server.models.enums import ChunkingMethod, RetrieverType

_EMPTY_CAPABILITIES = VectorCapabilities(
    retrieval_methods=frozenset({RetrieverType.DENSE}),  # type: ignore[arg-type]
    similarity_metrics=frozenset(),
    index_types=frozenset(),
    supported_embedding_dims=frozenset(),
    supports_metadata_filters=False,
    can_host_run_state=False,
)


def _config() -> ExperimentConfig:
    return ExperimentConfig(
        experiment_name="dual-store-preflight-test",
        data_paths=["./data"],
        queries_file="./queries.json",
        embedding=EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
        chunking=ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
        ),
        retrieval=RetrievalConfig(retrievers=[RetrieverConfig(type=RetrieverType.DENSE)]),
        execution=ExecutionConfig(),
    )


class _NoPlanVectorStore:
    """Registered-but-unimplemented vector store — publishes no index plan."""

    def health_check(self) -> bool:
        return True

    def plan_indexes(self, config: ExperimentConfig) -> None:
        raise NotImplementedError("no index plan published for this store")

    def ensure_indexes(self) -> None:
        raise AssertionError("ensure_indexes should not be reached — plan_indexes fails closed")

    def capabilities(self) -> VectorCapabilities:
        raise AssertionError("capabilities should not be reached — plan_indexes fails closed")


class _UnreachableVectorStore:
    """A configured but unreachable vector store — health_check() is False."""

    def health_check(self) -> bool:
        return False

    def plan_indexes(self, config: ExperimentConfig) -> None:
        raise AssertionError("plan_indexes should not be reached — health_check failed first")

    def ensure_indexes(self) -> None:
        raise AssertionError("ensure_indexes should not be reached — health_check failed first")

    def capabilities(self) -> VectorCapabilities:
        raise AssertionError("capabilities should not be reached — health_check failed first")


class TestGenericVectorStorePreflightFailsClosedShould:
    """Scenario: A vector store without an index plan fails preflight closed."""

    def test_given_registered_store_with_no_plan_when_preflight_runs_then_raises_naming_store(
        self,
    ) -> None:
        """
        Given a registered vector store that publishes no index plan for the
              submitted config (VECTOR_STORE_BACKEND=noplanvec, unregistered
              in the mongodb/postgres registry so it dispatches generically),
        When a sweep's preflight runs (validate_experiment_search_indexes),
        Then it raises HTTP-422-equivalent SearchIndexMismatchError naming
             the store and "no index plan" — fail closed, not pass silently.
        """
        ### Given / When / Then
        with (
            patch("server.settings.settings.storage_backend", "postgres"),
            patch("server.settings.settings.vector_store_backend", "noplanvec"),
            patch(
                "server.db.ports.store_factory.get_vector_store",
                return_value=_NoPlanVectorStore(),
            ),
            pytest.raises(SearchIndexMismatchError, match="no index plan"),
        ):
            validate_experiment_search_indexes(_config())


class TestVectorStoreUnreachablePreflightShould:
    """Scenario: Vector store unreachable."""

    def test_given_vector_store_unreachable_when_preflight_stores_then_stops_before_run_state(
        self,
    ) -> None:
        """
        Given the vector store is configured but unreachable
              (VECTOR_STORE_BACKEND=unreachablevec, STORAGE_BACKEND=postgres),
        When preflight_stores() runs,
        Then it raises naming the vector store as unreachable, and the
             run-state store's health probe is never consulted (DECISIONS
             #253 — the first failure stops the sequence).
        """
        ### Given / When / Then
        with (
            patch("server.settings.settings.storage_backend", "postgres"),
            patch("server.settings.settings.vector_store_backend", "unreachablevec"),
            patch(
                "server.db.ports.store_factory.get_vector_store",
                return_value=_UnreachableVectorStore(),
            ),
            patch("server.core.guards.health_check.postgres_health_status") as run_state_probe,
            pytest.raises(SearchIndexMismatchError, match="unreachable"),
        ):
            preflight_stores(_config())

        ### Then
        run_state_probe.assert_not_called()


class TestPreflightStoresRunStateStepShould:
    """Scenario: preflight_stores reaches the run-state step only when split."""

    def test_given_split_store_satisfied_when_preflight_stores_then_run_state_health_checked(
        self,
    ) -> None:
        """
        Given a satisfied vector step on a vector-only store (memory-like,
              can_host_run_state=False) paired with STORAGE_BACKEND=postgres,
        When preflight_stores() runs,
        Then the run-state store's health is checked exactly once (the two
             stores genuinely differ — DECISIONS #253 step 2).
        """

        class _SatisfiedVectorStore:
            def health_check(self) -> bool:
                return True

            def plan_indexes(self, config: ExperimentConfig):
                from server.core.guards.search_index_plan import preflight_not_applicable

                return preflight_not_applicable()

            def ensure_indexes(self) -> None:
                return None

            def capabilities(self) -> VectorCapabilities:
                return _EMPTY_CAPABILITIES

        ### Given / When
        with (
            patch("server.settings.settings.storage_backend", "postgres"),
            patch("server.settings.settings.vector_store_backend", "memorylike"),
            patch(
                "server.db.ports.store_factory.get_vector_store",
                return_value=_SatisfiedVectorStore(),
            ),
            patch(
                "server.core.guards.health_check.postgres_health_status", return_value="ok"
            ) as run_state_probe,
        ):
            preflight_stores(_config())

        ### Then
        run_state_probe.assert_called_once()

    def test_given_single_store_satisfied_when_preflight_stores_then_run_state_step_skipped(
        self,
    ) -> None:
        """
        Given STORAGE_BACKEND=postgres and VECTOR_STORE_BACKEND=postgres
              (single-store — the two steps would hit the same database),
        When preflight_stores() runs,
        Then the run-state health probe is never separately invoked
             (characterization — single-store behaviour is unchanged).
        """
        ### Given / When
        with (
            patch("server.settings.settings.storage_backend", "postgres"),
            patch("server.settings.settings.vector_store_backend", "postgres"),
            patch(
                "server.core.guards.search_index_guard.postgres_vector_extension_present",
                return_value=True,
            ),
            patch(
                "server.core.guards.search_index_guard.collect_postgres_index_snapshot",
            ) as pg_snapshot,
            patch("server.core.guards.health_check.postgres_health_status") as run_state_probe,
        ):
            from server.core.guards.search_index_plan import SearchIndexSnapshot

            required = frozenset(
                {
                    "chunks_embedding_384_hnsw",
                    "chunks_embedding_1024_hnsw",
                    "chunks_text_search_gin",
                }
            )
            pg_snapshot.return_value = SearchIndexSnapshot(
                chunks_ready=required,
                chunks_building=frozenset(),
                cluster_total=3,
                cluster_limit=3,
                unknown_count=0,
            )
            preflight_stores(_config())

        ### Then
        run_state_probe.assert_not_called()
