"""Unit tests for Atlas search index definitions."""

from __future__ import annotations

from server.db.indexes import (
    TEXT_SEARCH_INDEX_NAME,
    VECTOR_INDEX_CONFIGS,
    _build_vector_index_model,
    known_search_index_names,
)


def test_known_search_index_names_includes_splade_vector_index() -> None:
    # given / when
    names = known_search_index_names()

    # then
    assert "vector_index_30522" in names
    assert TEXT_SEARCH_INDEX_NAME in names


def test_build_vector_index_model_splade_v3_has_30522_dimensions() -> None:
    # given
    model = _build_vector_index_model("vector_index_30522", 30522)
    fields = model.document["definition"]["fields"]

    # then
    vector_field = fields[0]
    assert vector_field["numDimensions"] == 30522
    assert vector_field["path"] == "embedding"
    filter_paths = {f["path"] for f in fields[1:]}
    assert filter_paths == {
        "experiment_id",
        "embedding_model",
        "chunking_method",
        "chunk_size",
        "overlap",
    }


def test_vector_index_configs_includes_all_managed_dimensions() -> None:
    dims = {cfg["dimensions"] for cfg in VECTOR_INDEX_CONFIGS}
    assert dims == {384, 1024, 30522}
