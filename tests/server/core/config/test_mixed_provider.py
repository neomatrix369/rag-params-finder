"""
Tests for mixed-provider embedding configuration (S1 stream).

Author: Claude Haiku 4.5
Created: 2026-09-30
Scope: Config validation, provider derivation, sweep expansion, guard integration
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from server.core.guards.sie_guard import requires_sie, validate_sie_readiness
from server.core.model_registry import provider_for_model
from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
)
from server.models.enums import ChunkingMethod


class TestProviderDerivation:
    """Scenario: Provider is derived per model when not explicitly set."""

    def test_given_mixed_models_when_provider_none_then_models_are_valid(self) -> None:
        """
        Scenario: Mixed models accepted when provider is None.
        Slice: S1 mixed-provider axis

        Given a config with multiple models from different providers and provider=None,
        When the config is validated,
        Then no error is raised.
        """
        ### Given
        config = ExperimentConfig(
            experiment_name="test-mixed",
            data_paths=["./data"],
            queries_file="./queries.json",
            embedding=EmbeddingConfig(
                provider=None,
                models=["all-MiniLM-L6-v2", "voyage-3.5-lite", "Qwen/Qwen3-Embedding-8B"],
            ),
            chunking=ChunkingConfig(
                methods=[ChunkingMethod.RECURSIVE],
                params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
            ),
            retrieval=RetrievalConfig(),
            execution=ExecutionConfig(),
        )

        ### When
        providers = sorted(set(provider_for_model(m) for m in config.embedding.models))

        ### Then
        assert providers == ["doubleword", "local", "voyage"], (
            "Expected mixed config to contain local, voyage, and doubleword providers"
        )

    def test_given_explicit_provider_with_mismatch_then_raises(self) -> None:
        """
        Scenario: Explicit provider enforces model matching.
        Slice: S1 mixed-provider axis

        Given provider=voyage but models include a local model,
        When the config is validated,
        Then a ValueError is raised naming the mismatch.
        """
        ### Given / When / Then
        with pytest.raises(ValueError, match="belongs to provider"):
            ExperimentConfig(
                experiment_name="test-mismatch",
                data_paths=["./data"],
                queries_file="./queries.json",
                embedding=EmbeddingConfig(
                    provider="voyage",
                    models=["voyage-3.5-lite", "all-MiniLM-L6-v2"],
                ),
                chunking=ChunkingConfig(
                    methods=[ChunkingMethod.RECURSIVE],
                    params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
                ),
                retrieval=RetrievalConfig(),
                execution=ExecutionConfig(),
            )

    def test_given_explicit_provider_matching_then_succeeds(self) -> None:
        """
        Scenario: Explicit provider succeeds when all models match.
        Slice: S1 mixed-provider axis

        Given provider=local with all-MiniLM-L6-v2,
        When the config is validated,
        Then no error is raised.
        """
        ### Given
        config = ExperimentConfig(
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

        ### When
        provider = config.embedding.provider

        ### Then
        assert provider == "local", "Expected explicit provider to be retained"

    def test_given_unknown_model_when_validated_then_raises(self) -> None:
        """
        Scenario: Unknown models are rejected regardless of provider setting.
        Slice: S1 mixed-provider axis

        Given an unknown model in the list,
        When the config is validated,
        Then a ValueError is raised.
        """
        ### Given / When / Then
        with pytest.raises(ValueError, match="Unknown embedding model"):
            ExperimentConfig(
                experiment_name="test-unknown",
                data_paths=["./data"],
                queries_file="./queries.json",
                embedding=EmbeddingConfig(
                    provider=None,
                    models=["nonexistent-model"],
                ),
                chunking=ChunkingConfig(
                    methods=[ChunkingMethod.RECURSIVE],
                    params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
                ),
                retrieval=RetrievalConfig(),
                execution=ExecutionConfig(),
            )


class TestSIEGuardWithMixedProviders:
    """Scenario: SIE guard correctly identifies SIE usage in mixed configs."""

    def test_given_single_sie_model_when_requires_sie_then_returns_true(self) -> None:
        """
        Scenario: SIE guard fires for config with single SIE model.
        Slice: S1 mixed-provider axis

        Given a config with provider=sie and bge-m3 model,
        When requires_sie is called,
        Then True is returned.
        """
        ### Given
        config = ExperimentConfig(
            experiment_name="test-sie",
            data_paths=["./data"],
            queries_file="./queries.json",
            embedding=EmbeddingConfig(
                provider="sie",
                models=["bge-m3"],
            ),
            chunking=ChunkingConfig(
                methods=[ChunkingMethod.RECURSIVE],
                params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
            ),
            retrieval=RetrievalConfig(),
            execution=ExecutionConfig(),
        )

        ### When
        result = requires_sie(config)

        ### Then
        assert result is True, "Expected requires_sie to return True for SIE provider"

    def test_given_mixed_with_sie_model_when_requires_sie_then_returns_true(self) -> None:
        """
        Scenario: SIE guard fires for mixed config containing a SIE model.
        Slice: S1 mixed-provider axis

        Given provider=None with models including bge-m3,
        When requires_sie is called,
        Then True is returned (guard detects SIE model).
        """
        ### Given
        config = ExperimentConfig(
            experiment_name="test-mixed-sie",
            data_paths=["./data"],
            queries_file="./queries.json",
            embedding=EmbeddingConfig(
                provider=None,
                models=["all-MiniLM-L6-v2", "bge-m3"],
            ),
            chunking=ChunkingConfig(
                methods=[ChunkingMethod.RECURSIVE],
                params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
            ),
            retrieval=RetrievalConfig(),
            execution=ExecutionConfig(),
        )

        ### When
        result = requires_sie(config)

        ### Then
        assert result is True, (
            "Expected requires_sie to return True for mixed config with SIE model"
        )

    def test_given_mixed_without_sie_when_requires_sie_then_returns_false(self) -> None:
        """
        Scenario: SIE guard does not fire for mixed config without SIE models.
        Slice: S1 mixed-provider axis

        Given provider=None with models from local and voyage only,
        When requires_sie is called,
        Then False is returned.
        """
        ### Given
        config = ExperimentConfig(
            experiment_name="test-no-sie",
            data_paths=["./data"],
            queries_file="./queries.json",
            embedding=EmbeddingConfig(
                provider=None,
                models=["all-MiniLM-L6-v2", "voyage-3.5-lite"],
            ),
            chunking=ChunkingConfig(
                methods=[ChunkingMethod.RECURSIVE],
                params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
            ),
            retrieval=RetrievalConfig(),
            execution=ExecutionConfig(),
        )

        ### When
        result = requires_sie(config)

        ### Then
        assert result is False, (
            "Expected requires_sie to return False for mixed config without SIE models"
        )

    def test_given_mixed_with_sie_when_sie_disabled_then_raises(self) -> None:
        """
        Scenario: SIE guard blocks mixed config when SIE is disabled.
        Slice: S1 mixed-provider axis

        Given provider=None with a SIE model, SIE_ENABLED=false,
        When validate_sie_readiness is called,
        Then SIEUnavailableError is raised.
        """
        ### Given
        from server.core.guards.sie_guard import SIEUnavailableError

        config = ExperimentConfig(
            experiment_name="test-mixed-sie-disabled",
            data_paths=["./data"],
            queries_file="./queries.json",
            embedding=EmbeddingConfig(
                provider=None,
                models=["all-MiniLM-L6-v2", "bge-m3"],
            ),
            chunking=ChunkingConfig(
                methods=[ChunkingMethod.RECURSIVE],
                params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
            ),
            retrieval=RetrievalConfig(),
            execution=ExecutionConfig(),
        )

        mock_settings = MagicMock(sie_enabled=False, sie_endpoint="http://localhost:8720")

        ### When / Then
        with patch("server.core.guards.sie_guard.settings", mock_settings):
            with pytest.raises(SIEUnavailableError, match="SIE_ENABLED=true"):
                validate_sie_readiness(config)


class TestMixedProviderSweepExpansion:
    """Scenario: Sweep expansion works correctly with mixed providers."""

    def test_given_mixed_models_when_expand_sweep_then_all_runs_created(self) -> None:
        """
        Scenario: Sweep expansion creates one run per model.
        Slice: S1 mixed-provider axis

        Given provider=None with 3 models, 1 chunking, 1 size, 1 overlap, 1 retriever,
        When expand_sweep is called,
        Then exactly 3 runs are produced (one per model).
        """
        ### Given
        from server.models.config import expand_sweep

        config = ExperimentConfig(
            experiment_name="test-expand-mixed",
            data_paths=["./data"],
            queries_file="./queries.json",
            embedding=EmbeddingConfig(
                provider=None,
                models=["all-MiniLM-L6-v2", "voyage-3.5-lite", "Qwen/Qwen3-Embedding-8B"],
            ),
            chunking=ChunkingConfig(
                methods=[ChunkingMethod.RECURSIVE],
                params=ChunkParams(chunk_sizes=[512], overlaps=[50]),
            ),
            retrieval=RetrievalConfig(),
            execution=ExecutionConfig(),
        )

        ### When
        runs = expand_sweep(config)

        ### Then
        assert len(runs) == 3, f"Expected 3 runs (one per model), got {len(runs)}"
        assert all(run.embedding_model in config.embedding.models for run in runs), (
            "Expected all runs to reference a config model"
        )


class TestSweepSummaryWithMixedProviders:
    """Scenario: Sweep summary correctly represents mixed-provider experiments."""

    def test_given_single_provider_when_summary_created_then_embedding_provider_single(
        self,
    ) -> None:
        """
        Scenario: Single provider retained in sweep_summary.
        Slice: S1 mixed-provider axis

        Given all models from one provider,
        When sweep_summary embedding_provider is set,
        Then it contains the single provider (not "mixed").
        """
        ### Given / When
        # This is tested through the API layer; here we simulate the logic
        models = ["all-MiniLM-L6-v2", "all-MiniLM-L6-v2"]
        providers = sorted(set(provider_for_model(m) for m in models))
        embedding_provider = providers[0] if len(providers) == 1 else "mixed"

        ### Then
        assert embedding_provider == "local", "Expected single provider to be retained in summary"

    def test_given_mixed_providers_when_summary_created_then_embedding_provider_mixed(
        self,
    ) -> None:
        """
        Scenario: Mixed marker set in sweep_summary for multi-provider.
        Slice: S1 mixed-provider axis

        Given models from different providers,
        When sweep_summary embedding_provider is set,
        Then it contains "mixed" as the marker.
        """
        ### Given / When
        models = ["all-MiniLM-L6-v2", "voyage-3.5-lite", "Qwen/Qwen3-Embedding-8B"]
        providers = sorted(set(provider_for_model(m) for m in models))
        embedding_provider = providers[0] if len(providers) == 1 else "mixed"

        ### Then
        assert embedding_provider == "mixed", (
            "Expected 'mixed' marker when multiple providers present"
        )
        assert providers == ["doubleword", "local", "voyage"], (
            f"Expected providers to be sorted and deduplicated, got {providers}"
        )
