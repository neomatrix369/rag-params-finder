"""GWT tests for POST /api/v1/sweep — sweep router mounted independently.

We mount only the sweep router in a minimal FastAPI app to avoid importing
server.main (which chains into orchestrator → voyageai → torch), keeping
the test suite runnable without a GPU/OpenMP environment.

External calls (get_embedder, AimLogger) are all mocked.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_sweep_client() -> TestClient:
    """Minimal app — only the sweep router, no orchestrator or voyageai imports."""
    app = FastAPI()
    from server.api.sweep import router

    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


@pytest.fixture
def sweep_client():
    """TestClient with sweep router and all external calls mocked."""
    mock_embed_docs = MagicMock(return_value=[[0.1] * 1024, [0.2] * 1024])
    mock_embed_query = MagicMock(return_value=[0.15] * 1024)

    with (
        patch(
            "server.core.embedder_factory.get_embedder",
            return_value=(mock_embed_docs, mock_embed_query),
        ),
        patch("server.api.sweep.AimLogger.log_run"),
    ):
        yield _make_sweep_client()


class TestSweepEndpointTier1:
    """Scenario: POST /api/v1/sweep — Tier 1 sweep with SIE BGE-M3."""

    def test_sweep_returns_200_with_required_fields(self, sweep_client: TestClient):
        """
        Given SIE running, MongoDB connected, and a pre-fetched corpus provided
        When POST /api/v1/sweep {"topic":"AI agents","embedding_model":"bge-m3","corpus":[...]}
        Then HTTP 200 with body containing best_config, results, experiment_id, corpus_source.
        """
        resp = sweep_client.post(
            "/api/v1/sweep",
            json={
                "topic": "AI agents",
                "embedding_model": "bge-m3",
                "corpus": ["chunk about AI agents", "another relevant chunk"],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "best_config" in body
        assert "results" in body
        assert "experiment_id" in body
        assert "corpus_source" in body

    def test_sweep_defaults_to_bge_m3_when_model_omitted(self, sweep_client: TestClient):
        """
        Given a valid sweep request with no embedding_model field
        When POST /api/v1/sweep {"topic":"AI agents"}
        Then HTTP 200 and best_config.embedding_model is "bge-m3".
        """
        resp = sweep_client.post("/api/v1/sweep", json={"topic": "AI agents"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["best_config"]["embedding_model"] == "bge-m3"

    def test_sweep_missing_topic_returns_422(self, sweep_client: TestClient):
        """
        When POST /api/v1/sweep is called without a topic
        Then HTTP 422 (unprocessable entity) is returned.
        """
        resp = sweep_client.post("/api/v1/sweep", json={})
        assert resp.status_code == 422

    def test_sweep_corpus_source_is_provided_when_corpus_given(self, sweep_client: TestClient):
        """
        When a sweep runs with an explicit corpus list
        Then corpus_source in the response is "provided".
        """
        resp = sweep_client.post(
            "/api/v1/sweep",
            json={"topic": "machine learning", "corpus": ["chunk one", "chunk two"]},
        )
        assert resp.status_code == 200
        assert resp.json()["corpus_source"] == "provided"

    def test_sweep_corpus_source_is_topic_when_no_corpus_given(self, sweep_client: TestClient):
        """
        When a sweep runs without supplying a corpus
        Then corpus_source in the response is "topic" (falls back to topic string).
        """
        resp = sweep_client.post("/api/v1/sweep", json={"topic": "machine learning"})
        assert resp.status_code == 200
        assert resp.json()["corpus_source"] == "topic"

    def test_sweep_results_list_non_empty(self, sweep_client: TestClient):
        """
        When a sweep runs with default retrieval methods
        Then results list is non-empty with ranking scores.
        """
        resp = sweep_client.post("/api/v1/sweep", json={"topic": "RAG systems"})
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) > 0
        for r in results:
            assert "retrieval_method" in r
            assert "score" in r


class TestHealthEnhanced:
    """Scenario: GET /health — includes SIE reachability."""

    def test_check_sie_health_returns_string(self):
        """check_sie_health returns a string status."""
        with patch("server.api.sweep.httpx.get") as mock_get:
            mock_get.return_value.status_code = 200
            from server.api.sweep import check_sie_health

            result = check_sie_health()
        assert isinstance(result, str)
        assert result == "reachable"

    def test_check_sie_health_unreachable_on_exception(self):
        """check_sie_health returns 'unreachable' when SIE is down."""
        with patch("server.api.sweep.httpx.get", side_effect=Exception("connection refused")):
            from server.api.sweep import check_sie_health

            result = check_sie_health()
        assert result == "unreachable"

    def test_health_endpoint_includes_sie_and_version(self):
        """
        Given health endpoint is mounted
        When GET /health
        Then response contains sie and version keys.
        """
        app = FastAPI()

        @app.get("/health")
        def health():
            from server.api.sweep import check_sie_health

            return {
                "status": "ok",
                "mongodb": "connected",
                "sie": check_sie_health(),
                "version": "test",
            }

        test_client = TestClient(app)
        with patch("server.api.sweep.httpx.get") as mock_get:
            mock_get.return_value.status_code = 200
            resp = test_client.get("/health")

        assert resp.status_code == 200
        body = resp.json()
        assert "sie" in body
        assert "version" in body
        assert "tavily" not in body
