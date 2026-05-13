from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from cli.config_loader import load_config
from server.core import retriever
from server.core.kimchi_embedder import _normalize_base_url, _parse_embeddings, _to_api_model_name
from server.core.model_registry import EMBEDDING_MODELS
from server.models.config import ExperimentConfig


def _minimal_config(provider: str, models: list[str]) -> dict[str, Any]:
    return {
        "experiment_name": "test-kimchi",
        "data_paths": ["./input_data/pdfs/The_Federal_Pell_Grant_Program.pdf"],
        "queries_file": "./configs/questions.example.json",
        "database_provider": "mongodb",
        "embedding": {
            "provider": provider,
            "models": models,
        },
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


def test_kimchi_provider_model_validation_succeeds() -> None:
    config = ExperimentConfig.model_validate(
        _minimal_config("kimchi", ["mistral/codestral-embed"])
    )

    assert config.embedding.provider == "kimchi"
    assert config.embedding.models == ["mistral/codestral-embed"]
    assert EMBEDDING_MODELS["mistral/codestral-embed"]["dimensions"] is None


def test_provider_model_mismatch_still_fails() -> None:
    with pytest.raises(ValidationError, match="belongs to provider 'kimchi'"):
        ExperimentConfig.model_validate(
            _minimal_config("local", ["mistral/codestral-embed"])
        )


def test_example_kimchi_config_loads() -> None:
    config = load_config("configs/example-kimchi.yaml")

    assert config["embedding"]["provider"] == "kimchi"
    assert len(config["embedding"]["models"]) == 34
    assert len(set(config["embedding"]["models"])) == 34


def test_kimchi_response_parsing_preserves_embedding_order() -> None:
    body = {
        "data": [
            {"index": 1, "embedding": [3, 4]},
            {"index": 0, "embedding": [1, 2]},
        ]
    }

    assert _parse_embeddings(body, expected_count=2) == [[1.0, 2.0], [3.0, 4.0]]


@pytest.mark.parametrize(
    ("raw_base_url", "normalized"),
    [
        ("https://llm.cast.ai/openai", "https://llm.cast.ai/openai"),
        ("https://llm.cast.ai/openai/v1", "https://llm.cast.ai/openai"),
        ("https://llm.cast.ai/openai/v1/embeddings", "https://llm.cast.ai/openai"),
        (
            "https://api.cast.ai/v1/llm/openai/supported-providers",
            "https://llm.cast.ai/openai",
        ),
    ],
)
def test_kimchi_base_url_normalization(raw_base_url: str, normalized: str) -> None:
    assert _normalize_base_url(raw_base_url) == normalized


def test_kimchi_api_model_name_strips_internal_provider_prefix() -> None:
    assert _to_api_model_name("mistral/codestral-embed") == "codestral-embed"
    assert _to_api_model_name("text-embedding-3-large") == "text-embedding-3-large"


def test_dense_search_uses_runtime_embedding_dimension(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_ensure_vector_index(dimensions: int) -> bool:
        seen["dimensions"] = dimensions
        return True

    class FakeCollection:
        def aggregate(self, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
            seen["index"] = pipeline[0]["$vectorSearch"]["index"]
            return []

    monkeypatch.setattr(retriever, "ensure_vector_index", fake_ensure_vector_index)
    monkeypatch.setattr(retriever, "get_collection", lambda _name: FakeCollection())

    results = retriever.dense_search(
        query_embedding=[0.1, 0.2, 0.3],
        experiment_id="experiment-1",
        embedding_model="mistral/codestral-embed",
        top_k=5,
    )

    assert results == []
    assert seen == {"dimensions": 3, "index": "vector_index_3"}


def test_example_kimchi_config_path_exists() -> None:
    assert Path("configs/example-kimchi.yaml").exists()
