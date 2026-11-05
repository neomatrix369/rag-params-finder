"""
Tests for the golden-record breakdown facts in db-stats (Slice 67E, backend).

Author: Mani Sarkar
Created: 2026-11-05
Scope: result_runs / golden_queries / golden_queries_source / partial_runs in the
       shared assembly, group totals, SQLite and Mongo adapters, the run-state
       overlay, and lazy idempotent persistence of the golden count.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from server.api import experiments_shared
from server.core.orchestrator import _persist_golden_query_count
from server.core.query_loader import load_queries
from server.db.ports.stats_common import (
    assemble_experiment_db_stats,
    merge_group_totals,
    new_vector_db_group,
)
from server.models.enums import ExperimentStatus

_NEW_KEYS = {"result_runs", "golden_queries", "golden_queries_source", "partial_runs"}


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
        Then total_results is 6, result_runs 2, golden 3 (inferred), no partial run.
        """
        ### Given
        _seed(store, {"r1": 3, "r2": 3}, hits=hits)

        ### When
        actual = store.get_experiment_db_stats("e1")

        ### Then
        assert actual["total_results"] == 6
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
        Then total_results 4, partial_runs 1, golden 3 from config.
        """
        ### Given
        _seed(store, {"r1": 3, "r2": 1}, golden=3)

        ### When
        actual = store.get_experiment_db_stats("e1")

        ### Then
        assert actual["total_results"] == 4
        assert (actual["partial_runs"], actual["golden_queries"]) == (1, 3)
        assert actual["golden_queries_source"] == "config"

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


class TestMongoAdapterShould:
    def test_given_counts_per_run_when_stats_read_then_facts_match_sqlite(self) -> None:
        """
        Scenario: Mongo feeds the same per-run counts into the shared assembly.
        Slice: 67E

        Given result counts of 3 and 1 rows per run and golden 3 stored
        When the Mongo single-experiment stats are computed
        Then they equal the SQLite facts for the same data.
        """
        ### Given
        from server.db.mongo import mongo_stats

        coll = MagicMock()
        coll.find_one.return_value = {"sweep_summary": {"golden_queries": 3}}
        coll.count_documents.return_value = 0
        coll.distinct.return_value = []
        with (
            patch.object(mongo_stats, "get_collection", return_value=coll),
            patch.object(mongo_stats, "_document_counts_by_run_id", return_value={"a": 3, "b": 1}),
            patch.object(mongo_stats, "_run_breakdown_for_experiment", return_value=[]),
            patch.object(mongo_stats, "_chunking_breakdown", return_value={}),
        ):
            ### When
            actual = mongo_stats.get_experiment_db_stats("e1")

        ### Then
        assert (actual["result_runs"], actual["golden_queries"]) == (2, 3)
        assert (actual["partial_runs"], actual["golden_queries_source"]) == (1, "config")


class TestRedisAndElasticsearchShould:
    def test_given_vector_store_without_results_when_assembled_then_nothing_new(self) -> None:
        """
        Scenario: Redis/ES hold no results and pass no per-run counts.
        Slice: 67E

        Given an assembly call as the Redis/ES stores make it (no experiment, no counts)
        When assembled
        Then result_runs is 0 and golden_queries is None.
        """
        ### Given / When
        actual = _assemble(None, None)

        ### Then
        assert actual["result_runs"] == 0
        assert actual["golden_queries"] is None


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
        Scenario: the overlay carries the new fields from run state.
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
        with patch("server.core.orchestrator.get_storage_backend", return_value=backend):
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
        with patch("server.core.orchestrator.get_storage_backend", return_value=backend):
            _persist_golden_query_count("e1", 3)

        ### Then
        backend.update_experiment.assert_called_once_with(
            "e1", {"sweep_summary": {"models": ["m"], "golden_queries": 3}}
        )

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
        with patch("server.core.orchestrator.get_storage_backend", return_value=backend):
            _persist_golden_query_count("e1", len(load_queries(str(path))))

        ### Then
        written = backend.update_experiment.call_args.args[1]["sweep_summary"]
        assert written["golden_queries"] == expected
