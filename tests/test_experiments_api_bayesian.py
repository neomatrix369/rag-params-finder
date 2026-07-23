"""API tests for Bayesian execution strategy on /experiments."""

from __future__ import annotations

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_experiments_client() -> TestClient:
    app = FastAPI()
    from server.api.experiments import router

    app.include_router(router, prefix="/experiments")
    return TestClient(app)


_BAYESIAN_CONFIG = {
    "experiment_name": "example-bayesian-api",
    "data_paths": ["./input_data/pdfs/The_Federal_Pell_Grant_Program.pdf"],
    "queries_file": "./configs/questions.example.json",
    "database_provider": "mongodb",
    "embedding": {
        "provider": "local",
        "models": ["all-MiniLM-L6-v2"],
    },
    "chunking": {
        "methods": ["recursive"],
        "params": {
            "chunk_sizes": [256, 512, 768],
            "overlaps": [0, 50],
            "paddings": [0],
        },
    },
    "retrieval": {
        "top_k_initial": 20,
        "top_k_final": 5,
        "retrievers": [{"type": "dense"}],
    },
    "execution": {
        "search_strategy": "bayesian",
        "bayesian": {"n_trials": 12},
    },
}


def test_create_experiment_reports_bayesian_n_trials_as_run_count() -> None:
    """
    Scenario: POST /experiments for bayesian config reports planned Bayesian count.

    Given a valid bayesian configuration with chunk_size × overlap search space
    When create request is submitted
    Then run_count reflects the capped bayesian run count.
    """
    with (
        patch("server.api.experiments.validate_experiment_search_indexes"),
        patch("server.api.experiments.validate_sie_readiness"),
        patch("server.api.experiments.mongo_insert_experiment_doc"),
        patch("server.api.experiments.schedule_sweep"),
    ):
        client = _make_experiments_client()
        response = client.post("/experiments", json=_BAYESIAN_CONFIG)

    assert response.status_code == 200
    body = response.json()
    assert body["run_count"] == 6


def test_resume_bayesian_experiment_returns_409() -> None:
    """
    Scenario: POST /experiments/{id}/resume rejects bayesian experiments.

    Given a persisted bayesian experiment marked PAUSED
    When resume endpoint is called
    Then HTTP 409 is returned with a non-empty message.
    """
    experiment_doc = {
        "_id": "exp-bayesian",
        "status": "paused",
        "config": _BAYESIAN_CONFIG,
    }

    with (
        patch("server.api.experiments.mongo_find_experiment_by_id", return_value=experiment_doc),
        patch("server.api.experiments.mongo_mark_experiment_running"),
        patch("server.api.experiments.schedule_sweep"),
    ):
        client = _make_experiments_client()
        response = client.post("/experiments/exp-bayesian/resume")

    assert response.status_code == 409
    assert response.json()["detail"]


def test_detail_bayesian_experiment_populates_progress_summary_when_missing() -> None:
    """
    Scenario: GET /experiments/{id} exposes Bayesian summary even before finalization.

    Given a running Bayesian experiment without persisted summary metadata
    And run rows exist for partial progress
    When detail is requested
    Then response includes a normalized `bayesian_summary` with attempts and not-started.
    """
    experiment_doc = {
        "_id": "exp-bayesian-summary",
        "experiment_id": "exp-bayesian-summary",
        "status": "running",
        "run_count": 100,
        "grid_equivalent_count": 100,
        "config": {
            "execution": {"search_strategy": "bayesian"},
        },
        "runs": [
            {"phase": "complete", "run_id": "run-1"},
            {"phase": "complete", "run_id": "run-2"},
            {"phase": "querying", "run_id": "run-3"},
        ],
        "completed_at": None,
    }

    with (
        patch(
            "server.api.experiments.mongo_find_experiment_with_runs",
            return_value=experiment_doc,
        ),
    ):
        client = _make_experiments_client()
        response = client.get("/experiments/exp-bayesian-summary")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    bayesian_summary = body["bayesian_summary"]
    assert bayesian_summary["planned_trials"] == 100
    assert bayesian_summary["attempted_trials"] == 3
    assert bayesian_summary["discarded_trials"] == 0
    assert bayesian_summary["not_started"] == 97


