"""Regression tests for experiment config validation across embedding providers."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from cli.config_loader import load_config
from server.models.config import ExperimentConfig


def _minimal_config(provider: str, models: list[str]) -> dict[str, Any]:
    return {
        "experiment_name": "provider-regression",
        "data_paths": ["./input_data/pdfs/The_Federal_Pell_Grant_Program.pdf"],
        "queries_file": "./configs/questions.example.json",
        "database_provider": "mongodb",
        "embedding": {"provider": provider, "models": models},
        "chunking": {
            "methods": ["recursive"],
            "params": {"chunk_sizes": [256], "overlaps": [50]},
        },
        "retrieval": {
            "methods": ["dense"],
            "top_k_initial": 20,
            "top_k_final": 5,
            "rerank_provider": "local",
            "rerank_model": None,
        },
        "execution": {"parallelism": 1, "on_error": "continue"},
    }


def test_local_provider_accepts_local_model() -> None:
    config = ExperimentConfig.model_validate(_minimal_config("local", ["all-MiniLM-L6-v2"]))
    assert config.embedding.provider == "local"


def test_voyage_provider_accepts_voyage_model() -> None:
    config = ExperimentConfig.model_validate(_minimal_config("voyage", ["voyage-3.5-lite"]))
    assert config.embedding.provider == "voyage"


def test_voyage_provider_rejects_local_model() -> None:
    with pytest.raises(ValidationError, match="belongs to provider 'local'"):
        ExperimentConfig.model_validate(_minimal_config("voyage", ["all-MiniLM-L6-v2"]))


def test_kimchi_rerank_provider_is_rejected() -> None:
    payload = _minimal_config("kimchi", ["openai/text-embedding-3-large"])
    payload["retrieval"]["rerank_provider"] = "kimchi"
    payload["retrieval"]["rerank_model"] = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    with pytest.raises(ValidationError, match="Kimchi is supported for embeddings only"):
        ExperimentConfig.model_validate(payload)


def test_example_local_config_loads() -> None:
    config = load_config("configs/example-mongodb-local.yaml")
    assert config["embedding"]["provider"] == "local"
    assert config["embedding"]["models"] == ["all-MiniLM-L6-v2"]


def test_example_voyage_config_loads() -> None:
    config = load_config("configs/example-mongodb-voyage.yaml")
    assert config["embedding"]["provider"] == "voyage"
