"""Tests for SIE preflight guard (HTTP probe mocked at the boundary)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from server.core.sie_guard import SIEUnavailableError, validate_sie_readiness
from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
)
from server.models.enums import ChunkingMethod


def _sie_config() -> ExperimentConfig:
    return ExperimentConfig(
        experiment_name="test-sie",
        data_paths=["./data"],
        queries_file="./queries.json",
        embedding=EmbeddingConfig(provider="sie", models=["bge-m3"]),
        chunking=ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
        ),
        retrieval=RetrievalConfig(),
        execution=ExecutionConfig(),
    )


class TestSIEGuardPreflight:
    """Scenario: SIE readiness validation before sweep starts."""

    def test_skips_check_for_non_sie_provider(self):
        """
        Given an experiment with provider local
        When validate_sie_readiness is called
        Then no error is raised without probing SIE.
        """
        config = ExperimentConfig(
            experiment_name="test-local",
            data_paths=["./data"],
            queries_file="./queries.json",
            embedding=EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
            chunking=ChunkingConfig(
                methods=[ChunkingMethod.RECURSIVE],
                params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
            ),
            retrieval=RetrievalConfig(),
            execution=ExecutionConfig(),
        )

        with patch("server.core.sie_guard.probe_sie_reachable") as mock_probe:
            validate_sie_readiness(config)

        mock_probe.assert_not_called()

    def test_raises_when_sie_disabled_in_env(self):
        """
        Given provider sie but SIE_ENABLED=false
        When validate_sie_readiness is called
        Then SIEUnavailableError is raised mentioning SIE_ENABLED.
        """
        config = _sie_config()
        mock_settings = MagicMock(sie_enabled=False, sie_base_url="http://localhost:8720")

        with patch("server.core.sie_guard.settings", mock_settings):
            with pytest.raises(SIEUnavailableError, match="SIE_ENABLED=true"):
                validate_sie_readiness(config)

    def test_raises_when_sie_container_unreachable(self):
        """
        Given provider sie, SIE_ENABLED=true, and /healthz probe fails
        When validate_sie_readiness is called
        Then SIEUnavailableError is raised mentioning unreachable.
        """
        config = _sie_config()
        mock_settings = MagicMock(sie_enabled=True, sie_base_url="http://localhost:8720")

        with (
            patch("server.core.sie_guard.settings", mock_settings),
            patch("server.core.sie_guard.probe_sie_reachable", return_value=False),
        ):
            with pytest.raises(SIEUnavailableError, match="unreachable"):
                validate_sie_readiness(config)

    def test_passes_when_sie_enabled_and_reachable(self):
        """
        Given provider sie, SIE_ENABLED=true, and /healthz returns 200
        When validate_sie_readiness is called
        Then no error is raised.
        """
        config = _sie_config()
        mock_settings = MagicMock(sie_enabled=True, sie_base_url="http://localhost:8720")

        with (
            patch("server.core.sie_guard.settings", mock_settings),
            patch("server.core.sie_guard.probe_sie_reachable", return_value=True),
        ):
            validate_sie_readiness(config)
