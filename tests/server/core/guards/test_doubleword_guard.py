"""Tests for DoubleWord preflight guard."""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from server.core.guards.doubleword_guard import (
    load_unavailable_models,
    save_unavailable_model,
    validate_doubleword_readiness,
)
from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
)
from server.models.enums import ChunkingMethod


def _doubleword_config() -> ExperimentConfig:
    """Create a test config using DoubleWord model."""
    return ExperimentConfig(
        experiment_name="test-doubleword",
        data_paths=["./data"],
        queries_file="./queries.json",
        embedding=EmbeddingConfig(
            provider="doubleword",
            models=["Qwen/Qwen3-Embedding-8B"],
        ),
        chunking=ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
        ),
        retrieval=RetrievalConfig(),
        execution=ExecutionConfig(),
    )


def _local_config() -> ExperimentConfig:
    """Create a test config using local model (non-DoubleWord)."""
    return ExperimentConfig(
        experiment_name="test-local",
        data_paths=["./data"],
        queries_file="./queries.json",
        embedding=EmbeddingConfig(
            provider="local",
            models=["all-MiniLM-L6-v2"],
        ),
        chunking=ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
        ),
        retrieval=RetrievalConfig(),
        execution=ExecutionConfig(),
    )


class TestLoadUnavailableModels:
    """Scenario: Load unavailable models registry."""

    def test_loads_from_existing_file(self):
        """
        Scenario: loads from existing file.
        Slice: 48A — DoubleWord batch client.
        Given a registry file with model entries
        When load_unavailable_models is called
        Then returns dict of model_id → reason.
        """
        ### Given
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump(
                {"model-1": "rate limited", "model-2": "api error"},
                tmp,
            )
            tmp_path = tmp.name

        ### When
        with patch("server.core.guards.doubleword_guard.UNAVAILABLE_REGISTRY_PATH", tmp_path):
            result = load_unavailable_models()

        ### Then
        os.unlink(tmp_path)
        assert result == {"model-1": "rate limited", "model-2": "api error"}

    def test_returns_empty_dict_when_file_missing(self):
        """
        Scenario: returns empty dict when file missing.
        Slice: 48A — DoubleWord batch client.
        Given no registry file exists
        When load_unavailable_models is called
        Then returns empty dict.
        """
        ### Given / When
        with patch(
            "server.core.guards.doubleword_guard.UNAVAILABLE_REGISTRY_PATH",
            "/nonexistent/path.json",
        ):
            result = load_unavailable_models()

        ### Then
        assert result == {}

    def test_returns_empty_on_corrupted_json(self):
        """
        Scenario: returns empty on corrupted json.
        Slice: 48A — DoubleWord batch client.
        Given a corrupted JSON file
        When load_unavailable_models is called
        Then returns empty dict and logs warning.
        """
        ### Given
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp.write("{invalid json")
            tmp_path = tmp.name

        ### When
        with patch("server.core.guards.doubleword_guard.UNAVAILABLE_REGISTRY_PATH", tmp_path):
            result = load_unavailable_models()

        ### Then
        os.unlink(tmp_path)
        assert result == {}


class TestSaveUnavailableModel:
    """Scenario: Save unavailable model to registry."""

    def test_saves_model_and_creates_parent_dir(self):
        """
        Scenario: saves model and creates parent dir.
        Slice: 48A — DoubleWord batch client.
        Given a non-existent parent directory
        When save_unavailable_model is called
        Then creates directory and saves atomically.
        """
        ### Given
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = os.path.join(tmpdir, "subdir", "registry.json")

            ### When
            with patch(
                "server.core.guards.doubleword_guard.UNAVAILABLE_REGISTRY_PATH",
                registry_path,
            ):
                save_unavailable_model("test-model", "test reason")

            ### Then
            assert os.path.exists(registry_path)
            with open(registry_path) as f:
                data = json.load(f)
            assert data == {"test-model": "test reason"}

    def test_appends_to_existing_registry(self):
        """
        Scenario: appends to existing registry.
        Slice: 48A — DoubleWord batch client.
        Given existing registry with one entry
        When save_unavailable_model adds another
        Then both entries are preserved.
        """
        ### Given
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump({"existing-model": "old reason"}, tmp)
            tmp_path = tmp.name

        ### When
        with patch("server.core.guards.doubleword_guard.UNAVAILABLE_REGISTRY_PATH", tmp_path):
            save_unavailable_model("new-model", "new reason")
            result = load_unavailable_models()

        ### Then
        os.unlink(tmp_path)
        assert result == {
            "existing-model": "old reason",
            "new-model": "new reason",
        }

    def test_overwrites_existing_entry(self):
        """
        Scenario: overwrites existing entry.
        Slice: 48A — DoubleWord batch client.
        Given existing registry with a model entry
        When save_unavailable_model updates the same model
        Then only new reason is stored.
        """
        ### Given
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump({"model-x": "old reason"}, tmp)
            tmp_path = tmp.name

        ### When
        with patch("server.core.guards.doubleword_guard.UNAVAILABLE_REGISTRY_PATH", tmp_path):
            save_unavailable_model("model-x", "updated reason")
            result = load_unavailable_models()

        ### Then
        os.unlink(tmp_path)
        assert result == {"model-x": "updated reason"}


