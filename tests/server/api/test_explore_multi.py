"""
Tests for GET /api/v1/explore/multi (Slice 66 — selection-based merged leaderboard).

Author: swami
Created: 2026-11-06
Scope: explore_multi endpoint — dataset compatibility check, 404 handling, merge path.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api.explore_multi import router


def _exp(exp_id: str, data_paths: list[str], queries_file: str, name: str = "") -> dict:
    return {
        "experiment_id": exp_id,
        "experiment_name": name or exp_id,
        "status": "complete",
        "config": {"data_paths": data_paths, "queries_file": queries_file},
    }


def _run(run_id: str, exp_id: str) -> dict:
    return {
        "run_id": run_id,
        "experiment_id": exp_id,
        "database_provider": "redis",
        "phase": "complete",
        "embedding_provider": "local",
        "embedding_model": "all-MiniLM-L6-v2",
        "chunking_method": "recursive",
        "chunk_size": 512,
        "overlap": 0,
        "padding": 0,
        "retrieval_method": "dense",
    }


def _result(run_id: str, score: float = 0.8) -> dict:
    return {
        "run_id": run_id,
        "query_text": "q1",
        "results": [{"dense_score": score, "retrieval_method": "dense", "chunk": {"text": "t"}}],
    }


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def _source(exp: dict, runs: list[dict], results: list[dict]):
    return (exp, results, runs)


@pytest.fixture()
def client():
    return _client()


def test_given_fewer_than_two_ids_when_called_then_422(client: TestClient) -> None:
    """
    Scenario: At least 2 IDs are required.
    Slice: 66

    Given a single experiment ID in the query,
    When GET /api/v1/explore/multi is called,
    Then 422 is returned.
    """
    ### Given / When
    response = client.get("/api/v1/explore/multi?ids=e1")

    ### Then
    assert response.status_code == 422


def test_given_unknown_experiment_when_called_then_404(client: TestClient) -> None:
    """
    Scenario: One of the requested experiments does not exist.
    Slice: 66

    Given an ID that resolve to None from the storage backend,
    When GET /api/v1/explore/multi is called,
    Then 404 is returned.
    """
    ### Given
    missing_source = (None, [], [])

    ### When
    with patch("server.api.explore_multi.load_explore_source", return_value=missing_source):
        response = client.get("/api/v1/explore/multi?ids=e1&ids=e2")

    ### Then
    assert response.status_code == 404


def test_given_different_data_paths_when_called_then_422(client: TestClient) -> None:
    """
    Scenario: Incompatible datasets block the compare.
    Slice: 66

    Given two experiments with different data_paths,
    When GET /api/v1/explore/multi is called,
    Then 422 is returned with a clear message.
    """
    ### Given
    exp1 = _exp("e1", ["pell.pdf"], "q.json")
    exp2 = _exp("e2", ["other.pdf"], "q.json")
    sources = {
        "e1": _source(exp1, [_run("r1", "e1")], [_result("r1")]),
        "e2": _source(exp2, [_run("r2", "e2")], [_result("r2")]),
    }

    ### When
    with (
        patch(
            "server.api.explore_multi.load_explore_source",
            side_effect=lambda exp_id: sources[exp_id],
        ),
        patch("server.api.explore_multi._questions_sha", return_value=""),
    ):
        response = client.get("/api/v1/explore/multi?ids=e1&ids=e2")

    ### Then
    assert response.status_code == 422
    assert "different datasets" in response.json()["detail"]


def test_given_two_compatible_experiments_when_called_then_merged_results_returned(
    client: TestClient,
) -> None:
    """
    Scenario: Two compatible experiments produce a merged leaderboard.
    Slice: 66

    Given two experiments on the same dataset and questions file,
    When GET /api/v1/explore/multi is called,
    Then 200 is returned with both experiment_ids and a ranked_configs list.
    """
    ### Given
    exp1 = _exp("e1", ["pell.pdf"], "q.json", name="exp-one")
    exp2 = _exp("e2", ["pell.pdf"], "q.json", name="exp-two")
    sources = {
        "e1": _source(exp1, [_run("r1", "e1")], [_result("r1", 0.9)]),
        "e2": _source(exp2, [_run("r2", "e2")], [_result("r2", 0.5)]),
    }

    ### When
    with (
        patch(
            "server.api.explore_multi.load_explore_source",
            side_effect=lambda exp_id: sources[exp_id],
        ),
        patch("server.api.explore_multi._questions_sha", return_value="sha123"),
    ):
        response = client.get("/api/v1/explore/multi?ids=e1&ids=e2")

    ### Then
    assert response.status_code == 200
    body = response.json()
    assert body["experiment_ids"] == ["e1", "e2"]
    assert body["experiment_names"] == ["exp-one", "exp-two"]
    assert len(body["ranked_configs"]) >= 1
