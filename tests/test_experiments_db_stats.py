"""Regression tests for Vector DB stats dimension and index resolution."""

from __future__ import annotations

import pytest

from server.api import experiments_shared


def _base_stats_kwargs() -> dict:
    return {
        "total_chunks": 100,
        "chunking_breakdown": {"recursive": 100},
        "total_results": 10,
        "unique_queries": 2,
        "runs_with_data": 4,
        "run_breakdown": [],
    }


def test_db_stats_uses_registry_dimensions_for_voyage_without_chunk_sample() -> None:
    stats = experiments_shared._assemble_experiment_db_stats(
        {"experiment_id": "exp-voyage", "data_paths": ["./input_data/pdfs/sample.pdf"]},
        embedding_models=["voyage-3.5-lite"],
        **_base_stats_kwargs(),
    )

    assert stats["embedding_dimensions"] == [1024]
    assert stats["index_names"] == ["vector_index_1024"]
    assert stats["estimated_storage_mb"] > 0


def test_db_stats_uses_registry_dimensions_for_local_without_chunk_sample() -> None:
    stats = experiments_shared._assemble_experiment_db_stats(
        {"experiment_id": "exp-local", "data_paths": ["./input_data/pdfs/sample.pdf"]},
        embedding_models=["all-MiniLM-L6-v2"],
        **_base_stats_kwargs(),
    )

    assert stats["embedding_dimensions"] == [384]
    assert stats["index_names"] == ["vector_index_384"]


def test_db_stats_samples_runtime_dimensions_for_kimchi_when_chunks_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeCollection:
        def find_one(self, filter: dict[str, str], projection: dict[str, int]) -> dict | None:
            if filter.get("embedding_model") == "openai/text-embedding-3-large":
                return {"embedding": [0.0] * 3072}
            return None

    monkeypatch.setattr(experiments_shared, "get_collection", lambda _name: FakeCollection())

    stats = experiments_shared._assemble_experiment_db_stats(
        {"experiment_id": "exp-kimchi", "data_paths": ["./input_data/pdfs/sample.pdf"]},
        embedding_models=["openai/text-embedding-3-large"],
        **_base_stats_kwargs(),
    )

    assert stats["embedding_dimensions"] == [3072]
    assert "vector_index_3072" in stats["index_names"]
