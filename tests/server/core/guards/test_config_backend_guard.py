"""
Tests for config↔server engine mismatch guard and provider normalize.

Author: swami
Created: 2026-07-26
Scope: Slice 37 — supabase→postgres normalize; ConfigBackendMismatchError 422 text;
       vector_db_group_key uses storage_mode:<host>
"""

from __future__ import annotations

import warnings
from unittest.mock import patch

import pytest

from server.core.config_backend_guard import (
    ConfigBackendMismatchError,
    format_config_backend_mismatch,
    validate_config_backend_match,
)
from server.db.ports.stats_common import (
    normalize_stats_database_provider,
    resolve_experiment_storage_mode,
    vector_db_group_key,
)
from server.models.config import ExperimentConfig, normalize_database_provider


def _minimal_config(**overrides: object) -> ExperimentConfig:
    base: dict[str, object] = {
        "experiment_name": "slice37",
        "data_paths": ["./input_data"],
        "queries_file": "./configs/questions.json",
        "database_provider": "mongodb",
        "embedding": {"provider": "local", "models": ["all-MiniLM-L6-v2"]},
        "chunking": {"methods": ["fixed"], "params": {"chunk_sizes": [256], "overlaps": [32]}},
        "retrieval": {"retrievers": [{"type": "dense"}]},
    }
    base.update(overrides)
    return ExperimentConfig.model_validate(base)


class TestNormalizeDatabaseProviderShould:
    def test_given_supabase_when_normalized_then_postgres(self) -> None:
        """
        Scenario: given supabase when normalized then postgres.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Deprecated supabase label becomes postgres engine.
        Slice: 37 — provider normalize

        Given database_provider supabase,
        When normalize_database_provider runs,
        Then the result is postgres.
        """
        ### Given / When
        actual = normalize_database_provider("supabase")

        ### Then
        assert actual == "postgres", "supabase must normalize to postgres"

    def test_given_supabase_yaml_when_config_loaded_then_provider_is_postgres(self) -> None:
        """
        Scenario: given supabase yaml when config loaded then provider is postgres.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: ExperimentConfig accepts supabase input but stores postgres.
        Slice: 37 — provider normalize

        Given YAML with database_provider supabase,
        When ExperimentConfig validates,
        Then database_provider equals postgres and a deprecation warning fires.
        """
        ### Given / When
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            actual = _minimal_config(database_provider="supabase")

        ### Then
        assert actual.database_provider == "postgres", (
            f"Expected postgres after normalize, got {actual.database_provider!r}"
        )
        assert any(issubclass(w.category, DeprecationWarning) for w in caught), (
            "Expected DeprecationWarning for database_provider: supabase"
        )


class TestConfigBackendGuardShould:
    def test_given_matching_engines_when_validated_then_no_error(self) -> None:
        """
        Scenario: given matching engines when validated then no error.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Matching config and server engines pass.
        Slice: 37 — config↔server 422

        Given postgres config and STORAGE_BACKEND=postgres,
        When validate_config_backend_match runs,
        Then no exception is raised.
        """
        ### Given
        config = _minimal_config(database_provider="postgres")

        ### When / Then
        with patch("server.core.guards.config_backend_guard.settings") as mock_settings:
            mock_settings.storage_backend = "postgres"
            validate_config_backend_match(config)

    def test_given_mismatch_when_validated_then_raises_before_index_wording(self) -> None:
        """
        Scenario: given mismatch when validated then raises before index wording.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Engine mismatch yields remediation distinct from catalog 422.
        Slice: 37 — config↔server 422

        Given mongodb config on a postgres-cloud server,
        When validate_config_backend_match runs,
        Then ConfigBackendMismatchError names restart flag and alternate config,
        And the message does not mention catalog or index missing.
        """
        ### Given
        config = _minimal_config(database_provider="mongodb")

        ### When
        with (
            patch("server.core.guards.config_backend_guard.settings") as mock_settings,
            patch(
                "server.core.guards.config_backend_guard.resolve_storage_mode",
                return_value="postgres-cloud",
            ),
        ):
            mock_settings.storage_backend = "postgres"
            with pytest.raises(ConfigBackendMismatchError) as raised:
                validate_config_backend_match(config)

        ### Then
        detail = str(raised.value)
        assert "Config engine mismatch" in detail
        assert "database_provider=mongodb" in detail
        assert "storage_backend=postgres" in detail
        assert "storage_mode=postgres-cloud" in detail
        assert "./start-services.sh --mongodb-cloud" in detail
        assert "configs/supabase/example-local.yaml" in detail
        assert "index" not in detail.lower()
        assert "catalog" not in detail.lower()
        assert "extension" not in detail.lower()

    def test_given_template_inputs_when_formatted_then_matches_slice_shape(self) -> None:
        """
        Scenario: given template inputs when formatted then matches slice shape.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Canonical 422 template fills engine/mode/paths.
        Slice: 37 — config↔server 422

        Given mismatched engines and a storage_mode,
        When format_config_backend_mismatch runs,
        Then the detail follows the Slice 37 stdout template.
        """
        ### Given / When
        actual = format_config_backend_mismatch(
            config_engine="mongodb",
            server_backend="postgres",
            storage_mode="postgres-cloud",
        )

        ### Then
        expected_prefix = (
            "Config engine mismatch: database_provider=mongodb but "
            "server storage_backend=postgres (storage_mode=postgres-cloud)."
        )
        assert actual.startswith(expected_prefix), actual
        assert "Restart with matching backend: ./start-services.sh --mongodb-cloud" in actual
        assert "Or submit a postgres config, e.g. configs/supabase/example-local.yaml" in actual


class TestVectorDbGroupKeyShould:
    def test_given_storage_mode_when_keyed_then_uses_mode_not_provider(self) -> None:
        """
        Scenario: given storage mode when keyed then uses mode not provider.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: vector_db_id is storage_mode:host.
        Slice: 37 — stats identity

        Given storage_mode postgres-cloud and a host,
        When vector_db_group_key builds the id,
        Then the key is postgres-cloud:<host>.
        """
        ### Given / When
        actual = vector_db_group_key("postgres-cloud", "db.abc.supabase.co")

        ### Then
        assert actual == "postgres-cloud:db.abc.supabase.co"

    def test_given_legacy_supabase_label_when_normalized_then_postgres(self) -> None:
        """
        Scenario: given legacy supabase label when normalized then postgres.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Stats never emit supabase as database_provider.
        Slice: 37 — stats identity

        Given a sweep_summary label of supabase,
        When normalize_stats_database_provider runs,
        Then the result is postgres.
        """
        ### Given / When
        actual = normalize_stats_database_provider("supabase", fallback="postgres")

        ### Then
        assert actual == "postgres"

    def test_given_persisted_mode_when_resolved_then_prefers_experiment_doc(self) -> None:
        """
        Scenario: given persisted mode when resolved then prefers experiment doc.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Grouping prefers persisted experiment storage_mode.
        Slice: 37 — persist storage_mode

        Given an experiment doc with storage_mode mongodb-local,
        When resolve_experiment_storage_mode runs with a different fallback,
        Then the persisted mode wins.
        """
        ### Given
        experiment = {"storage_mode": "mongodb-local", "sweep_summary": {}}

        ### When
        actual = resolve_experiment_storage_mode(experiment, fallback_mode="mongodb-cloud")

        ### Then
        assert actual == "mongodb-local"
