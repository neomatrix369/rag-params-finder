"""
Live Mongo test for the golden-record breakdown aggregation (Slice 67E).

Author: Mani Sarkar
Created: 2026-11-05
Scope: Runs the real grouped results pipeline and the single-experiment stats against a
       live MongoDB (skips without one, like the other live Mongo tests). Start one with
       ``./start-services.sh --mongodb-local`` or point RAG_TEST_MONGODB_URI at any
       MongoDB; no Atlas Search feature is used.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from server.db.mongo import mongo_stats
from server.models.enums import ExperimentStatus

pytestmark = pytest.mark.integration

_EXP_A = "exp-67e-live-a"
_EXP_B = "exp-67e-live-b"


def _experiment(exp_id: str, golden: int | None) -> dict:
    sweep: dict = {"database_provider": "mongodb"}
    if golden is not None:
        sweep["golden_queries"] = golden
    return {
        "_id": exp_id,
        "experiment_id": exp_id,
        "experiment_name": exp_id,
        "status": ExperimentStatus.COMPLETE,
        "created_at": datetime(2026, 11, 5, tzinfo=UTC),
        "data_paths": [],
        "sweep_summary": sweep,
    }


def _insert_rows(store, exp_id: str, run_id: str, rows: int) -> None:
    for n in range(rows):
        store.insert_result(
            {
                "experiment_id": exp_id,
                "run_id": run_id,
                "query_id": f"{run_id}-q{n}",
                "query_text": "q",
                "results": [{"rank": 1}, {"rank": 2}],
            }
        )
    mongo_stats.get_collection("chunks").insert_one(
        {
            "chunk_id": f"{run_id}-c",
            "experiment_id": exp_id,
            "run_id": run_id,
            "embedding_model": "all-MiniLM-L6-v2",
            "chunk_method": "recursive",
            "embedding": [0.1] * 384,
        }
    )


@pytest.fixture
def seeded(mongo_storage) -> Iterator[object]:
    """Exp A: golden 3, runs of 3 and 1 rows. Exp B: no golden count, runs of 2 and 2 rows."""
    for exp_id in (_EXP_A, _EXP_B):
        mongo_storage.delete_experiment_data(exp_id)
    mongo_storage.insert_experiment(_experiment(_EXP_A, 3))
    mongo_storage.insert_experiment(_experiment(_EXP_B, None))
    _insert_rows(mongo_storage, _EXP_A, "a-r1", 3)
    _insert_rows(mongo_storage, _EXP_A, "a-r2", 1)
    _insert_rows(mongo_storage, _EXP_B, "b-r1", 2)
    _insert_rows(mongo_storage, _EXP_B, "b-r2", 2)
    try:
        yield mongo_storage
    finally:
        for exp_id in (_EXP_A, _EXP_B):
            mongo_storage.delete_experiment_data(exp_id)


class TestMongoResultsBreakdownLiveShould:
    def test_given_seeded_rows_when_bulk_aggregated_then_per_run_counts_roll_up(
        self, seeded
    ) -> None:
        """
        Scenario: the real two-stage pipeline rolls per-run counts up per experiment.
        Slice: 67E

        Given two experiments with different row counts per run
        When _bulk_result_aggregates runs against MongoDB
        Then totals, distinct query ids and per-run counts match what was inserted.
        """
        ### Given / When
        actual = mongo_stats._bulk_result_aggregates()

        ### Then
        assert actual[_EXP_A]["total_results"] == 4
        assert actual[_EXP_A]["unique_queries"] == 4
        assert sorted(actual[_EXP_A]["results_per_run"]) == [1, 3]
        assert actual[_EXP_B]["total_results"] == 4
        assert sorted(actual[_EXP_B]["results_per_run"]) == [2, 2]

    def test_given_seeded_rows_when_stats_read_then_single_and_grouped_agree(self, seeded) -> None:
        """
        Scenario: single-experiment and grouped paths report the same golden facts.
        Slice: 67E

        Given the seeded experiments (A has a stored golden count, B is inferred)
        When single stats and grouped stats are read from MongoDB
        Then A is (2 runs, golden 3 config, 1 partial) and B is (2 runs, golden 2 inferred,
        0 partial) in both views, and the group totals fold them.
        """
        ### Given / When
        single_a = seeded.get_experiment_db_stats(_EXP_A)
        single_b = seeded.get_experiment_db_stats(_EXP_B)
        grouped = seeded.get_vector_db_stats_grouped()

        ### Then
        assert (single_a["result_runs"], single_a["golden_queries"]) == (2, 3)
        assert (single_a["golden_queries_source"], single_a["partial_runs"]) == ("config", 1)
        assert (single_b["result_runs"], single_b["golden_queries"]) == (2, 2)
        assert (single_b["golden_queries_source"], single_b["partial_runs"]) == ("max_per_run", 0)
        rows = {r["experiment_id"]: r for g in grouped["groups"] for r in g["experiments"]}
        for exp_id, single in ((_EXP_A, single_a), (_EXP_B, single_b)):
            for key in ("result_runs", "golden_queries", "golden_queries_source", "partial_runs"):
                assert rows[exp_id][key] == single[key], (exp_id, key)
        totals = next(g["totals"] for g in grouped["groups"] if rows[_EXP_A] in g["experiments"])
        assert totals["total_result_runs"] >= 4
        assert totals["golden_queries_min"] <= 2
        assert totals["golden_queries_max"] >= 3
