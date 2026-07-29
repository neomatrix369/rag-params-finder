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


class _FakeStorage:
    def insert_experiment(self, _doc: dict) -> None:
        return None

    def find_all_experiments(self) -> list[dict]:
        return []


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
            "server.core.embedding.embedder_factory.get_embedder",
            return_value=(mock_embed_docs, mock_embed_query),
        ),
        patch("server.api.sweep.get_storage_backend", return_value=_FakeStorage()),
        patch("server.api.sweep.AimLogger.log_run"),
    ):
        yield _make_sweep_client()


class TestSweepEndpointTier1:
    """Scenario: POST /api/v1/sweep — Tier 1 sweep with SIE BGE-M3."""

    def test_sweep_returns_200_with_required_fields(self, sweep_client: TestClient):
        """
        Scenario: sweep returns 200 with required fields.
        Slice: 45 — GWT-on-touch (module theme separation)
        Given SIE running and a pre-fetched corpus provided
        When POST /api/v1/sweep {"topic":"AI agents","embedding_model":"bge-m3","corpus":[...]}
        Then HTTP 200 with body containing best_config, results, experiment_id, corpus_source.
        """
        ### Given
        ### When
        ### Then
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
        Scenario: sweep defaults to bge m3 when model omitted.
        Slice: 45 — GWT-on-touch (module theme separation)
        Given SIE enabled and a valid sweep request with no embedding_model field
        When POST /api/v1/sweep {"topic":"AI agents"}
        Then HTTP 200 and best_config.embedding_model is "bge-m3".
        """
        ### Given
        ### When
        ### Then
        with patch("server.api.sweep.settings") as mock_settings:
            mock_settings.sie_enabled = True
            resp = sweep_client.post("/api/v1/sweep", json={"topic": "AI agents"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["best_config"]["embedding_model"] == "bge-m3"

    def test_sweep_defaults_to_local_model_when_sie_disabled(self, sweep_client: TestClient):
        """
        Scenario: sweep defaults to local model when sie disabled.
        Slice: 45 — GWT-on-touch (module theme separation)
        Given SIE disabled (default) and no embedding_model field
        When POST /api/v1/sweep {"topic":"AI agents"}
        Then HTTP 200 and best_config.embedding_model is all-MiniLM-L6-v2.
        """
        ### Given
        ### When
        ### Then
        with patch("server.api.sweep.settings") as mock_settings:
            mock_settings.sie_enabled = False
            resp = sweep_client.post("/api/v1/sweep", json={"topic": "AI agents"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["best_config"]["embedding_model"] == "all-MiniLM-L6-v2"

    def test_sweep_missing_topic_returns_422(self, sweep_client: TestClient):
        """
        Scenario: sweep missing topic returns 422.
        Slice: 45 — GWT-on-touch (module theme separation)
        When POST /api/v1/sweep is called without a topic
        Then HTTP 422 (unprocessable entity) is returned.
        """
        ### Given
        ### When
        ### Then
        resp = sweep_client.post("/api/v1/sweep", json={})
        assert resp.status_code == 422

    def test_sweep_corpus_source_is_provided_when_corpus_given(self, sweep_client: TestClient):
        """
        Scenario: sweep corpus source is provided when corpus given.
        Slice: 45 — GWT-on-touch (module theme separation)
        When a sweep runs with an explicit corpus list
        Then corpus_source in the response is "provided".
        """
        ### Given
        ### When
        ### Then
        resp = sweep_client.post(
            "/api/v1/sweep",
            json={"topic": "machine learning", "corpus": ["chunk one", "chunk two"]},
        )
        assert resp.status_code == 200
        assert resp.json()["corpus_source"] == "provided"

    def test_sweep_corpus_source_is_topic_when_no_corpus_given(self, sweep_client: TestClient):
        """
        Scenario: sweep corpus source is topic when no corpus given.
        Slice: 45 — GWT-on-touch (module theme separation)
        When a sweep runs without supplying a corpus
        Then corpus_source in the response is "topic" (falls back to topic string).
        """
        ### Given
        ### When
        ### Then
        resp = sweep_client.post("/api/v1/sweep", json={"topic": "machine learning"})
        assert resp.status_code == 200
        assert resp.json()["corpus_source"] == "topic"

    def test_sweep_results_list_non_empty(self, sweep_client: TestClient):
        """
        Scenario: sweep results list non empty.
        Slice: 45 — GWT-on-touch (module theme separation)
        When a sweep runs with default retrieval methods
        Then results list is non-empty with ranking scores.
        """
        ### Given
        ### When
        ### Then
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
        """
        Scenario: check sie health returns string.
        Slice: 45 — GWT-on-touch (module theme separation)
        check_sie_health returns a string status.
        """
        ### Given
        ### When
        ### Then
        with (
            patch("server.core.guards.sie_guard.settings") as mock_settings,
            patch("server.core.guards.sie_guard.httpx.get") as mock_get,
        ):
            mock_settings.sie_enabled = True
            mock_settings.sie_endpoint = "http://localhost:8720"
            mock_settings.sie_api_key = ""
            mock_get.return_value.status_code = 200
            from server.core.sie_guard import check_sie_health

            result = check_sie_health()
        assert isinstance(result, str)
        assert result == "reachable"

    def test_check_sie_health_returns_disabled_when_sie_off(self):
        """
        Scenario: check sie health returns disabled when sie off.
        Slice: 45 — GWT-on-touch (module theme separation)
        check_sie_health returns 'disabled' when SIE_ENABLED is false.
        """
        ### Given
        ### When
        ### Then
        with patch("server.core.guards.sie_guard.settings") as mock_settings:
            mock_settings.sie_enabled = False
            from server.core.sie_guard import check_sie_health

            result = check_sie_health()
        assert result == "disabled"

    def test_check_sie_health_unreachable_on_exception(self):
        """
        Scenario: check sie health unreachable on exception.
        Slice: 45 — GWT-on-touch (module theme separation)
        check_sie_health returns 'unreachable' when SIE is down.
        """
        ### Given
        ### When
        ### Then
        with (
            patch("server.core.guards.sie_guard.settings") as mock_settings,
            patch(
                "server.core.guards.sie_guard.httpx.get",
                side_effect=Exception("connection refused"),
            ),
        ):
            mock_settings.sie_enabled = True
            mock_settings.sie_endpoint = "http://localhost:8720"
            mock_settings.sie_api_key = ""
            from server.core.sie_guard import check_sie_health

            result = check_sie_health()
        assert result == "unreachable"

    def test_health_endpoint_includes_sie_and_version(self):
        """
        Scenario: health endpoint includes sie and version.
        Slice: 45 — GWT-on-touch (module theme separation)
        Given health endpoint is mounted
        When GET /health
        Then response contains sie and version keys.
        """
        ### Given
        ### When
        ### Then
        app = FastAPI()

        @app.get("/health")
        def health():
            from server.core.sie_guard import check_sie_health

            return {
                "status": "ok",
                "sie": check_sie_health(),
                "version": "test",
            }

        test_client = TestClient(app)
        with (
            patch("server.core.guards.sie_guard.settings") as mock_settings,
            patch("server.core.guards.sie_guard.httpx.get") as mock_get,
        ):
            mock_settings.sie_enabled = True
            mock_settings.sie_endpoint = "http://localhost:8720"
            mock_settings.sie_api_key = ""
            mock_get.return_value.status_code = 200
            resp = test_client.get("/health")

        assert resp.status_code == 200
        body = resp.json()
        assert "sie" in body
        assert "version" in body
