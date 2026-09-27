"""
Tests for GET /api/stores.

Author: swami
Created: 2026-09-27
Scope: public store catalog, secret redaction, registry example_config
"""

from __future__ import annotations

import json

import pytest

from server.api.stores import build_stores_payload
from server.core.guards.config_backend_guard import format_config_backend_mismatch
from server.db.ports.registry import example_config_for, known_vector_stores
from server.settings import settings


def test_given_registry_when_catalog_built_then_secrets_are_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Scenario: GET /api/stores reports the registry with secrets redacted.
    Slice: 51

    Given configured API keys and connection URIs,
    When the public catalog is built,
    Then every registered store is listed and no secret appears.
    """
    ### Given
    monkeypatch.setattr(settings, "elasticsearch_api_key", "es-secret-key-value")
    monkeypatch.setattr(settings, "mongodb_uri", "mongodb+srv://user:secretpass@cluster.example")
    monkeypatch.setattr(settings, "database_url", "postgresql://rag:secretpass@localhost:5433/rag")
    monkeypatch.setattr(settings, "vector_store_backend", "elasticsearch")

    ### When
    payload = build_stores_payload()
    dumped = json.dumps(payload)

    ### Then
    providers = {row["provider"] for row in payload["stores"]}  # type: ignore[index]
    assert providers == set(known_vector_stores())
    assert payload["active"] == "elasticsearch"
    assert "es-secret-key-value" not in dumped
    assert "secretpass" not in dumped
    assert "mongodb+srv://" not in dumped
    active = next(row for row in payload["stores"] if row["active"])  # type: ignore[union-attr]
    assert active["example_config"] == "configs/elasticsearch/example-local.yaml"
    assert active["labels"]["index"] == "Index"
    assert active["index_summary"]["index"] == "rpf-chunks"


def test_given_elasticsearch_server_when_mismatch_formatted_then_example_config_is_named() -> None:
    """
    Scenario: The config-engine 422 suggests the registry's example config.
    Slice: 51

    Given a YAML engine that is not the active Elasticsearch vector store,
    When the 422 detail is formatted,
    Then it names configs/elasticsearch/example-local.yaml.
    """
    ### Given / When
    detail = format_config_backend_mismatch(
        config_engine="mongodb",
        server_backend="elasticsearch",
        storage_mode="elasticsearch-local",
    )

    ### Then
    assert detail.endswith("configs/elasticsearch/example-local.yaml") or (
        "configs/elasticsearch/example-local.yaml" in detail
    )
    assert example_config_for("elasticsearch") in detail