def test_detail_bayesian_experiment_passes_through_trial_log() -> None:
    """
    Scenario: GET /experiments/{id} passes trial_log from bayesian_summary to client.

    Given a completed Bayesian experiment with a stored trial_log in its bayesian_summary
    When the detail endpoint is queried
    Then the response includes trial_log with the correct entry structure.
    """
    experiment_doc = {
        "_id": "exp-bayesian-trial-log",
        "experiment_id": "exp-bayesian-trial-log",
        "status": "complete",
        "run_count": 3,
        "grid_equivalent_count": 4,
        "config": {"execution": {"search_strategy": "bayesian"}},
        "bayesian_summary": {
            "planned_trials": 3,
            "attempted_trials": 3,
            "discarded_trials": 1,
            "not_started": 0,
            "grid_equivalent_count": 4,
            "best_query_avg_score": 0.85,
            "best_chunk_size": 512,
            "best_overlap": 50,
            "trial_log": [
                {"chunk_size": 256, "overlap": 0, "state": "completed", "score": 0.72},
                {"chunk_size": 512, "overlap": 50, "state": "completed", "score": 0.85},
                {"chunk_size": 256, "overlap": 0, "state": "pruned", "score": None},
                {"chunk_size": 768, "overlap": 100, "state": "completed", "score": 0.78},
            ],
        },
        "runs": [
            {"phase": "complete", "run_id": "run-1"},
            {"phase": "complete", "run_id": "run-2"},
            {"phase": "complete", "run_id": "run-3"},
        ],
        "completed_at": "2026-07-23T10:00:00+00:00",
    }

    with (
        patch(
            "server.api.experiments.mongo_find_experiment_with_runs",
            return_value=experiment_doc,
        ),
    ):
        client = _make_experiments_client()
        response = client.get("/experiments/exp-bayesian-trial-log")

    assert response.status_code == 200
    body = response.json()
    trial_log = body["bayesian_summary"]["trial_log"]
    assert len(trial_log) == 4
    completed = [e for e in trial_log if e["state"] == "completed"]
    pruned = [e for e in trial_log if e["state"] == "pruned"]
    assert len(completed) == 3
    assert len(pruned) == 1
    assert all(isinstance(e["score"], float) for e in completed)
    assert pruned[0]["score"] is None
    assert pruned[0]["chunk_size"] == 256


def test_detail_partial_bayesian_experiment_populates_summary_from_runs() -> None:
    """
    Scenario: GET /experiments/{id} includes Bayesian summary for partial runs.

    Given a partially completed Bayesian experiment
    And the document has no stored bayesian_summary
    When the detail endpoint is queried
    Then summary is derived from the observed run rows.
    """
    experiment_doc = {
        "_id": "exp-bayesian-partial",
        "experiment_id": "exp-bayesian-partial",
        "status": "partial",
        "run_count": 100,
        "config": {"execution": {"search_strategy": "bayesian"}},
        "runs": [{"phase": "complete", "run_id": "run-1"}] * 79,
        "completed_at": "2026-07-21T15:34:04.225000+00:00",
    }

    with (
        patch(
            "server.api.experiments.mongo_find_experiment_with_runs",
            return_value=experiment_doc,
        ),
    ):
        client = _make_experiments_client()
        response = client.get("/experiments/exp-bayesian-partial")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial"
    bayesian_summary = body["bayesian_summary"]
    assert bayesian_summary["planned_trials"] == 100
    assert bayesian_summary["attempted_trials"] == 79
    assert bayesian_summary["discarded_trials"] == 0
    assert bayesian_summary["not_started"] == 21
