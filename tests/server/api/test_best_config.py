"""
Tests for server.api.sweep best-config history flows.

Author: swami
Created: 2026-07-29
Scope: sweep history persistence, best-config lookup, sparse SPLADE sweep path
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeStorage:
    def __init__(self, docs: list[dict] | None = None) -> None:
        self.docs = docs or []
        self.inserted: list[dict] = []

    def insert_experiment(self, doc: dict) -> None:
        self.inserted.append(doc)
        self.docs.append(doc)

    def find_all_experiments(self) -> list[dict]:
        return list(self.docs)


def _make_client() -> TestClient:
    app = FastAPI()
    from server.api.sweep import router

    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def test_given_sweep_request_when_post_sweep_then_history_is_persisted_via_storage_backend() -> (
    None
):
    """
    Scenario: POST sweep persists lightweight history through StorageBackend.
    Slice: 22 — SIE Scooter

    Given a Tier-1 sweep request and a storage backend double,
    When POST /api/v1/sweep is called,
    Then the sweep history is inserted through the active StorageBackend with ranked configs.
    """
    ### Given
    storage = _FakeStorage()
    mock_embed_docs = MagicMock(return_value=[[0.1, 0.2], [0.2, 0.1]])
    mock_embed_query = MagicMock(return_value=[0.2, 0.2])

    ### When
    with (
        patch("server.api.sweep.get_storage_backend", return_value=storage),
        patch(
            "server.api.sweep.get_embedder",
            return_value=(mock_embed_docs, mock_embed_query),
        ),
        patch("server.api.sweep.AimLogger.log_run"),
    ):
        client = _make_client()
        response = client.post(
            "/api/v1/sweep",
            json={
                "topic": "machine learning",
                "embedding_model": "bge-m3",
                "corpus": ["chunk one", "chunk two"],
            },
        )

    ### Then
    body = response.json()
    assert response.status_code == 200, "Expected sweep endpoint to accept a valid Tier-1 request."
    assert len(storage.inserted) == 1, "Expected sweep history to be persisted exactly once."
    persisted = storage.inserted[0]
    assert persisted["experiment_id"] == body["experiment_id"], (
        "Expected persisted history to match response experiment id."
    )
    assert persisted["experiment_type"] == "tier1_sweep", (
        "Expected persisted history to be marked as a Tier-1 sweep."
    )
    assert persisted["task"] == "machine learning", (
        "Expected task/topic to be stored for later best-config lookup."
    )
    assert persisted["results"], "Expected ranked configs to be stored in the sweep history."


def test_given_sparse_splade_request_when_post_sweep_then_existing_sparse_foundation_is_used() -> (
    None
):
    """
    Scenario: SPLADE sparse-only sweep reuses the existing registry foundation.
    Slice: 22 — SIE Scooter

    Given the existing splade-v3 registry entry and a bm25-only sweep request,
    When POST /api/v1/sweep is called with embedding_model="splade-v3",
    Then the endpoint succeeds without invoking the dense embedder path.
    """
    ### Given
    storage = _FakeStorage()

    ### When
    with (
        patch("server.api.sweep.get_storage_backend", return_value=storage),
        patch("server.api.sweep.get_embedder") as mock_get_embedder,
        patch("server.api.sweep.AimLogger.log_run"),
    ):
        client = _make_client()
        response = client.post(
            "/api/v1/sweep",
            json={
                "topic": "machine learning",
                "embedding_model": "splade-v3",
                "retrieval_methods": ["bm25"],
            },
        )

    ### Then
    body = response.json()
    assert response.status_code == 200, "Expected SPLADE sparse-only sweep request to succeed."
    assert mock_get_embedder.call_count == 0, (
        "Expected sparse-only SPLADE sweep to skip dense embedder dispatch."
    )
    assert body["best_config"]["retrieval_method"] == "bm25", (
        "Expected bm25 to remain the selected sparse retrieval method."
    )
    assert storage.inserted[0]["embedding_model"] == "splade-v3", (
        "Expected persisted history to retain the SPLADE model id."
    )


def test_given_matching_history_when_get_best_config_then_highest_scoring_config_is_returned() -> (
    None
):
    """
    Scenario: GET best-config returns the highest-scoring persisted recommendation.
    Slice: 22 — SIE Scooter

    Given multiple persisted sweep history documents for the same task,
    When GET /api/v1/best-config is called,
    Then the highest-scoring config is returned with HTTP 200.
    """
    ### Given
    now = datetime.now(UTC)
    storage = _FakeStorage(
        [
            {
                "experiment_id": "exp-low",
                "experiment_type": "tier1_sweep",
                "task": "machine learning",
                "completed_at": now,
                "best_config": {
                    "retrieval_method": "dense",
                    "score": 0.72,
                    "embedding_model": "bge-m3",
                },
            },
            {
                "experiment_id": "exp-high",
                "experiment_type": "tier1_sweep",
                "task": "machine learning",
                "completed_at": now,
                "best_config": {
                    "retrieval_method": "hybrid-rrf",
                    "score": 0.83,
                    "embedding_model": "bge-m3",
                },
            },
        ]
    )

    ### When
    with patch("server.api.sweep.get_storage_backend", return_value=storage):
        client = _make_client()
        response = client.get("/api/v1/best-config", params={"task": "machine learning"})

    ### Then
    body = response.json()
    assert response.status_code == 200, (
        "Expected best-config history lookup to succeed when history exists."
    )
    assert body["experiment_id"] == "exp-high", (
        "Expected the highest-scoring history entry to be selected."
    )
    assert body["history_count"] == 2, (
        "Expected history_count to reflect all matching sweep history rows."
    )
    assert body["best_config"]["retrieval_method"] == "hybrid-rrf", (
        "Expected best-config to expose the winning retrieval method."
    )
    assert body["best_config"]["embedding_model"] == "bge-m3", (
        "Expected best-config to expose the winning embedding model."
    )
    assert body["best_config"]["score"] == 0.83, "Expected best-config to expose the winning score."


def test_given_no_matching_history_when_get_best_config_then_404_is_returned() -> None:
    """
    Scenario: GET best-config returns 404 without persisted sweep history.
    Slice: 22 — SIE Scooter

    Given no persisted sweep history for the requested task,
    When GET /api/v1/best-config is called,
    Then the endpoint returns HTTP 404.
    """
    ### Given
    storage = _FakeStorage()

    ### When
    with patch("server.api.sweep.get_storage_backend", return_value=storage):
        client = _make_client()
        response = client.get("/api/v1/best-config", params={"task": "unknown-topic"})

    ### Then
    assert response.status_code == 404, (
        "Expected best-config lookup to return 404 when no history exists."
    )
