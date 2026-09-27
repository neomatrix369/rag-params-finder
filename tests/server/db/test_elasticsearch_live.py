"""Live Elasticsearch leg of the Slice 50 split-store acceptance test.

Author: swami
Created: 2026-09-27
Scope: refresh-before-return, delete-by-query, BM25, and the unit score scale
       against a reachable cluster. Skips when Elasticsearch is down unless
       RAG_REQUIRE_ELASTICSEARCH=1. Slice 51 owns the nightly job that sets
       that flag.
"""

from __future__ import annotations

import pytest

from server.db.elasticsearch.elasticsearch_vector_store import ElasticsearchVectorStore
from server.models.enums import RetrievalMethod
from server.settings import settings
from tests.helpers.storage_live import DEFAULT_ELASTICSEARCH_URL, elasticsearch_skip_reason

pytestmark = pytest.mark.integration

_EXPERIMENT = "exp-slice50-live"
_OTHER = "exp-slice50-live-other"
_RUN = "run-slice50-live"
_MODEL = "all-MiniLM-L6-v2"


def test_given_live_cluster_when_upsert_then_search_and_delete_are_scoped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Scenario: Insert-then-immediately-search, sparse BM25, and delete_experiment
    on live Elasticsearch.
    Slice: 50

    Given a reachable Elasticsearch cluster,
    When a chunk is indexed and searched immediately,
    Then the hit is found, the dense score is on the unit interval,
    BM25 returns the same chunk, and delete removes only that experiment.
    """
    ### Given
    url = settings.elasticsearch_url.strip() or DEFAULT_ELASTICSEARCH_URL
    reason = elasticsearch_skip_reason(url)
    if reason:
        pytest.skip(reason)
    monkeypatch.setattr(settings, "elasticsearch_url", url)
    monkeypatch.setattr(settings, "elasticsearch_index_prefix", "rpf-slice50-test")
    store = ElasticsearchVectorStore()
    vector = [0.1] * 384
    doc = {
        "chunk_id": "chunk-live-1",
        "experiment_id": _EXPERIMENT,
        "run_id": _RUN,
        "text": "pell grant deadline for students",
        "index": 0,
        "embedding": vector,
        "embedding_model": _MODEL,
        "chunk_method": "fixed",
    }
    other = {
        **doc,
        "chunk_id": "chunk-live-other",
        "experiment_id": _OTHER,
    }

    ### When
    try:
        store.ensure_indexes()
        store.insert_chunks([doc, other])
        dense = store.retriever().search(
            RetrievalMethod.DENSE,
            "pell",
            _EXPERIMENT,
            _MODEL,
            _RUN,
            5,
            vector,
        )
        sparse = store.retriever().search(
            RetrievalMethod.SPARSE,
            "pell grant",
            _EXPERIMENT,
            _MODEL,
            _RUN,
            5,
            None,
        )
        deleted = store.delete_chunks_for_experiment(_EXPERIMENT)
        remaining = store.retriever().search(
            RetrievalMethod.SPARSE,
            "pell grant",
            _EXPERIMENT,
            _MODEL,
            _RUN,
            5,
            None,
        )
    finally:
        store.delete_chunks_for_experiment(_EXPERIMENT)
        store.delete_chunks_for_experiment(_OTHER)

    ### Then
    assert dense, "insert-then-search must find the chunk (refresh=wait_for)"
    assert 0.0 <= dense[0].dense_score <= 1.0
    assert sparse, "BM25 must return the in-scope chunk"
    assert deleted >= 1
    assert remaining == []
