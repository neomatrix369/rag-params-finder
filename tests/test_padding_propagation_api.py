"""API smoke tests for Slice 29 — padding in explore and experiment detail responses."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_experiments_client() -> TestClient:
    app = FastAPI()
    from server.api.experiments import router

    app.include_router(router, prefix="/experiments")
    return TestClient(app)


def _padding_run_statuses() -> list[dict]:
    base = {
        "experiment_id": "exp-padding-smoke",
        "phase": "complete",
        "database_provider": "mongodb",
        "embedding_provider": "local",
        "embedding_model": "all-MiniLM-L6-v2",
        "chunking_method": "semantic",
        "chunk_size": 512,
        "overlap": 50,
        "retrieval_method": "sparse",
        "retrieval_provider": "local",
        "retrievers": [{"type": "sparse"}],
        "created_at": "2026-07-06T00:00:00Z",
        "updated_at": "2026-07-06T00:01:00Z",
        "elapsed_ms": 1000,
    }
    return [
        {**base, "run_id": "run-pad-0", "padding": 0},
        {**base, "run_id": "run-pad-50", "padding": 50},
    ]


def _padding_query_results() -> list[dict]:
    return [
        {
            "run_id": "run-pad-0",
            "query_text": "query1",
            "results": [
                {"dense_score": 1.0, "chunk": {"text": "chunk-a"}, "retrieval_method": "sparse"},
            ],
        },
        {
            "run_id": "run-pad-50",
            "query_text": "query1",
            "results": [
                {"dense_score": 1.0, "chunk": {"text": "chunk-b"}, "retrieval_method": "sparse"},
            ],
        },
    ]


@pytest.fixture
def experiments_client() -> TestClient:
    return _make_experiments_client()


class TestPaddingExploreApiSmoke:
    """Scenario: GET /experiments/{id}/explore exposes padding on ranked configs."""

    def test_explore_returns_two_ranked_configs_when_runs_differ_only_by_padding(
        self, experiments_client: TestClient
    ) -> None:
        experiment_doc = {
            "experiment_id": "exp-padding-smoke",
            "experiment_name": "padding-smoke",
        }
        explore_source = (experiment_doc, _padding_query_results(), _padding_run_statuses())

        with patch(
            "server.api.experiments.mongo_load_explore_source",
            return_value=explore_source,
        ):
            resp = experiments_client.get("/experiments/exp-padding-smoke/explore")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["ranked_configs"]) == 2
        paddings = sorted(c["padding"] for c in body["ranked_configs"])
        assert paddings == [0, 50]
        assert {d["padding"] for d in body["detailed_results"]} == {0, 50}


class TestPaddingExperimentDetailApiSmoke:
    """Scenario: GET /experiments/{id} returns per-run padding for detail UI."""

    def test_experiment_detail_includes_padding_on_each_run(
        self, experiments_client: TestClient
    ) -> None:
        experiment = {
            "experiment_id": "exp-padding-smoke",
            "experiment_name": "padding-smoke",
            "status": "complete",
            "sweep_summary": {
                "database_provider": "mongodb",
                "embedding_provider": "local",
                "models": ["all-MiniLM-L6-v2"],
                "chunking_methods": ["semantic"],
                "chunk_sizes": [512],
                "overlaps": [50],
                "paddings": [0, 50],
                "retrieval_methods": ["sparse"],
                "retrieval_provider": "local",
            },
            "runs": _padding_run_statuses(),
        }

        with patch(
            "server.api.experiments.mongo_find_experiment_with_runs",
            return_value=experiment,
        ):
            resp = experiments_client.get("/experiments/exp-padding-smoke")

        assert resp.status_code == 200
        body = resp.json()
        assert body["sweep_summary"]["paddings"] == [0, 50]
        run_paddings = sorted(run["padding"] for run in body["runs"])
        assert run_paddings == [0, 50]
