"""
Tests for example experiment configurations.

Author: Mani Sarkar
Created: 2026-06-29
Scope: config loading, sweep expansion, search-index requirements, backend example parity
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cli.config_loader import load_config
from server.core.search_index_plan import required_search_indexes
from server.db.mongo.indexes import TEXT_SEARCH_INDEX_NAME
from server.models.config import ExperimentConfig, expand_sweep
from tests.helpers.repo_paths import repo_root_from

_REPO_ROOT = repo_root_from(Path(__file__))
_MONGODB_CONFIG_DIR = _REPO_ROOT / "configs" / "mongodb"
_SUPABASE_CONFIG_DIR = _REPO_ROOT / "configs" / "supabase"
_SIE_CONFIG = _REPO_ROOT / "configs" / "mongodb" / "example-sie.yaml"
_SIE_MODELS = frozenset({"bge-m3", "stella-v5"})


def _yaml_names(config_dir: Path) -> set[str]:
    return {path.name for path in config_dir.glob("*.yaml")}


def _database_providers(config_dir: Path) -> set[str]:
    return {
        ExperimentConfig.model_validate(load_config(str(path))).database_provider
        for path in config_dir.glob("*.yaml")
    }


class TestExampleSieConfig:
    def test_given_sie_yaml_when_load_config_then_provider_and_models_valid(self) -> None:
        """
        Scenario: The MongoDB SIE example declares valid SIE models.
        Slice: SIE config validation

        Given the MongoDB SIE example,
        When it is loaded and validated,
        Then its provider and required model set are preserved.
        """
        ### Given
        config_path = str(_SIE_CONFIG)

        ### When
        raw = load_config(config_path)
        experiment = ExperimentConfig.model_validate(raw)

        ### Then
        assert experiment.embedding.provider == "sie" and _SIE_MODELS <= frozenset(
            experiment.embedding.models
        ), "Expected the SIE example to retain its provider and required models"

    def test_given_sie_yaml_when_expand_sweep_then_yields_eighty_runs(self) -> None:
        """
        Scenario: The SIE example expands to its documented sweep size.
        Slice: SIE config validation

        Given the validated MongoDB SIE example,
        When its sweep dimensions are expanded,
        Then exactly eighty run configurations are produced.
        """
        ### Given
        raw = load_config(str(_SIE_CONFIG))
        experiment = ExperimentConfig.model_validate(raw)

        ### When
        runs = expand_sweep(experiment)

        ### Then
        assert len(runs) == 80, (
            "Expected 2 models × 5 chunking × 2 sizes × 1 overlap × 4 retrievers = 80 runs"
        )

    def test_given_sie_yaml_when_required_search_indexes_then_vector_and_text(self) -> None:
        """
        Scenario: MongoDB SIE sweeps request their required Atlas indexes.
        Slice: SIE config validation

        Given the validated MongoDB SIE example,
        When MongoDB search-index requirements are calculated,
        Then the dense and text indexes are requested without a SPLADE vector index.
        """
        ### Given
        raw = load_config(str(_SIE_CONFIG))
        experiment = ExperimentConfig.model_validate(raw)

        ### When
        required = required_search_indexes(experiment)

        ### Then
        assert (
            "vector_index_1024" in required
            and "vector_index_30522" not in required
            and TEXT_SEARCH_INDEX_NAME in required
        ), "Expected the SIE sweep to require the dense and text Atlas indexes only"


class TestBackendExampleParity:
    def test_given_backend_config_directories_when_compared_then_examples_are_mirrored(
        self,
    ) -> None:
        """
        Scenario: MongoDB and Supabase/Postgres offer matching example entry points.
        Slice: 43 — Supabase/Postgres operator parity

        Given the two backend example directories,
        When their YAML filenames are compared,
        Then every MongoDB example has a Supabase/Postgres twin and vice versa.
        """
        ### Given / When
        actual_mongodb_names = _yaml_names(_MONGODB_CONFIG_DIR)
        expected_supabase_names = _yaml_names(_SUPABASE_CONFIG_DIR)

        ### Then
        assert actual_mongodb_names == expected_supabase_names, (
            "Expected configs/mongodb and configs/supabase to expose matching YAML examples"
        )

    def test_given_mirrored_examples_when_expanded_then_run_counts_match(self) -> None:
        """
        Scenario: Twin configs expand to the same sweep size.
        Slice: 43 — Supabase/Postgres operator parity

        Given matching MongoDB and Supabase example stems,
        When each pair is expanded,
        Then both sides produce the same number of runs.
        """
        ### Given / When / Then
        for name in sorted(_yaml_names(_MONGODB_CONFIG_DIR)):
            mongo_cfg = ExperimentConfig.model_validate(
                load_config(str(_MONGODB_CONFIG_DIR / name))
            )
            supabase_cfg = ExperimentConfig.model_validate(
                load_config(str(_SUPABASE_CONFIG_DIR / name))
            )
            actual_mongo_runs = len(expand_sweep(mongo_cfg))
            actual_supabase_runs = len(expand_sweep(supabase_cfg))
            assert actual_mongo_runs == actual_supabase_runs, (
                f"{name}: expected matching run counts, "
                f"got mongo={actual_mongo_runs} supabase={actual_supabase_runs}"
            )

    @pytest.mark.parametrize(
        ("config_dir", "expected_provider"),
        [
            pytest.param(_MONGODB_CONFIG_DIR, "mongodb", id="mongodb"),
            pytest.param(_SUPABASE_CONFIG_DIR, "postgres", id="supabase-folder-postgres-engine"),
        ],
    )
    def test_given_backend_examples_when_loaded_then_provider_labels_match_directory(
        self,
        config_dir: Path,
        expected_provider: str,
    ) -> None:
        """
        Scenario: Each backend example directory uses a consistent engine label.
        Slice: 37 — supabase YAML normalizes to postgres

        Given one backend's example directory,
        When every YAML config is loaded,
        Then each config labels mongodb or postgres (supabase input → postgres).
        """
        ### Given / When
        actual_providers = _database_providers(config_dir)

        ### Then
        assert actual_providers == {expected_provider}, (
            f"Expected every config in {config_dir} to use {expected_provider!r}"
        )


@pytest.mark.parametrize(
    "config_rel_path",
    [
        "configs/mongodb/example-local.yaml",
        "configs/mongodb/example-local-parallel.yaml",
        "configs/mongodb/example-voyage.yaml",
        "configs/mongodb/example-voyage-parallel.yaml",
        "configs/mongodb/example-unified-retrievers.yaml",
        "configs/mongodb/example-sie.yaml",
        "configs/mongodb/example-sie-parallel.yaml",
        "configs/mongodb/example-unified-retrievers-bayesian.yaml",
        "configs/mongodb/example-local-bayesian.yaml",
        "configs/supabase/example-local.yaml",
        "configs/supabase/example-local-parallel.yaml",
        "configs/supabase/example-voyage.yaml",
        "configs/supabase/example-voyage-parallel.yaml",
        "configs/supabase/example-unified-retrievers.yaml",
        "configs/supabase/example-sie.yaml",
        "configs/supabase/example-sie-parallel.yaml",
        "configs/supabase/example-unified-retrievers-bayesian.yaml",
        "configs/supabase/example-local-bayesian.yaml",
    ],
)
def test_given_example_yaml_when_load_and_validate_then_no_errors(config_rel_path: str) -> None:
    """
    Scenario: Every published example expands into at least one valid run.
    Slice: Config example regression coverage

    Given a published MongoDB or Supabase/Postgres example,
    When it is loaded, validated, and expanded,
    Then it has a name and produces at least one run.
    """
    ### Given
    config_path = str(_REPO_ROOT / config_rel_path)

    ### When
    raw = load_config(config_path)
    experiment = ExperimentConfig.model_validate(raw)
    runs = expand_sweep(experiment)

    ### Then
    assert experiment.experiment_name and len(runs) >= 1, (
        f"Expected {config_rel_path} to have a name and expand to at least one run"
    )