class TestValidateDoublewordReadiness:
    """Scenario: DoubleWord preflight validation."""

    def test_skips_check_for_non_doubleword_provider(self):
        """
        Scenario: skips check for non doubleword provider.
        Slice: 48A — DoubleWord batch client.
        Given an experiment with provider local
        When validate_doubleword_readiness is called
        Then no error is raised.
        """
        ### Given
        config = _local_config()
        mock_settings = MagicMock(doubleword_api_key=None)

        ### When / Then
        with patch("server.core.guards.doubleword_guard.settings", mock_settings):
            validate_doubleword_readiness(config)

    def test_raises_when_api_key_missing(self):
        """
        Scenario: raises when api key missing.
        Slice: 48A — DoubleWord batch client.
        Given provider doubleword but DOUBLEWORD_API_KEY=None
        When validate_doubleword_readiness is called
        Then raises HTTPException(422) mentioning DOUBLEWORD_API_KEY.
        """
        ### Given
        config = _doubleword_config()
        mock_settings = MagicMock(doubleword_api_key=None)

        ### When / Then
        with patch("server.core.guards.doubleword_guard.settings", mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                validate_doubleword_readiness(config)
            assert exc_info.value.status_code == 422
            assert "DOUBLEWORD_API_KEY" in exc_info.value.detail

    def test_raises_when_model_unavailable(self):
        """
        Scenario: raises when model unavailable.
        Slice: 48A — DoubleWord batch client.
        Given a model in the unavailable registry
        When validate_doubleword_readiness is called
        Then raises HTTPException(422) with reason and clear instructions.
        """
        ### Given
        config = _doubleword_config()
        mock_settings = MagicMock(
            doubleword_api_key=MagicMock(get_secret_value=MagicMock(return_value="key"))
        )

        unavailable = {"Qwen/Qwen3-Embedding-8B": "API quota exceeded"}

        ### When / Then
        with (
            patch("server.core.guards.doubleword_guard.settings", mock_settings),
            patch(
                "server.core.guards.doubleword_guard.load_unavailable_models",
                return_value=unavailable,
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                validate_doubleword_readiness(config)
            assert exc_info.value.status_code == 422
            assert "API quota exceeded" in exc_info.value.detail
            assert ".rpf_state/doubleword_unavailable.json" in exc_info.value.detail

    def test_passes_when_api_key_set_and_models_available(self):
        """
        Scenario: passes when api key set and models available.
        Slice: 48A — DoubleWord batch client.
        Given provider doubleword, DOUBLEWORD_API_KEY set, no unavailable models
        When validate_doubleword_readiness is called
        Then no error is raised.
        """
        ### Given
        config = _doubleword_config()
        mock_settings = MagicMock(
            doubleword_api_key=MagicMock(get_secret_value=MagicMock(return_value="key"))
        )

        ### When / Then
        with (
            patch("server.core.guards.doubleword_guard.settings", mock_settings),
            patch(
                "server.core.guards.doubleword_guard.load_unavailable_models",
                return_value={},
            ),
        ):
            validate_doubleword_readiness(config)

    def test_checks_all_models_in_config(self):
        """
        Scenario: checks all models in config.
        Slice: 48A — DoubleWord batch client.
        Given a config with one DoubleWord model and it's unavailable
        When validate_doubleword_readiness is called
        Then raises HTTPException for the unavailable model.
        """
        ### Given
        # Use the single valid DoubleWord model
        config = _doubleword_config()
        mock_settings = MagicMock(
            doubleword_api_key=MagicMock(get_secret_value=MagicMock(return_value="key"))
        )
        # Model is unavailable
        unavailable = {"Qwen/Qwen3-Embedding-8B": "model down"}

        ### When / Then
        with (
            patch("server.core.guards.doubleword_guard.settings", mock_settings),
            patch(
                "server.core.guards.doubleword_guard.load_unavailable_models",
                return_value=unavailable,
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                validate_doubleword_readiness(config)
            assert "model down" in exc_info.value.detail
