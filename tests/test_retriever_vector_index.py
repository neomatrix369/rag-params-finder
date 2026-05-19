"""Regression tests for dense search vector index selection by embedding dimension."""

from __future__ import annotations

from typing import Any

import pytest

from server.core import retriever


@pytest.mark.parametrize(
    ("query_embedding", "embedding_model", "expected_index"),
    [
        ([0.0] * 384, "all-MiniLM-L6-v2", "vector_index_384"),
        ([0.0] * 1024, "voyage-3.5-lite", "vector_index_1024"),
        ([0.0] * 1536, "openai/text-embedding-3-large", "vector_index_1536"),
    ],
)
def test_dense_search_selects_index_from_query_vector_length(
    monkeypatch: pytest.MonkeyPatch,
    query_embedding: list[float],
    embedding_model: str,
    expected_index: str,
) -> None:
    seen: dict[str, Any] = {}

    def fake_ensure_vector_index(dimensions: int) -> bool:
        seen["dimensions"] = dimensions
        return True

    class FakeCollection:
        def aggregate(self, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
            seen["index"] = pipeline[0]["$vectorSearch"]["index"]
            seen["filter_model"] = pipeline[0]["$vectorSearch"]["filter"]["embedding_model"]
            return []

    monkeypatch.setattr(retriever, "ensure_vector_index", fake_ensure_vector_index)
    monkeypatch.setattr(retriever, "get_collection", lambda _name: FakeCollection())

    results = retriever.dense_search(
        query_embedding=query_embedding,
        experiment_id="exp-local",
        embedding_model=embedding_model,
        top_k=10,
    )

    assert results == []
    assert seen["dimensions"] == len(query_embedding)
    assert seen["index"] == expected_index
    assert seen["filter_model"] == {"$eq": embedding_model}
