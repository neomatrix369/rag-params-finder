"""GWT tests for config validation and CLI submit timeout.

Author: Codex
Created: 2026-07-20
Scope: Legacy/explicit retrievers, parallelism bounds, embedding/retrieval validation, CLI timeout.
"""

from __future__ import annotations

import importlib

import pytest
from pydantic import ValidationError

import cli.api_client
from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExperimentConfig,
    RetrievalConfig,
    RetrieverConfig,
    expand_sweep,
)
from server.models.enums import (
    ChunkingMethod,
    RetrievalMethod,
    RetrieverType,
)
from tests.helpers.pipeline_sweep import _slice_config


def test_legacy_methods_are_ignored_when_retrievers_explicitly_set() -> None:
    """
    Scenario: explicit retrievers disable legacy method migration.
    """
    config = ExperimentConfig(
        experiment_name="legacy-has-overrides",
        data_paths=["./data"],
        queries_file="./queries.json",
        embedding=EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
        chunking=ChunkingConfig(methods=[ChunkingMethod.RECURSIVE], params=ChunkParams()),
        retrieval=RetrievalConfig(
            methods=[RetrievalMethod.DENSE],
            retrievers=[
                RetrieverConfig(
                    type=RetrieverType.CROSS_ENCODER,
                    provider="local",
                    model="cross-encoder/ms-marco-MiniLM-L-6-v2",
                )
            ],
            retrieval_provider="local",
            retrieval_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        ),
    )

    runs = expand_sweep(config)
    assert len(runs) == 1
    assert runs[0].retrievers[0].type == RetrieverType.CROSS_ENCODER


def test_slice16_legacy_retrieval_unknown_model_rejected() -> None:
    """
    Scenario: legacy retrieval_model must exist in reranker registry.
    """
    with pytest.raises(ValidationError):
        RetrievalConfig(
            methods=[RetrievalMethod.DENSE],
            retrieval_model="unknown-reranker",
            retrieval_provider="local",
        )


def test_parallelism_bounds_are_enforced_in_model() -> None:
    """
    Scenario: execution.parallelism is bounded in config model validation

    Given parallelism values outside the [1,16] range
    When ExperimentConfig is built
    Then ValidationError is raised.
    """
    # Given / When / Then
    with pytest.raises(ValidationError):
        _slice_config(parallelism=0)
    with pytest.raises(ValidationError):
        _slice_config(parallelism=17)


def test_slice16_config_rejects_unknown_embedding_model() -> None:
    """
    Scenario: unknown embedding model is rejected by config validation.
    """
    with pytest.raises(ValidationError):
        ExperimentConfig(
            experiment_name="invalid-model",
            data_paths=["./data"],
            queries_file="./queries.json",
            embedding=EmbeddingConfig(provider="local", models=["unknown-model"]),
            chunking=ChunkingConfig(methods=[ChunkingMethod.RECURSIVE], params=ChunkParams()),
            retrieval=RetrievalConfig(retrievers=[RetrieverConfig(type=RetrieverType.DENSE)]),
        )


def test_slice16_config_rejects_embedding_provider_mismatch() -> None:
    """
    Scenario: embedding provider mismatch is rejected by config validation.
    """
    with pytest.raises(ValidationError):
        ExperimentConfig(
            experiment_name="invalid-provider",
            data_paths=["./data"],
            queries_file="./queries.json",
            embedding=EmbeddingConfig(provider="local", models=["voyage-4-large"]),
            chunking=ChunkingConfig(methods=[ChunkingMethod.RECURSIVE], params=ChunkParams()),
            retrieval=RetrievalConfig(),
        )


def test_slice16_retrieval_config_rejects_invalid_reranker_model() -> None:
    """
    Scenario: retrieval reranker model is validated against the known registry.
    """
    with pytest.raises(ValidationError):
        RetrieverConfig(
            type=RetrieverType.RERANKER,
            provider="local",
            model="unknown-reranker",
        )


def test_slice16_retrieval_config_rejects_reranker_without_provider() -> None:
    """
    Scenario: reranker without provider is rejected.
    """
    with pytest.raises(ValidationError):
        RetrieverConfig(
            type=RetrieverType.RERANKER,
            model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        )


def test_slice16_retrieval_config_rejects_reranker_without_model() -> None:
    """
    Scenario: reranker without model is rejected.
    """
    with pytest.raises(ValidationError):
        RetrieverConfig(
            type=RetrieverType.CROSS_ENCODER,
            provider="local",
        )


def test_slice16_legacy_retrieval_mismatched_provider_is_rejected() -> None:
    """
    Scenario: legacy retrieval provider/model pairing is validated.
    """
    with pytest.raises(ValidationError):
        RetrievalConfig(
            methods=[RetrievalMethod.SPARSE],
            retrieval_provider="voyage",
            retrieval_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        )


def test_cli_default_submit_timeout_is_120_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Scenario: default submit timeout is stable

    Given no client timeout env var is set
    When the CLI API client module loads
    Then `_DEFAULT_TIMEOUT_S` defaults to 120 seconds.
    """
    monkeypatch.delenv("RAG_PARAMS_FINDER_CLIENT_TIMEOUT_S", raising=False)
    importlib.reload(cli.api_client)
    assert cli.api_client._DEFAULT_TIMEOUT_S == 120.0


def test_cli_timeout_override_via_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Scenario: timeout override is respected

    Given `RAG_PARAMS_FINDER_CLIENT_TIMEOUT_S` is set
    When the CLI API client module loads
    Then `_DEFAULT_TIMEOUT_S` reflects the override value.
    """
    monkeypatch.setenv("RAG_PARAMS_FINDER_CLIENT_TIMEOUT_S", "7")
    importlib.reload(cli.api_client)
    assert cli.api_client._DEFAULT_TIMEOUT_S == 7.0
