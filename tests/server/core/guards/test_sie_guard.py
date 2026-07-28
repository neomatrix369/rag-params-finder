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
        Scenario: skips check for non sie provider.
        Slice: 45 — GWT-on-touch (module theme separation)
        Given an experiment with provider local
        When validate_sie_readiness is called
        Then no error is raised without probing SIE.
        """
        ### Given
        ### When
        ### Then
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

        with patch("server.core.guards.sie_guard.probe_sie_reachable") as mock_probe:
            validate_sie_readiness(config)

        mock_probe.assert_not_called()

    def test_raises_when_sie_disabled_in_env(self):
        """
        Scenario: raises when sie disabled in env.
        Slice: 45 — GWT-on-touch (module theme separation)
        Given provider sie but SIE_ENABLED=false
        When validate_sie_readiness is called
        Then SIEUnavailableError is raised mentioning SIE_ENABLED.
        """
        ### Given
        ### When
        ### Then
        config = _sie_config()
        mock_settings = MagicMock(
            sie_enabled=False, sie_endpoint="http://localhost:8720", sie_api_key=""
        )

        with patch("server.core.guards.sie_guard.settings", mock_settings):
            with pytest.raises(SIEUnavailableError, match="SIE_ENABLED=true"):
                validate_sie_readiness(config)

    def test_raises_when_sie_container_unreachable(self):
        """
        Scenario: raises when sie container unreachable.
        Slice: 45 — GWT-on-touch (module theme separation)
        Given provider sie, SIE_ENABLED=true, and /healthz probe fails
        When validate_sie_readiness is called
        Then SIEUnavailableError is raised mentioning unreachable.
        """
        ### Given
        ### When
        ### Then
        config = _sie_config()
        mock_settings = MagicMock(
            sie_enabled=True, sie_endpoint="http://localhost:8720", sie_api_key=""
        )

        with (
            patch("server.core.guards.sie_guard.settings", mock_settings),
            patch("server.core.guards.sie_guard.probe_sie_reachable", return_value=False),
        ):
            with pytest.raises(SIEUnavailableError, match="unreachable"):
                validate_sie_readiness(config)

    def test_passes_when_sie_enabled_and_reachable(self):
        """
        Scenario: passes when sie enabled and reachable.
        Slice: 45 — GWT-on-touch (module theme separation)
        Given provider sie, SIE_ENABLED=true, and /healthz returns 200
        When validate_sie_readiness is called
        Then no error is raised.
        """
        ### Given
        ### When
        ### Then
        config = _sie_config()
        mock_settings = MagicMock(
            sie_enabled=True, sie_endpoint="http://localhost:8720", sie_api_key=""
        )

        with (
            patch("server.core.guards.sie_guard.settings", mock_settings),
            patch("server.core.guards.sie_guard.probe_sie_reachable", return_value=True),
        ):
            validate_sie_readiness(config)

    def test_probe_sends_bearer_token_when_api_key_configured(self):
        """
        Scenario: probe sends bearer token when api key configured.
        Slice: 45 — GWT-on-touch (module theme separation)
        Given SIE_API_KEY is set
        When probe_sie_reachable is called
        Then the health probe includes Authorization Bearer header.
        """
        ### Given
        ### When
        ### Then
        mock_settings = MagicMock(
            sie_endpoint="https://sie.example.com",
            sie_api_key="secret-token",
        )
        with (
            patch("server.core.guards.sie_guard.settings", mock_settings),
            patch("server.core.guards.sie_guard.httpx.get") as mock_get,
        ):
            mock_get.return_value.status_code = 200
            from server.core.sie_guard import probe_sie_reachable

            assert probe_sie_reachable() is True

        mock_get.assert_called_once_with(
            "https://sie.example.com/healthz",
            headers={"Authorization": "Bearer secret-token"},
            timeout=3.0,
        )
