"""
Tests for the golden-record breakdown facts in db-stats (Slice 67E, backend).

Author: Mani Sarkar
Created: 2026-11-05
Scope: result_runs / golden_queries / golden_queries_source / partial_runs in the
       shared assembly, group totals, SQLite, Mongo and Postgres adapters (query
       counts, failure isolation), the run-state overlay, and lazy idempotent
       persistence of the golden count.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from server.api import experiments_shared
from server.core.pipeline import orchestrator
from server.core.pipeline.orchestrator import _persist_golden_query_count
from server.core.query_loader import load_queries
from server.db.mongo import mongo_stats
from server.db.ports.stats_common import (
    assemble_experiment_db_stats,
    merge_group_totals,
    new_vector_db_group,
)
from server.db.postgres import postgres_stats
from server.models.enums import ExperimentStatus

_NEW_KEYS = {"result_runs", "golden_queries", "golden_queries_source", "partial_runs"}


@pytest.fixture(autouse=True)
def _fresh_golden_memo():
    orchestrator._golden_persisted.clear()
    orchestrator._golden_failure_traced = False
    yield
    orchestrator._golden_persisted.clear()
    orchestrator._golden_failure_traced = False


def _assemble(experiment: dict | None, per_run: list[int] | None) -> dict:
    return assemble_experiment_db_stats(
        experiment,
        database_provider="x",
        collection_name="c",
        cluster_host=None,
        index_names=[],
        total_chunks=0,
        embedding_models=[],
        chunking_breakdown={},
        total_results=sum(per_run or []),
        unique_queries=sum(per_run or []),
        runs_with_data=0,
        run_breakdown=[],
        results_per_run=per_run,
    )


@pytest.fixture()
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import server.db.sqlite.sqlite_store as store_module

    monkeypatch.setattr("server.settings.settings.sqlite_db_path", str(tmp_path / "rs.db"))
    store_module._local.__dict__.clear()
    store_module._storage = None
    from server.db.sqlite.sqlite_store import SQLiteStorageBackend

    return SQLiteStorageBackend()


def _seed(store, rows_per_run: dict[str, int], hits: int = 5, golden: int | None = None) -> None:
    sweep = {"database_provider": "sqlite"}
    if golden is not None:
        sweep["golden_queries"] = golden
    store.insert_experiment(
        {
            "_id": "e1",
            "experiment_id": "e1",
            "experiment_name": "n",
            "status": ExperimentStatus.RUNNING,
            "created_at": datetime(2026, 11, 5, tzinfo=UTC),
            "sweep_summary": sweep,
        }
    )
    n = 0
    for run_id, rows in rows_per_run.items():
        for _ in range(rows):
            n += 1
            store.insert_result(
                {
                    "experiment_id": "e1",
                    "run_id": run_id,
                    "query_id": f"q{n}",
                    "query_text": "t",
                    "results": [{"rank": i} for i in range(hits)],
                }
            )


class TestSharedAssemblyShould:
    def test_given_no_results_when_assembled_then_new_keys_present_and_empty(self) -> None:
        """
        Scenario: every adapter gets the new keys, empty when nothing is known.
        Slice: 67E

        Given an experiment with no result rows
        When the stats are assembled
        Then the four new keys exist with zero or None values.
        """
        ### Given / When
        actual = _assemble(None, None)

        ### Then
        assert _NEW_KEYS <= set(actual)
        assert (actual["result_runs"], actual["golden_queries"]) == (0, None)
        assert (actual["golden_queries_source"], actual["partial_runs"]) == (None, 0)

    def test_given_stored_golden_when_assembled_then_source_is_config(self) -> None:
        """
        Scenario: persisted golden count wins over inference.
        Slice: 67E

        Given sweep_summary.golden_queries = 3 and runs with 3 and 1 rows
        When assembled
        Then source is config and one run is partial.
        """
        ### Given
        experiment = {"sweep_summary": {"golden_queries": 3}}

        ### When
        actual = _assemble(experiment, [3, 1])

        ### Then
        assert (actual["golden_queries"], actual["golden_queries_source"]) == (3, "config")
        assert (actual["result_runs"], actual["partial_runs"]) == (2, 1)

    @pytest.mark.parametrize(
        ("stored", "per_run", "expected"),
        [
            (0, [2], (0, "config", 0)),
            (True, [3, 2], (3, "max_per_run", 1)),
        ],
    )
    def test_given_edge_stored_values_when_assembled_then_rules_hold(
        self, stored: object, per_run: list[int], expected: tuple
    ) -> None:
        """
        Scenario: an empty-dataset count of 0 is honoured; a bool is not a count.
        Slice: 67E

        Given a stored golden of 0, or a stored True
        When assembled
        Then 0 gives source config with no partial runs, and True falls through to inference.
        """
        ### Given
        experiment = {"sweep_summary": {"golden_queries": stored}}

        ### When
        actual = _assemble(experiment, per_run)

        ### Then
        got = (actual["golden_queries"], actual["golden_queries_source"], actual["partial_runs"])
        assert got == expected

    def test_given_results_unknown_when_assembled_then_facts_are_none_not_zero(self) -> None:
        """
        Scenario: a failed optional fetch reports "unknown", not a false zero.
        Slice: 67E

        Given an experiment with a stored golden count but results_known=False
        When assembled and merged into a group
        Then result_runs, partial_runs and golden facts are None and the totals skip them.
        """
        ### Given
        experiment = {"sweep_summary": {"golden_queries": 3}}

        ### When
        actual = assemble_experiment_db_stats(
            experiment,
            database_provider="x",
            collection_name="c",
            cluster_host=None,
            index_names=[],
            total_chunks=0,
            embedding_models=[],
            chunking_breakdown={},
            total_results=4,
            unique_queries=4,
            runs_with_data=0,
            run_breakdown=[],
            results_known=False,
        )
        group = new_vector_db_group("k", actual)
        merge_group_totals(group, actual)

        ### Then
        assert (actual["result_runs"], actual["partial_runs"]) == (None, None)
        assert (actual["golden_queries"], actual["golden_queries_source"]) == (None, None)
        assert group["totals"]["total_result_runs"] == 0
        assert group["totals"]["golden_queries_min"] is None

    def test_given_no_stored_golden_when_assembled_then_inferred_from_max(self) -> None:
        """
        Scenario: older experiments infer the golden count.
        Slice: 67E

        Given no stored golden count and per-run rows 3, 3, 2
        When assembled
        Then golden is 3, tagged max_per_run, and one run is partial.
        """
        ### Given / When
        actual = _assemble({"sweep_summary": {}}, [3, 2, 3])

        ### Then
        assert (actual["golden_queries"], actual["golden_queries_source"]) == (3, "max_per_run")
        assert actual["partial_runs"] == 1

    def test_given_same_inputs_when_assembled_in_any_order_then_identical(self) -> None:
        """
        Scenario: assembly is deterministic regardless of input order.
        Slice: 67E

        Given the same per-run counts in two orders
        When assembled
        Then the outputs are equal.
        """
        ### Given / When / Then
        assert _assemble(None, [1, 3, 2]) == _assemble(None, [2, 3, 1])


class TestGroupTotalsShould:
    def test_given_experiments_when_merged_then_min_max_and_runs_accumulate(self) -> None:
        """
        Scenario: group totals carry min/max golden and total result runs.
        Slice: 67E

        Given a group with experiments golden 5, none, and 3
        When merged
        Then min is 3, max is 5, and result runs add up.
        """
        ### Given
        base = _assemble(None, None)
        group = new_vector_db_group("k", base)
        assert group["totals"]["golden_queries_min"] is None
        assert group["totals"]["golden_queries_max"] is None

        ### When
        for golden, runs in ((5, 2), (None, 0), (3, 4)):
            merge_group_totals(group, {**base, "golden_queries": golden, "result_runs": runs})

        ### Then
        totals = group["totals"]
        assert (totals["golden_queries_min"], totals["golden_queries_max"]) == (3, 5)
        assert totals["total_result_runs"] == 6


class TestSqliteAdapterShould:
    @pytest.mark.parametrize("hits", [5, 10])
    def test_given_three_queries_two_runs_when_top_k_varies_then_total_results_is_six(
        self, store, hits: int
    ) -> None:
        """
        Scenario: top_k_final does not change the results row count.
        Slice: 67E

        Given 3 queries x 2 runs with 5 or 10 hits per row
        When stats are read
        Then total_results and unique_queries are 6, result_runs 2, golden 3 (inferred),
        and no run is partial.
        """
        ### Given
        _seed(store, {"r1": 3, "r2": 3}, hits=hits)

        ### When
        actual = store.get_experiment_db_stats("e1")

        ### Then
        assert (actual["total_results"], actual["unique_queries"]) == (6, 6)
        assert (actual["result_runs"], actual["golden_queries"]) == (2, 3)
        assert (actual["golden_queries_source"], actual["partial_runs"]) == ("max_per_run", 0)

    def test_given_run_failed_after_one_query_when_read_then_partial_run_counted(
        self, store
    ) -> None:
        """
        Scenario: a run that raised after 1 of 3 queries is partial.
        Slice: 67E

        Given golden 3 persisted, one full run and one run with 1 row
        When stats are read
        Then total_results 4, partial_runs 1, golden 3 from config, and the runs conserve:
        partial <= result_runs and full + partial == result_runs.
        """
        ### Given
        _seed(store, {"r1": 3, "r2": 1}, golden=3)

        ### When
        actual = store.get_experiment_db_stats("e1")

        ### Then
        assert actual["total_results"] == 4
        assert (actual["partial_runs"], actual["golden_queries"]) == (1, 3)
        assert actual["golden_queries_source"] == "config"
        golden = actual["golden_queries"]
        full_runs = sum(1 for r in actual["run_breakdown"] if r["results"] >= golden)
        assert actual["partial_runs"] <= actual["result_runs"]
        assert full_runs + actual["partial_runs"] == actual["result_runs"]
        assert store.get_experiment_db_stats("e1") == actual  # repeat-read stability

    def test_given_run_with_zero_rows_when_read_then_not_counted_and_not_partial(
        self, store
    ) -> None:
        """
        Scenario: a run that died before query 1 is invisible to the result facts.
        Slice: 67E

        Given golden 3, one full run and a run_status row with no result rows
        When stats are read
        Then result_runs is 1 and partial_runs is 0.
        """
        ### Given
        _seed(store, {"r1": 3}, golden=3)
        store.insert_run_status(
            {"run_id": "r-dead", "experiment_id": "e1", "phase": "failed", "created_at": None}
        )

        ### When
        actual = store.get_experiment_db_stats("e1")

        ### Then
        assert (actual["result_runs"], actual["partial_runs"]) == (1, 0)

    def test_given_experiment_when_grouped_then_row_and_totals_carry_facts(self, store) -> None:
        """
        Scenario: grouped rows and totals reuse the shared assembly.
        Slice: 67E

        Given one experiment golden 3 with two full runs
        When grouped stats are read
        Then the row has the new keys and totals report 2 runs, min=max=3.
        """
        ### Given
        _seed(store, {"r1": 3, "r2": 3}, golden=3)

        ### When
        group = store.get_vector_db_stats_grouped()["groups"][0]

        ### Then
        totals = group["totals"]
        assert _NEW_KEYS <= set(group["experiments"][0])
        assert totals["total_result_runs"] == 2
        assert (totals["golden_queries_min"], totals["golden_queries_max"]) == (3, 3)

    def test_given_persistence_backend_raises_when_stats_read_then_falls_back_to_inferred(
        self, store, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Scenario: a failing golden-count write is silent but visible in the log.
        Slice: 67E

        Given a backend whose find_experiment_by_id raises and an experiment with no count
        When the count is persisted and the stats are then read
        Then no exception escapes, a warning is logged, and golden comes from max_per_run.
        """
        ### Given
        _seed(store, {"r1": 3, "r2": 2})
        backend = MagicMock()
        backend.find_experiment_by_id.side_effect = RuntimeError("store down")

        ### When
        with (
            patch.object(orchestrator, "get_storage_backend", return_value=backend),
            caplog.at_level(logging.WARNING),
        ):
            _persist_golden_query_count("e1", 3)
        actual = store.get_experiment_db_stats("e1")

        ### Then
        assert any("golden query count not persisted" in r.message for r in caplog.records)
        assert (actual["golden_queries"], actual["golden_queries_source"]) == (3, "max_per_run")
        assert "e1" not in orchestrator._golden_persisted


