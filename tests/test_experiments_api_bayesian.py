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
    Then run_count reflects execution.bayesian.n_trials.
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
    assert body["run_count"] == 12


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
