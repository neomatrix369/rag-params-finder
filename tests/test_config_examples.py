"""Validate example YAML configs load, expand, and declare correct search indexes."""

from __future__ import annotations

from pathlib import Path

import pytest

from cli.config_loader import load_config
from server.core.search_index_plan import required_search_indexes
from server.db.indexes import TEXT_SEARCH_INDEX_NAME
from server.models.config import ExperimentConfig, expand_sweep

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SIE_CONFIG = _REPO_ROOT / "configs" / "mongodb" / "example-sie.yaml"
_SIE_MODELS = frozenset({"bge-m3", "stella-v5"})


class TestExampleMongoDbSieConfig:
    def test_given_sie_yaml_when_load_config_then_provider_and_models_valid(self) -> None:
        # given
        config_path = str(_SIE_CONFIG)

        # when
        raw = load_config(config_path)
        experiment = ExperimentConfig.model_validate(raw)

        # then
        assert experiment.embedding.provider == "sie"
        assert _SIE_MODELS <= frozenset(experiment.embedding.models)

    def test_given_sie_yaml_when_expand_sweep_then_yields_eighty_runs(self) -> None:
        # given
        raw = load_config(str(_SIE_CONFIG))
        experiment = ExperimentConfig.model_validate(raw)

        # when
        runs = expand_sweep(experiment)

        # then
        assert len(runs) == 80, (
            "Expected 2 models × 5 chunking × 2 sizes × 1 overlap × 4 retrievers = 80 runs"
        )

    def test_given_sie_yaml_when_required_search_indexes_then_vector_and_text(self) -> None:
        # given
        raw = load_config(str(_SIE_CONFIG))
        experiment = ExperimentConfig.model_validate(raw)

        # when
        required = required_search_indexes(experiment)

        # then
        assert "vector_index_1024" in required
        assert "vector_index_30522" not in required
        assert TEXT_SEARCH_INDEX_NAME in required


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
    # given
    config_path = str(_REPO_ROOT / config_rel_path)

    # when
    raw = load_config(config_path)
    experiment = ExperimentConfig.model_validate(raw)
    runs = expand_sweep(experiment)

    # then
    assert experiment.experiment_name
    assert len(runs) >= 1
