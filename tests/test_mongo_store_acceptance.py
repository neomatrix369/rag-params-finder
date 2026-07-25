"""
Acceptance tests for server.db.mongo_store (MongoStorageBackend port).

Author: swami
Created: 2026-07-25
Scope: ATDD scenarios for experiment CRUD lifecycle, cascade delete, explore
       source, per-experiment db stats, grouped vector-db stats, run interrupt,
       and singleton accessors — Mongo I/O mocked at get_collection / get_database.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from server.db.indexes import TEXT_SEARCH_INDEX_NAME
from server.db.mongo_store import (
    MongoStorageBackend,
    get_mongo_retriever,
    get_mongo_storage,
)
from server.models.enums import ExperimentStatus

_EXP_ID = "exp-at-1"
_RUN_ID = "run-at-1"
_MODEL = "voyage-3.5-lite"
_LOCAL_MODEL = "all-MiniLM-L6-v2"


def _coll() -> MagicMock:
    """Fresh collection mock with chainable find/sort/limit defaults."""
    c = MagicMock(name="collection")
    c.find.return_value = c
    c.sort.return_value = c
    c.limit.return_value = []
    c.find_one.return_value = None
    c.count_documents.return_value = 0
    c.distinct.return_value = []
    c.aggregate.return_value = []
    c.insert_one.return_value = MagicMock()
    c.insert_many.return_value = MagicMock()
    c.update_one.return_value = MagicMock()
    c.update_many.return_value = MagicMock()
    c.delete_many.return_value = MagicMock(deleted_count=0)
    c.delete_one.return_value = MagicMock(deleted_count=0)
    return c


def _patch_collections(mapping: dict[str, MagicMock]) -> Any:
    """Patch get_collection in mongo_store (CRUD methods that still live there)."""

    def _get(name: str) -> MagicMock:
        if name not in mapping:
            mapping[name] = _coll()
        return mapping[name]

    return patch("server.db.mongo_store.get_collection", side_effect=_get)


def _patch_stats_collections(mapping: dict[str, MagicMock]) -> Any:
    """Patch get_collection in mongo_stats (stats/explore helpers)."""

    def _get(name: str) -> MagicMock:
        if name not in mapping:
            mapping[name] = _coll()
        return mapping[name]

    return patch("server.db.mongo_stats.get_collection", side_effect=_get)


class TestMongoStorageBackendShould:
    """Acceptance scenarios for the Mongo storage adapter (StorageBackend port)."""

    # ── Cascade delete ────────────────────────────────────────────────────────

    def test_given_experiment_with_related_docs_when_deleted_then_returns_all_counts(
        self,
    ) -> None:
        """
        Scenario: Cascade delete removes experiment, runs, chunks, and results.
        Slice: mongo-store-acceptance / cascade-delete

        Given related documents exist across four collections,
        When delete_experiment_data is called,
        Then counts for experiments, run_status, chunks, and results are returned.
        """
        ### Given
        store = MongoStorageBackend()
        collections = {
            "chunks": _coll(),
            "results": _coll(),
            "run_status": _coll(),
            "experiments": _coll(),
        }
        collections["chunks"].delete_many.return_value = MagicMock(deleted_count=10)
        collections["results"].delete_many.return_value = MagicMock(deleted_count=5)
        collections["run_status"].delete_many.return_value = MagicMock(deleted_count=3)
        collections["experiments"].delete_one.return_value = MagicMock(deleted_count=1)

        ### When
        with _patch_collections(collections):
            actual = store.delete_experiment_data(_EXP_ID)

        ### Then
        expected = {"experiments": 1, "run_status": 3, "chunks": 10, "results": 5}
        assert actual == expected, f"cascade counts mismatch: {actual}"
        collections["chunks"].delete_many.assert_called_once_with({"experiment_id": _EXP_ID})
        collections["experiments"].delete_one.assert_called_once_with({"experiment_id": _EXP_ID})

    # ── Explore source ────────────────────────────────────────────────────────

    def test_given_missing_experiment_when_explore_loaded_then_returns_none_and_empty_lists(
        self,
    ) -> None:
        """
        Scenario: Explore source for unknown experiment yields empty payload.
        Slice: mongo-store-acceptance / explore

        Given no experiment document exists,
        When load_explore_source is called,
        Then (None, [], []) is returned.
        """
        ### Given
        store = MongoStorageBackend()
        collections = {"experiments": _coll()}

        ### When
        with _patch_stats_collections(collections):
            actual = store.load_explore_source(_EXP_ID)

        ### Then
        assert actual == (None, [], []), f"expected empty explore tuple, got {actual}"

    def test_given_experiment_with_results_when_explore_loaded_then_returns_full_tuple(
        self,
    ) -> None:
        """
        Scenario: Explore source loads experiment, results, and run statuses.
        Slice: mongo-store-acceptance / explore

        Given an experiment with results and run statuses,
        When load_explore_source is called,
        Then the experiment and both lists are returned.
        """
        ### Given
        store = MongoStorageBackend()
        experiment = {"experiment_id": _EXP_ID, "status": "complete"}
        results = [{"query_id": "q1"}]
        runs = [{"run_id": _RUN_ID}]
        collections = {
            "experiments": _coll(),
            "results": _coll(),
            "run_status": _coll(),
        }
        collections["experiments"].find_one.return_value = experiment
        collections["results"].find.return_value = results
        collections["run_status"].find.return_value = runs

        ### When
        with _patch_stats_collections(collections):
            actual_exp, actual_results, actual_runs = store.load_explore_source(_EXP_ID)

        ### Then
        assert actual_exp == experiment, "experiment must be returned as stored"
        assert actual_results == results, "results list must match collection find"
        assert actual_runs == runs, "run statuses must match collection find"

    # ── Lifecycle status ──────────────────────────────────────────────────────

    def test_given_cancelled_experiment_when_checked_then_is_cancelled_true(self) -> None:
        """
        Scenario: Cancellation flag reflects cancelled experiment status.
        Slice: mongo-store-acceptance / lifecycle

        Given an experiment document with cancelled status,
        When is_experiment_cancelled is called,
        Then True is returned.
        """
        ### Given
        store = MongoStorageBackend()
        collections = {"experiments": _coll()}
        collections["experiments"].find_one.return_value = {
            "status": ExperimentStatus.CANCELLED.value
        }

        ### When
        with _patch_collections(collections):
            actual = store.is_experiment_cancelled(_EXP_ID)

        ### Then
        assert actual is True, "cancelled experiment must report is_cancelled=True"

    def test_given_running_experiment_when_checked_then_is_cancelled_false(self) -> None:
        """
        Scenario: Non-cancelled status does not report as cancelled.
        Slice: mongo-store-acceptance / lifecycle

        Given an experiment document with running status,
        When is_experiment_cancelled is called,
        Then False is returned.
        """
        ### Given
        store = MongoStorageBackend()
        collections = {"experiments": _coll()}
        collections["experiments"].find_one.return_value = {
            "status": ExperimentStatus.RUNNING.value
        }

        ### When
        with _patch_collections(collections):
            actual = store.is_experiment_cancelled(_EXP_ID)

        ### Then
        assert actual is False, "running experiment must report is_cancelled=False"

    def test_given_experiment_id_when_lifecycle_marks_applied_then_status_updates_issued(
        self,
    ) -> None:
        """
        Scenario: Pause / cancel / resume marks write the expected status fields.
        Slice: mongo-store-acceptance / lifecycle

        Given an experiment id,
        When mark cancelled, paused, and running are called,
        Then each issues an update_one with the corresponding status.
        """
        ### Given
        store = MongoStorageBackend()
        collections = {"experiments": _coll()}

        ### When
        with _patch_collections(collections):
            store.mark_experiment_cancelled(_EXP_ID)
            store.mark_experiment_paused(_EXP_ID)
            store.mark_experiment_running(_EXP_ID)

        ### Then
        calls = collections["experiments"].update_one.call_args_list
        assert len(calls) == 3, f"expected 3 status updates, got {len(calls)}"
        statuses = [c.args[1]["$set"]["status"] for c in calls]
        assert statuses == [
            ExperimentStatus.CANCELLED,
            ExperimentStatus.PAUSED,
            ExperimentStatus.RUNNING,
        ], f"unexpected status sequence: {statuses}"
        assert calls[2].args[1]["$set"]["completed_at"] is None, "resume must clear completed_at"

    def test_given_experiment_with_runs_when_fetched_then_runs_attached_sorted(
        self,
    ) -> None:
        """
        Scenario: Experiment detail includes sorted run statuses.
        Slice: mongo-store-acceptance / lifecycle

        Given an experiment and two run status docs,
        When find_experiment_with_runs is called,
        Then the experiment dict includes a runs list from the run_status query.
        """
        ### Given
        store = MongoStorageBackend()
        experiment = {"experiment_id": _EXP_ID, "status": "running"}
        runs = [{"run_id": "r1"}, {"run_id": "r2"}]
        collections = {"experiments": _coll(), "run_status": _coll()}
        collections["experiments"].find_one.return_value = experiment
        collections["run_status"].find.return_value = collections["run_status"]
        collections["run_status"].sort.return_value = runs

        ### When
        with _patch_collections(collections):
            actual = store.find_experiment_with_runs(_EXP_ID)

        ### Then
        assert actual is not None, "experiment must be found"
        assert actual["runs"] == runs, "runs must be attached from run_status"
        collections["run_status"].sort.assert_called_once_with("created_at", 1)

    def test_given_missing_experiment_when_fetched_with_runs_then_returns_none(
        self,
    ) -> None:
        """
        Scenario: Missing experiment yields None without querying runs further.
        Slice: mongo-store-acceptance / lifecycle

        Given no experiment document,
        When find_experiment_with_runs is called,
        Then None is returned.
        """
        ### Given
        store = MongoStorageBackend()
        collections = {"experiments": _coll()}

        ### When
        with _patch_collections(collections):
            actual = store.find_experiment_with_runs(_EXP_ID)

        ### Then
        assert actual is None, "missing experiment must return None"

    # ── Run interrupt / chunks guards ─────────────────────────────────────────

    def test_given_empty_run_ids_when_mark_interrupted_then_no_update_issued(self) -> None:
        """
        Scenario: Interrupt with empty run list is a no-op.
        Slice: mongo-store-acceptance / run-interrupt

        Given an empty run_ids list,
        When mark_runs_interrupted is called,
        Then no collection update is issued.
        """
        ### Given
        store = MongoStorageBackend()
        collections = {"run_status": _coll()}

        ### When
        with _patch_collections(collections):
            store.mark_runs_interrupted(
                [],
                updated_at=datetime.now(UTC),
                error_message="server restart",
            )

        ### Then
        collections["run_status"].update_many.assert_not_called()

    def test_given_run_ids_when_mark_interrupted_then_phase_set_to_interrupted(
        self,
    ) -> None:
        """
        Scenario: Interrupt marks listed runs as interrupted with error message.
        Slice: mongo-store-acceptance / run-interrupt

        Given two run ids,
        When mark_runs_interrupted is called,
        Then update_many sets phase=interrupted for those run ids.
        """
        ### Given
        store = MongoStorageBackend()
        collections = {"run_status": _coll()}
        when = datetime(2026, 7, 25, tzinfo=UTC)

        ### When
        with _patch_collections(collections):
            store.mark_runs_interrupted(
                ["r1", "r2"],
                updated_at=when,
                error_message="orphaned",
            )

        ### Then
        collections["run_status"].update_many.assert_called_once()
        filter_arg, update_arg = collections["run_status"].update_many.call_args.args
        assert filter_arg == {"run_id": {"$in": ["r1", "r2"]}}
        assert update_arg["$set"]["phase"] == "interrupted"
        assert update_arg["$set"]["error_message"] == "orphaned"

    def test_given_empty_docs_when_insert_chunks_then_no_insert_many(self) -> None:
        """
        Scenario: Empty chunk batch does not call insert_many.
        Slice: mongo-store-acceptance / chunks

        Given an empty document list,
        When insert_chunks is called,
        Then insert_many is not invoked.
        """
        ### Given
        store = MongoStorageBackend()
        collections = {"chunks": _coll()}

        ### When
        with _patch_collections(collections):
            store.insert_chunks([])

        ### Then
        collections["chunks"].insert_many.assert_not_called()

    def test_given_chunk_docs_when_inserted_then_insert_many_called(self) -> None:
        """
        Scenario: Non-empty chunk batch is written via insert_many.
        Slice: mongo-store-acceptance / chunks

        Given one chunk document,
        When insert_chunks is called,
        Then insert_many receives that document list.
        """
        ### Given
        store = MongoStorageBackend()
        collections = {"chunks": _coll()}
        docs = [{"experiment_id": _EXP_ID, "text": "hello"}]

        ### When
        with _patch_collections(collections):
            store.insert_chunks(docs)

        ### Then
        collections["chunks"].insert_many.assert_called_once_with(docs)

    # ── Per-experiment db stats ───────────────────────────────────────────────

    def test_given_experiment_with_chunks_and_sparse_retrieval_when_stats_then_includes_text_index(
        self,
    ) -> None:
        """
        Scenario: Db stats assemble chunk/result metrics and text index for sparse.
        Slice: mongo-store-acceptance / db-stats

        Given chunks for a voyage model and sparse retrieval in sweep_summary,
        When get_experiment_db_stats is called,
        Then totals, storage estimates, and text_search_index appear in the result.
        """
        ### Given
        store = MongoStorageBackend()
        experiment = {
            "experiment_id": _EXP_ID,
            "data_paths": ["a.pdf", "b.pdf"],
            "sweep_summary": {
                "database_provider": "mongodb",
                "retrieval_methods": ["sparse"],
            },
        }
        chunks = _coll()
        results = _coll()
        experiments = _coll()
        experiments.find_one.return_value = experiment
        chunks.count_documents.return_value = 100
        chunks.distinct.side_effect = lambda field, *_a, **_k: (
            [_MODEL] if field == "embedding_model" else [_RUN_ID]
        )
        results.count_documents.return_value = 20
        results.distinct.return_value = ["q1", "q2"]
        chunks.aggregate.side_effect = [
            [{"_id": _RUN_ID, "count": 100}],  # document counts by run
            [{"_id": "fixed", "count": 100}],  # chunking breakdown
        ]
        results.aggregate.return_value = [{"_id": _RUN_ID, "count": 20}]
        collections = {
            "experiments": experiments,
            "chunks": chunks,
            "results": results,
        }

        ### When
        with _patch_stats_collections(collections):
            actual = store.get_experiment_db_stats(_EXP_ID)

        ### Then
        assert actual["total_chunks"] == 100, "chunk count must match"
        assert actual["unique_documents"] == 2, "data_paths length is unique_documents"
        assert actual["unique_queries"] == 2, "distinct query_ids"
        assert actual["total_results"] == 20
        assert TEXT_SEARCH_INDEX_NAME in actual["index_names"], (
            "sparse retrieval must include text search index"
        )
        assert actual["estimated_storage_mb"] > 0, "known model must yield storage estimate"
        assert actual["runs_with_data"] == 1
        assert actual["run_breakdown"] == [{"run_id": _RUN_ID, "chunks": 100, "results": 20}]

    def test_given_stats_compute_failure_when_requested_then_reraises(self) -> None:
        """
        Scenario: Db-stats failure is logged and re-raised to the caller.
        Slice: mongo-store-acceptance / db-stats

        Given get_collection raises during stats computation,
        When get_experiment_db_stats is called,
        Then the original exception propagates.
        """
        ### Given
        store = MongoStorageBackend()

        ### When / Then
        with (
            patch(
                "server.db.mongo_stats.get_collection",
                side_effect=RuntimeError("db down"),
            ),
            pytest.raises(RuntimeError, match="db down"),
        ):
            store.get_experiment_db_stats(_EXP_ID)

    # ── Grouped vector db stats ───────────────────────────────────────────────

    def test_given_experiments_when_grouped_stats_then_aggregates_totals_and_cluster_storage(
        self,
    ) -> None:
        """
        Scenario: Grouped vector-db stats merge per-experiment rows and cluster quota.
        Slice: mongo-store-acceptance / grouped-stats

        Given two experiments sharing a cluster with chunk/result aggregates,
        When get_vector_db_stats_grouped is called,
        Then one group is returned with summed totals and cluster storage fields.
        """
        ### Given
        store = MongoStorageBackend()
        created = datetime(2026, 7, 1, tzinfo=UTC)
        experiments = [
            {
                "experiment_id": "e1",
                "experiment_name": "alpha",
                "status": "complete",
                "created_at": created,
                "data_paths": ["a.pdf"],
                "sweep_summary": {
                    "database_provider": "mongodb",
                    "retrieval_methods": ["dense"],
                },
            },
            {
                "experiment_id": "e2",
                "experiment_name": "beta",
                "status": "complete",
                "created_at": "2026-07-02T00:00:00+00:00",
                "data_paths": [],
                "sweep_summary": {
                    "database_provider": "mongodb",
                    "retrieval_methods": ["hybrid"],
                },
            },
        ]
        exp_coll = _coll()
        exp_coll.find.return_value = exp_coll
        exp_coll.sort.return_value = experiments

        chunks = _coll()
        results = _coll()
        # bulk chunk aggregates, then bulk chunking breakdown
        chunks.aggregate.side_effect = [
            [
                {
                    "_id": "e1",
                    "total_chunks": 50,
                    "embedding_models": [_MODEL],
                    "run_ids": ["r1"],
                },
                {
                    "_id": "e2",
                    "total_chunks": 30,
                    "embedding_models": [_LOCAL_MODEL, "unknown-model"],
                    "run_ids": ["r2", "r3"],
                },
            ],
            [
                {"_id": {"experiment_id": "e1", "chunk_method": "fixed"}, "count": 50},
                {"_id": {"experiment_id": "e2", "chunk_method": "recursive"}, "count": 30},
                {"_id": {"experiment_id": None, "chunk_method": "fixed"}, "count": 1},
            ],
        ]
        results.aggregate.return_value = [
            {"_id": "e1", "total_results": 10, "query_ids": ["q1"]},
            {"_id": "e2", "total_results": 5, "query_ids": ["q2", "q3"]},
        ]

        collections = {
            "experiments": exp_coll,
            "chunks": chunks,
            "results": results,
        }
        db = MagicMock()
        db.command.return_value = {
            "dataSize": 10 * 1024 * 1024,
            "indexSize": 2 * 1024 * 1024,
            "totalSize": 12 * 1024 * 1024,
        }
        tier = {
            "storage_mb": 512,
            "instance_size": "M0",
            "tier_type": "shared",
            "provider": "AWS",
            "region": "EU_WEST_1",
        }

        ### When
        with (
            _patch_collections(collections),
            _patch_stats_collections(collections),
            patch("server.db.mongo_stats.get_database", return_value=db),
            patch(
                "server.db.mongo_stats.resolve_tier_specs",
                return_value=tier,
            ),
            patch(
                "server.settings.settings.mongodb_uri",
                "mongodb+srv://u:p@cluster0.abc.mongodb.net/rag?retryWrites=true",
            ),
        ):
            actual = store.get_vector_db_stats_grouped()

        ### Then
        groups = actual["groups"]
        assert len(groups) == 1, f"expected one cluster group, got {len(groups)}"
        group = groups[0]
        assert group["cluster_host"] == "cluster0.abc.mongodb.net"
        assert group["totals"]["experiment_count"] == 2
        assert group["totals"]["total_chunks"] == 80
        assert group["totals"]["total_results"] == 15
        assert group["totals"]["database_storage_limit_mb"] == 512.0
        assert group["totals"]["cluster_tier"] == "M0"
        assert TEXT_SEARCH_INDEX_NAME in group["index_names"], (
            "hybrid experiment must contribute text search index to group"
        )
        exp_ids = [e["experiment_id"] for e in group["experiments"]]
        assert exp_ids[0] == "e2", "experiments sorted newest-first by created_at"

    def test_given_grouped_stats_failure_when_requested_then_reraises(self) -> None:
        """
        Scenario: Grouped-stats failure is logged and re-raised.
        Slice: mongo-store-acceptance / grouped-stats

        Given find_all_experiments raises,
        When get_vector_db_stats_grouped is called,
        Then the exception propagates.
        """
        ### Given
        store = MongoStorageBackend()

        ### When / Then
        with (
            patch.object(
                store,
                "find_all_experiments",
                side_effect=RuntimeError("agg failed"),
            ),
            pytest.raises(RuntimeError, match="agg failed"),
        ):
            store.get_vector_db_stats_grouped()

    # ── CRUD smoke (essential write/read shaping) ─────────────────────────────

    def test_given_docs_when_basic_crud_called_then_collection_ops_dispatched(
        self,
    ) -> None:
        """
        Scenario: Thin CRUD methods dispatch to the correct collection operations.
        Slice: mongo-store-acceptance / crud

        Given a storage backend,
        When insert/find/update/count helpers are exercised,
        Then each issues the expected collection call and return shaping.
        """
        ### Given
        store = MongoStorageBackend()
        collections = {
            "experiments": _coll(),
            "run_status": _coll(),
            "results": _coll(),
            "chunks": _coll(),
        }
        exp_cursor = MagicMock(name="exp_cursor")
        exp_cursor.sort.return_value = [{"experiment_id": _EXP_ID}]
        exp_cursor.__iter__ = lambda self: iter([{"experiment_id": "running-1"}])
        collections["experiments"].find.return_value = exp_cursor
        collections["experiments"].find_one.return_value = {"experiment_id": _EXP_ID}

        run_cursor = MagicMock(name="run_cursor")
        run_cursor.__iter__ = lambda self: iter([{"run_id": _RUN_ID}])
        run_cursor.limit.return_value = [{"run_id": _RUN_ID}]
        collections["run_status"].find.return_value = run_cursor
        collections["run_status"].find_one.return_value = {"run_id": _RUN_ID}
        collections["run_status"].count_documents.return_value = 2
        collections["results"].find.return_value = [{"query_text": "q"}]
        collections["chunks"].delete_many.return_value = MagicMock(deleted_count=4)
        collections["results"].delete_many.return_value = MagicMock(deleted_count=7)
        when = datetime.now(UTC)

        ### When
        with _patch_collections(collections), _patch_stats_collections(collections):
            store.insert_experiment({"experiment_id": _EXP_ID})
            store.update_experiment(_EXP_ID, {"status": "running"})
            store.insert_run_status({"run_id": _RUN_ID})
            store.update_run_phase(
                _RUN_ID,
                phase="complete",
                updated_at=when,
                elapsed_ms=10,
                error_message=None,
            )
            store.insert_result({"experiment_id": _EXP_ID})
            store.update_experiment_reconciled(
                _EXP_ID,
                status=ExperimentStatus.PARTIAL,
                failed_count=1,
                completion_reason="boot",
                completed_at=when,
            )
            actual_all = store.find_all_experiments()
            actual_one = store.find_experiment_by_id(_EXP_ID)
            actual_run = store.find_run_status(_RUN_ID)
            actual_runs = store.find_run_statuses(_EXP_ID)
            actual_sigs = store.find_completed_run_sigs(_EXP_ID)
            actual_count = store.count_runs_by_phase(_EXP_ID, "failed")
            actual_by_phase = store.find_runs_by_phase(_EXP_ID, "failed", 5)
            actual_running = store.find_running_experiments()
            actual_results = store.find_results_for_experiment(_EXP_ID)
            actual_run_results = store.find_results_for_run(_EXP_ID, _RUN_ID)
            actual_list = store.list_results_for_experiment(_EXP_ID)
            actual_del_chunks = store.delete_chunks_for_experiment(_EXP_ID)
            actual_del_results = store.delete_results_for_experiment(_EXP_ID)

        ### Then
        assert actual_all == [{"experiment_id": _EXP_ID}]
        assert actual_one == {"experiment_id": _EXP_ID}
        assert actual_run == {"run_id": _RUN_ID}
        assert actual_runs == [{"run_id": _RUN_ID}]
        assert actual_sigs == [{"run_id": _RUN_ID}]
        assert actual_count == 2
        assert actual_by_phase == [{"run_id": _RUN_ID}]
        assert actual_running == [{"experiment_id": "running-1"}]
        assert actual_results == [{"query_text": "q"}]
        assert actual_run_results == [{"query_text": "q"}]
        assert actual_list == [{"query_text": "q"}]
        assert actual_del_chunks == 4
        assert actual_del_results == 7
        collections["experiments"].insert_one.assert_called_once()
        collections["run_status"].insert_one.assert_called_once()
        collections["results"].insert_one.assert_called_once()
        collections["experiments"].find.assert_any_call({"status": ExperimentStatus.RUNNING})

    # ── Singletons ────────────────────────────────────────────────────────────

    def test_given_repeated_accessor_calls_when_fetched_then_same_singleton_returned(
        self,
    ) -> None:
        """
        Scenario: Storage and retriever accessors memoize a single instance.
        Slice: mongo-store-acceptance / singletons

        Given the module-level singletons are cleared,
        When get_mongo_storage / get_mongo_retriever are called twice each,
        Then each pair returns the identical instance.
        """
        ### Given
        import server.db.mongo_store as mod

        mod._storage = None
        mod._retriever = None

        ### When
        s1 = get_mongo_storage()
        s2 = get_mongo_storage()
        r1 = get_mongo_retriever()
        r2 = get_mongo_retriever()

        ### Then
        assert s1 is s2, "storage singleton must be memoized"
        assert r1 is r2, "retriever singleton must be memoized"
        assert isinstance(s1, MongoStorageBackend)
