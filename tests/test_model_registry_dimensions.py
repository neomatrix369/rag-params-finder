"""Regression tests for fixed vs runtime embedding dimensions in the model registry."""

from __future__ import annotations

import pytest

from server.core.model_registry import (
    get_dimensions,
    get_index_name,
    get_index_name_for_dimensions,
    get_model_info,
)


def test_get_dimensions_returns_local_model_size() -> None:
    assert get_dimensions("all-MiniLM-L6-v2") == 384


def test_get_dimensions_returns_voyage_model_size() -> None:
    assert get_dimensions("voyage-3.5-lite") == 1024


def test_get_dimensions_raises_for_runtime_kimchi_models() -> None:
    with pytest.raises(ValueError, match="runtime-detected dimensions"):
        get_dimensions("openai/text-embedding-3-large")


def test_get_index_name_matches_registry_for_fixed_dimension_models() -> None:
    assert get_index_name("all-MiniLM-L6-v2") == "vector_index_384"
    assert get_index_name("voyage-3.5-lite") == "vector_index_1024"


def test_get_index_name_for_dimensions_builds_expected_atlas_index_name() -> None:
    assert get_index_name_for_dimensions(3072) == "vector_index_3072"


def test_kimchi_models_are_registered_with_null_dimensions() -> None:
    info = get_model_info("mistral/codestral-embed")
    assert info["provider"] == "kimchi"
    assert info["dimensions"] is None