class TestPersistenceFailureLoggingShould:
    def test_given_repeated_failures_when_persisting_then_traceback_only_on_first(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Scenario: a flapping store cannot flood the log with tracebacks.
        Slice: 67E

        Given a backend that always raises
        When two experiments fail to persist
        Then the first warning carries the traceback and the second is one line.
        """
        ### Given
        backend = MagicMock()
        backend.find_experiment_by_id.side_effect = RuntimeError("down")

        ### When
        with (
            patch.object(orchestrator, "get_storage_backend", return_value=backend),
            caplog.at_level(logging.WARNING),
        ):
            _persist_golden_query_count("e1", 3)
            _persist_golden_query_count("e2", 3)

        ### Then
        records = [r for r in caplog.records if "not persisted" in r.message]
        assert [bool(r.exc_info) for r in records] == [True, False]


class TestMongoAdapterShould:
    def test_given_same_data_as_sqlite_when_stats_read_then_golden_facts_equal(self, store) -> None:
        """
        Scenario: Mongo feeds the breakdown it already builds into the shared assembly.
        Slice: 67E

        Given SQLite seeded with runs of 3 and 1 rows and a mocked Mongo breakdown with the
        same per-run result counts (the mock feeds them; the counts are not re-verified)
        When each adapter computes the single-experiment stats
        Then the four golden facts are equal.
        """
        ### Given
        _seed(store, {"r1": 3, "r2": 1}, golden=3)
        expected = store.get_experiment_db_stats("e1")
        coll = MagicMock()
        coll.find_one.return_value = {"sweep_summary": {"golden_queries": 3}}
        coll.count_documents.return_value = 0
        coll.distinct.return_value = []
        breakdown = [
            {"run_id": "r1", "chunks": 5, "results": 3},
            {"run_id": "r2", "chunks": 5, "results": 1},
        ]
        with (
            patch.object(mongo_stats, "get_collection", return_value=coll),
            patch.object(mongo_stats, "_run_breakdown_for_experiment", return_value=breakdown),
            patch.object(mongo_stats, "_chunking_breakdown", return_value={}),
        ):
            ### When
            actual = mongo_stats.get_experiment_db_stats("e1")

        ### Then
        assert {k: actual[k] for k in _NEW_KEYS} == {k: expected[k] for k in _NEW_KEYS}

    def test_given_chunk_only_run_when_stats_read_then_not_counted(self) -> None:
        """
        Scenario: runs with chunks but no result rows are excluded from result facts.
        Slice: 67E

        Given a breakdown with a full run and a chunk-only run
        When Mongo stats are computed
        Then result_runs is 1 and partial_runs is 0.
        """
        ### Given
        coll = MagicMock()
        coll.find_one.return_value = {"sweep_summary": {"golden_queries": 3}}
        coll.count_documents.return_value = 0
        coll.distinct.return_value = []
        breakdown = [
            {"run_id": "r1", "chunks": 5, "results": 3},
            {"run_id": "r2", "chunks": 5, "results": 0},
        ]
        with (
            patch.object(mongo_stats, "get_collection", return_value=coll),
            patch.object(mongo_stats, "_run_breakdown_for_experiment", return_value=breakdown),
            patch.object(mongo_stats, "_chunking_breakdown", return_value={}),
        ):
            ### When
            actual = mongo_stats.get_experiment_db_stats("e1")

        ### Then
        assert (actual["result_runs"], actual["partial_runs"]) == (1, 0)

    def test_given_single_experiment_when_stats_read_then_aggregate_call_count_unchanged(
        self,
    ) -> None:
        """
        Scenario: the breakdown feeds the golden facts; no extra results scan.
        Slice: 67E

        Given a collection mock that counts aggregate calls
        When the single-experiment stats are computed
        Then aggregate ran exactly twice per collection pair (chunks + results counts by run),
        the count it ran before this slice.
        """
        ### Given
        coll = MagicMock()
        coll.find_one.return_value = None
        coll.count_documents.return_value = 0
        coll.distinct.return_value = []
        coll.aggregate.return_value = []

        ### When
        with patch.object(mongo_stats, "get_collection", return_value=coll):
            mongo_stats.get_experiment_db_stats("e1")

        ### Then
        # chunk counts + result counts (_run_breakdown_for_experiment) + chunking breakdown
        assert coll.aggregate.call_count == 3

    def test_given_grouped_stats_when_results_aggregated_then_one_pipeline_groups_by_exp_and_run(
        self,
    ) -> None:
        """
        Scenario: per-run counts ride the existing results scan.
        Slice: 67E

        Given an aggregate that answers by pipeline content, not by call order
        When the bulk result aggregates are built
        Then exactly one pipeline ran, grouping by experiment_id and run_id first, and the
        per-run counts and distinct query ids roll up per experiment.
        """
        ### Given
        seen: list[list[dict]] = []

        def aggregate(pipeline: list[dict], **_kwargs: object) -> list[dict]:
            seen.append(pipeline)
            return [
                {
                    "_id": "e1",
                    "total_results": 4,
                    "run_counts": [3, 1],
                    "query_ids": [["a", "b", "c"], ["d"]],
                }
            ]

        coll = MagicMock()
        coll.aggregate.side_effect = aggregate

        ### When
        with patch.object(mongo_stats, "get_collection", return_value=coll):
            actual = mongo_stats._bulk_result_aggregates()

        ### Then
        assert len(seen) == 1
        assert seen[0][0]["$group"]["_id"] == {
            "experiment_id": "$experiment_id",
            "run_id": "$run_id",
        }
        assert actual["e1"] == {
            "total_results": 4,
            "unique_queries": 4,
            "results_per_run": [3, 1],
        }


class TestPostgresAdapterShould:
    def test_given_single_experiment_when_stats_read_then_results_table_scanned_twice_only(
        self,
    ) -> None:
        """
        Scenario: the run breakdown feeds the golden facts; no third results GROUP BY.
        Slice: 67E

        Given recorded SQL for every query the single-experiment path issues
        When the stats are computed
        Then SQL touching the results table ran exactly twice (totals + breakdown join),
        and a chunk-only run is not counted in result_runs.
        """
        ### Given
        sql_seen: list[str] = []

        def fetch_one(sql: str, params: tuple = ()) -> dict | None:
            sql_seen.append(sql)
            if "FROM experiments" in sql:
                return None
            if "FROM chunks" in sql:
                return {"total_chunks": 0, "embedding_models": []}
            return {"total_results": 3, "unique_queries": 3}

        def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
            sql_seen.append(sql)
            if "FULL OUTER JOIN" in sql:
                return [
                    {"run_id": "r1", "chunks": 2, "results": 3},
                    {"run_id": "r2", "chunks": 2, "results": 0},
                ]
            return []

        ### When
        with (
            patch.object(postgres_stats, "fetch_one", side_effect=fetch_one),
            patch.object(postgres_stats, "fetch_all", side_effect=fetch_all),
            patch.object(postgres_stats, "_chunks_index_names", return_value=[]),
            patch.object(postgres_stats, "_cluster_host", return_value=None),
        ):
            actual = postgres_stats.get_experiment_db_stats("e1")

        ### Then
        assert sum(1 for sql in sql_seen if "results" in sql) == 2
        assert (actual["result_runs"], actual["partial_runs"]) == (1, 0)

    def test_given_per_run_fetch_raises_when_grouped_then_old_fields_still_returned(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Scenario: the optional per-run query cannot take the group list down.
        Slice: 67E

        Given the grouped path where only the per-run results query raises
        When grouped stats are computed
        Then the group list still returns its old fields, the new facts are None (unknown,
        not 0), the group totals skip them, and one warning is logged with the traceback.
        """
        ### Given
        experiment = {"experiment_id": "e1", "experiment_name": "n", "status": "complete"}

        def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
            if "GROUP BY experiment_id, run_id" in sql:
                raise RuntimeError("boom")
            return []

        ### When
        with (
            patch.object(postgres_stats, "fetch_all", side_effect=fetch_all),
            patch.object(postgres_stats, "_bulk_chunk_aggregates", return_value={}),
            patch.object(
                postgres_stats,
                "_bulk_result_aggregates",
                return_value={"e1": {"total_results": 4, "unique_queries": 4}},
            ),
            patch.object(postgres_stats, "_bulk_chunking_breakdown", return_value={}),
            patch.object(postgres_stats, "_cluster_storage_mb", return_value={}),
            patch.object(postgres_stats, "_chunks_index_names", return_value=[]),
            patch.object(postgres_stats, "_cluster_host", return_value=None),
            caplog.at_level(logging.WARNING),
        ):
            actual = postgres_stats.get_vector_db_stats_grouped(lambda: [experiment])

        ### Then
        row = actual["groups"][0]["experiments"][0]
        assert row["total_results"] == 4
        assert (row["result_runs"], row["partial_runs"], row["golden_queries"]) == (
            None,
            None,
            None,
        )
        assert actual["groups"][0]["totals"]["total_result_runs"] == 0
        warnings = [r for r in caplog.records if "per-run result counts" in r.message]
        assert len(warnings) == 1
        assert warnings[0].exc_info is not None


class TestGroupedViewForStoresWithoutResultsShould:
    def test_given_vector_store_without_results_when_grouped_then_nothing_new_is_reported(
        self,
    ) -> None:
        """
        Scenario: Redis/ES group totals show nothing new (owner decision: no grouped overlay).
        Slice: 67E

        Given stats as the Redis/ES vector stores assemble them (no results, no experiment)
        When a group is created and merged
        Then total_result_runs is 0 and golden min/max stay None.
        """
        ### Given
        stats = _assemble(None, None)
        group = new_vector_db_group("redis-local:host", stats)

        ### When
        merge_group_totals(group, stats)

        ### Then
        totals = group["totals"]
        assert totals["total_result_runs"] == 0
        assert (totals["golden_queries_min"], totals["golden_queries_max"]) == (None, None)


def _zeros() -> dict:
    return {
        "total_results": 0,
        "unique_queries": 0,
        "result_runs": 0,
        "golden_queries": None,
        "golden_queries_source": None,
        "partial_runs": 0,
    }


class TestRunStateOverlayShould:
    def test_given_run_state_facts_when_composed_then_they_override_vector_store(self) -> None:
        """
        Scenario: the single-experiment detail view overlays run-state facts for every
        vector backend (Redis/ES included); only the grouped view has no overlay.
        Slice: 67E

        Given a vector store reporting zeros and run state reporting golden facts
        When experiments_shared composes the stats
        Then the run-state values win for every result fact.
        """
        ### Given
        vector = MagicMock()
        vector.get_experiment_db_stats.return_value = {"total_chunks": 7, **_zeros()}
        run_state = MagicMock()
        run_state.get_experiment_db_stats.return_value = {
            "total_results": 6,
            "unique_queries": 6,
            "result_runs": 2,
            "golden_queries": 3,
            "golden_queries_source": "config",
            "partial_runs": 0,
        }

        ### When
        with (
            patch.object(experiments_shared.store_factory, "get_vector_store", return_value=vector),
            patch.object(experiments_shared, "get_storage_backend", return_value=run_state),
        ):
            actual = experiments_shared.get_experiment_db_stats("e1")

        ### Then
        assert actual["total_chunks"] == 7
        assert (actual["result_runs"], actual["golden_queries"]) == (2, 3)
        assert actual["golden_queries_source"] == "config"
        assert actual["total_results"] == 6


class TestGoldenCountPersistenceShould:
    def test_given_stored_count_when_second_run_loads_then_nothing_written(self) -> None:
        """
        Scenario: lazy persistence is idempotent.
        Slice: 67E

        Given an experiment that already has golden_queries
        When another run persists a count
        Then no update is issued.
        """
        ### Given
        backend = MagicMock()
        backend.find_experiment_by_id.return_value = {"sweep_summary": {"golden_queries": 3}}

        ### When
        with patch.object(orchestrator, "get_storage_backend", return_value=backend):
            _persist_golden_query_count("e1", 99)

        ### Then
        backend.update_experiment.assert_not_called()

    def test_given_no_count_when_first_run_loads_then_written_once_keeping_summary(self) -> None:
        """
        Scenario: the first run writes the count and keeps the rest of sweep_summary.
        Slice: 67E

        Given an experiment without golden_queries
        When the first run persists 3
        Then update_experiment receives the merged sweep_summary exactly once.
        """
        ### Given
        backend = MagicMock()
        backend.find_experiment_by_id.return_value = {"sweep_summary": {"models": ["m"]}}

        ### When
        with patch.object(orchestrator, "get_storage_backend", return_value=backend):
            _persist_golden_query_count("e1", 3)

        ### Then
        backend.update_experiment.assert_called_once_with(
            "e1", {"sweep_summary": {"models": ["m"], "golden_queries": 3}}
        )

    def test_given_count_already_persisted_when_second_run_loads_then_no_read_happens(self) -> None:
        """
        Scenario: the process-local memo caps the read at once per experiment.
        Slice: 67E

        Given the first run persisted the count
        When a second run asks to persist again
        Then no further read or write reaches the backend.
        """
        ### Given
        backend = MagicMock()
        backend.find_experiment_by_id.return_value = {"sweep_summary": {}}
        with patch.object(orchestrator, "get_storage_backend", return_value=backend):
            _persist_golden_query_count("e1", 3)
            backend.reset_mock()

            ### When
            _persist_golden_query_count("e1", 3)

        ### Then
        backend.find_experiment_by_id.assert_not_called()
        backend.update_experiment.assert_not_called()

    @pytest.mark.parametrize(
        ("personas", "expected"),
        [
            ([("a", ["q1", "q2"]), ("b", ["q3"])], 3),
            ([("a", ["same", "same", "same"])], 3),
        ],
    )
    def test_given_dataset_when_persisted_then_count_is_records_not_distinct_texts(
        self, tmp_path: Path, personas: list, expected: int
    ) -> None:
        """
        Scenario: golden count equals the records the pipeline's loader returns.
        Slice: 67E

        Given a multi-persona dataset, and one with duplicate query text
        When the count from load_queries is persisted
        Then the stored value is the number of records (duplicates counted).
        """
        ### Given
        path = tmp_path / "q.json"
        path.write_text(
            json.dumps(
                {
                    "personas": [
                        {"id": pid, "questions": [{"text": t} for t in texts]}
                        for pid, texts in personas
                    ]
                }
            )
        )
        backend = MagicMock()
        backend.find_experiment_by_id.return_value = {"sweep_summary": {}}

        ### When
        with patch.object(orchestrator, "get_storage_backend", return_value=backend):
            _persist_golden_query_count("e1", len(load_queries(str(path))))

        ### Then
        written = backend.update_experiment.call_args.args[1]["sweep_summary"]
        assert written["golden_queries"] == expected
