"""
Tests for server.core.compare and GET /api/v1/compare.

Author: swami
Created: 2026-11-05
Scope: SLICE-66 live cross-store compare — grouping, per-group ranking, API wiring
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from server.core.compare import build_compare, count_duplicates_collapsed


def _experiment(
    exp_id: str, store: str, *, queries: str = "q.json", day: int = 1, status: str = "complete"
) -> dict:
    return {
        "experiment_id": exp_id,
        "experiment_name": exp_id,
        "status": status,
        "created_at": datetime(2026, 11, day, tzinfo=UTC),
        "config": {"database_provider": store, "data_paths": ["pell.pdf"], "queries_file": queries},
    }


def _run(
    run_id: str, exp_id: str, store: str, *, chunk_size: int = 512, phase: str = "complete"
) -> dict:
    return {
        "run_id": run_id,
        "experiment_id": exp_id,
        "database_provider": store,
        "phase": phase,
        "embedding_provider": "local",
        "embedding_model": "all-MiniLM-L6-v2",
        "chunking_method": "recursive",
        "chunk_size": chunk_size,
        "overlap": 0,
        "padding": 0,
        "retrieval_method": "dense",
        "elapsed_ms": 1000,
    }


def _result(run_id: str, score: float) -> dict:
    return {
        "run_id": run_id,
        "query_text": "q1",
        "results": [{"dense_score": score, "retrieval_method": "dense", "chunk": {"text": "t"}}],
    }


def _bundle(exp: dict, runs: list[dict], scores: dict[str, float]) -> tuple:
    return exp, runs, [_result(rid, s) for rid, s in scores.items()]


def test_given_same_config_on_two_stores_when_compared_then_one_group_ranks_both() -> None:
    """
    Scenario: A Redis run and a MongoDB run of the same config share one group.
    Slice: 66

    Given two completed experiments on different stores with the same dataset, questions and config,
    When build_compare runs,
    Then one cross-store group holds both runs, the higher-scoring one ranked first.
    """
    ### Given
    bundles = [
        _bundle(_experiment("e1", "redis"), [_run("r1", "e1", "redis")], {"r1": 0.9}),
        _bundle(_experiment("e2", "mongodb"), [_run("r2", "e2", "mongodb")], {"r2": 0.5}),
    ]

    ### When
    out = build_compare(bundles)

    ### Then
    assert out["group_count"] == 1
    assert out["cross_store_group_count"] == 1
    assert [r["run_id"] for r in out["groups"][0]["runs"]] == ["r1", "r2"]
    assert out["groups"][0]["runs"][0]["rank"] == 1
    assert out["stores"] == ["mongodb", "redis"]


def test_given_different_questions_files_when_compared_then_runs_stay_in_separate_groups() -> None:
    """
    Scenario: Scores are never compared across different question sets.
    Slice: 66

    Given the same config on two stores but different queries files,
    When build_compare runs,
    Then two groups are returned and neither spans stores.
    """
    ### Given
    bundles = [
        _bundle(
            _experiment("e1", "redis", queries="a.json"), [_run("r1", "e1", "redis")], {"r1": 0.9}
        ),
        _bundle(
            _experiment("e2", "mongodb", queries="b.json"),
            [_run("r2", "e2", "mongodb")],
            {"r2": 0.5},
        ),
    ]

    ### When
    out = build_compare(bundles)

    ### Then
    assert out["group_count"] == 2
    assert out["cross_store_group_count"] == 0


def test_given_unfinished_or_failed_work_when_compared_then_it_is_skipped() -> None:
    """
    Scenario: Only completed runs of complete/partial experiments with results count.
    Slice: 66

    Given a running experiment, a run not in phase complete, and a complete run with no results,
    When build_compare runs,
    Then no groups are returned.
    """
    ### Given
    bundles = [
        _bundle(
            _experiment("e1", "redis", status="running"), [_run("r1", "e1", "redis")], {"r1": 0.9}
        ),
        _bundle(
            _experiment("e2", "redis"), [_run("r2", "e2", "redis", phase="embedding")], {"r2": 0.9}
        ),
        (_experiment("e3", "redis"), [_run("r3", "e3", "redis")], []),
    ]

    ### When
    out = build_compare(bundles)

    ### Then
    assert out["groups"] == []
    assert out["run_count"] == 0


def test_given_two_experiments_for_one_store_and_config_when_compared_then_latest_wins() -> None:
    """
    Scenario: Re-running a config on the same store supersedes the older experiment.
    Slice: 66

    Given an older and a newer Redis experiment with the same config,
    When build_compare runs,
    Then only the newer experiment's run is listed.
    """
    ### Given
    bundles = [
        _bundle(
            _experiment("old", "redis", day=1), [_run("r-old", "old", "redis")], {"r-old": 0.9}
        ),
        _bundle(
            _experiment("new", "redis", day=2), [_run("r-new", "new", "redis")], {"r-new": 0.4}
        ),
    ]

    ### When
    out = build_compare(bundles)

    ### Then
    assert [r["run_id"] for r in out["groups"][0]["runs"]] == ["r-new"]


def test_given_two_groups_when_compared_then_best_group_comes_first() -> None:
    """
    Scenario: Groups are ordered by their top run's max score.
    Slice: 66

    Given two configs (chunk 256 and chunk 512) where 512 scores higher,
    When build_compare runs,
    Then the 512 group is listed first.
    """
    ### Given
    exp = _experiment("e1", "redis")
    runs = [
        _run("r256", "e1", "redis", chunk_size=256),
        _run("r512", "e1", "redis", chunk_size=512),
    ]
    bundles = [_bundle(exp, runs, {"r256": 0.2, "r512": 0.9})]

    ### When
    out = build_compare(bundles)

    ### Then
    assert [g["runs"][0]["run_id"] for g in out["groups"]] == ["r512", "r256"]


def test_given_run_whose_queries_retrieved_nothing_when_compared_then_it_is_left_out() -> None:
    """
    Scenario: An empty result list must not crash the endpoint.
    Slice: 66

    Given a completed run whose only result document has no retrieved chunks,
    When build_compare runs,
    Then no group is returned and nothing raises.
    """
    ### Given
    exp = _experiment("e1", "redis")
    empty = {"run_id": "r1", "query_text": "q1", "results": []}

    ### When
    out = build_compare([(exp, [_run("r1", "e1", "redis")], [empty])])

    ### Then
    assert out["groups"] == []
    assert out["run_count"] == 0


def test_given_two_same_store_runs_with_one_config_key_when_compared_then_one_run_is_kept() -> None:
    """
    Scenario: Runs that cannot be told apart must not have their scores merged.
    Slice: 66

    Given two runs of one experiment on one store with an identical config key,
    When build_compare runs,
    Then a single run (the lowest run id) represents that store in the group.
    """
    ### Given
    exp = _experiment("e1", "redis")
    runs = [_run("rB", "e1", "redis"), _run("rA", "e1", "redis")]

    ### When
    out = build_compare([_bundle(exp, runs, {"rA": 0.9, "rB": 0.1})])

    ### Then
    assert [r["run_id"] for r in out["groups"][0]["runs"]] == ["rA"]


def test_given_two_experiments_for_one_slot_when_compared_then_one_duplicate_is_reported() -> None:
    """
    Scenario: The response says how many rows the one-run-per-slot rule removed.
    Slice: 67F

    Given an older and a newer Redis experiment with the same config,
    When build_compare runs,
    Then duplicates_collapsed is 1 and the group still lists one run.
    """
    ### Given
    bundles = [
        _bundle(_experiment("old", "redis", day=1), [_run("r1", "old", "redis")], {"r1": 0.9}),
        _bundle(_experiment("new", "redis", day=2), [_run("r2", "new", "redis")], {"r2": 0.4}),
    ]

    ### When
    out = build_compare(bundles)

    ### Then
    assert out["duplicates_collapsed"] == 1
    assert out["run_count"] == 1


def test_given_distinct_slots_when_compared_then_no_duplicates_are_reported() -> None:
    """
    Scenario: Nothing is collapsed when every (store, group) slot has one run.
    Slice: 67F

    Given one Redis and one MongoDB experiment with the same config,
    When build_compare runs,
    Then duplicates_collapsed is 0.
    """
    ### Given
    bundles = [
        _bundle(_experiment("a", "redis"), [_run("r1", "a", "redis")], {"r1": 0.9}),
        _bundle(_experiment("b", "mongodb"), [_run("r2", "b", "mongodb")], {"r2": 0.8}),
    ]

    ### When
    out = build_compare(bundles)

    ### Then
    assert out["duplicates_collapsed"] == 0
    assert out["run_count"] == 2


@pytest.mark.parametrize(
    ("slot_keys", "expected"),
    [
        ([], 0),
        ([("redis", "g1")], 0),
        ([("redis", "g1"), ("mongodb", "g1"), ("redis", "g2")], 0),
        ([("redis", "g1"), ("redis", "g1")], 1),
        ([("redis", "g1")] * 5, 4),
        (
            [
                ("redis", "g1"),
                ("redis", "g1"),
                ("mongodb", "g1"),
                ("mongodb", "g1"),
                ("redis", "g2"),
            ],
            2,
        ),
    ],
    ids=["empty", "single", "all-distinct", "one-pair", "many-same-slot", "two-slots-duplicated"],
)
def test_given_slot_keys_when_counting_then_collapsed_is_total_minus_distinct(
    slot_keys: list[tuple[str, str]], expected: int
) -> None:
    """
    Scenario: The collapsed count is a pure function of the (store, group) keys.
    Slice: 67F

    Given a list of (store, group) keys,
    When count_duplicates_collapsed is called,
    Then it returns the number of keys beyond the first of each distinct key.
    """
    ### Given / When
    result = count_duplicates_collapsed(slot_keys)

    ### Then
    assert result == expected
