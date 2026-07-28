"""GWT tests for pipeline search helpers and param signatures.

Author: Codex
Created: 2026-07-20
Scope: Traditional/reranker search helpers, completed signatures, primary retriever.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from server.core.orchestrator import (
    _completed_param_signatures,
    _primary_retriever,
    _run_doc_signature,
    _search_reranker_retriever,
    _search_traditional_retriever,
    _stored_enum_value,
)
from server.models.config import (
    RetrieverConfig,
)
from server.models.enums import (
    ChunkingMethod,
    RetrievalMethod,
    RetrieverType,
)
from tests.helpers.pipeline_sweep import _run_param


def test_search_traditional_retriever_embeds_when_needed() -> None:
    """
    Scenario: _search_traditional_retriever computes query embedding for dense/hybrid retrieval.
    Slice: 45 — GWT-on-touch (module theme separation)
    """
    ### Given
    ### When
    ### Then
    with patch("server.core.pipeline.search.get_retriever_backend") as mock_get_retriever_backend:
        mock_retriever_search = mock_get_retriever_backend.return_value.search
        mock_retriever_search.return_value = []
        embed_query_calls = []

        def _embed(_query_text: str, model: str) -> list[float]:
            embed_query_calls.append(model)
            return [0.1, 0.2]

        cfg = RetrieverConfig(type=RetrieverType.DENSE)

        results, query_embedding = _search_traditional_retriever(
            cfg,
            run_id="run-1",
            query_text="q",
            experiment_id="exp-1",
            embedding_model="emb-model",
            embed_query_fn=_embed,
            top_k=10,
            query_embedding=None,
        )

        assert results == []
        assert query_embedding == [0.1, 0.2]
        assert embed_query_calls == ["emb-model"]
        mock_retriever_search.assert_called_once()


def test_search_reranker_retriever_rejects_missing_provider_or_model() -> None:
    """
    Scenario: _search_reranker_retriever validates reranker configuration.
    Slice: 45 — GWT-on-touch (module theme separation)
    """
    ### Given
    ### When
    ### Then
    cfg_missing = SimpleNamespace(type=RetrieverType.RERANKER, provider=None, model=None)
    with pytest.raises(ValueError):
        _search_reranker_retriever(
            cfg_missing,
            run_id="run-1",
            query_text="q",
            experiment_id="exp-1",
            embedding_model="emb-model",
            embed_query_fn=lambda q, m: [0.0],
            top_k_initial=10,
            top_k_final=2,
        )


@patch("server.core.orchestrator._update_phase")
@patch("server.core.pipeline.search._search_traditional_retriever")
def test_search_reranker_retriever_no_candidates_logs_warning(
    mock_search_traditional: MagicMock, mock_update_phase: MagicMock
) -> None:
    """
    Scenario: _search_reranker_retriever returns empty list when no dense candidates are found.
    Slice: 45 — GWT-on-touch (module theme separation)
    """
    ### Given
    ### When
    ### Then
    mock_search_traditional.return_value = ([], None)

    cfg = RetrieverConfig(
        type=RetrieverType.RERANKER, provider="local", model="cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    results = _search_reranker_retriever(
        cfg,
        run_id="run-1",
        query_text="q",
        experiment_id="exp-1",
        embedding_model="emb-model",
        embed_query_fn=lambda q, m: [0.0],
        top_k_initial=10,
        top_k_final=2,
    )

    assert results == []
    mock_search_traditional.assert_called_once()
    mock_update_phase.assert_not_called()


def test_completed_param_signatures_extracts_phase_fields() -> None:
    """
    Scenario: _completed_param_signatures builds signatures from complete run documents.
    Slice: 45 — GWT-on-touch (module theme separation)
    """
    ### Given
    ### When
    ### Then
    runs = [
        {
            "database_provider": "mongodb",
            "embedding_provider": "local",
            "embedding_model": "all-MiniLM-L6-v2",
            "chunking_method": ChunkingMethod.RECURSIVE,
            "chunk_size": 512,
            "overlap": 25,
            "retrieval_method": RetrievalMethod.DENSE,
            "retrieval_provider": "local",
            "retrieval_model": None,
        }
    ]
    expected = {
        ("mongodb", "local", "all-MiniLM-L6-v2", "recursive", 512, 25, "dense", "local", None)
    }

    with patch("server.core.pipeline.signatures.get_storage_backend") as mock_get_storage_backend:
        mock_get_storage_backend.return_value.find_completed_run_sigs.return_value = runs
        assert _completed_param_signatures("exp") == expected


def test_stored_enum_value_and_run_doc_signature() -> None:
    """
    Scenario: storage helpers normalize enum and plain values for signatures.
    Slice: 45 — GWT-on-touch (module theme separation)
    """
    ### Given
    ### When
    ### Then
    assert _stored_enum_value(ChunkingMethod.RECURSIVE) == "recursive"
    assert _stored_enum_value("plain") == "plain"
    assert _stored_enum_value(None) == ""
    # Pin storage_backend so ambient STORAGE_BACKEND=postgres in .env cannot
    # change the missing-database_provider fallback used by resume signatures.
    with patch("server.core.pipeline.signatures.settings.storage_backend", "mongodb"):
        assert _run_doc_signature({"chunking_method": ChunkingMethod.RECURSIVE}) == (
            "mongodb",
            "",
            "",
            "recursive",
            0,
            0,
            "",
            "",
            None,
        )


def test_primary_retriever_with_empty_retrievers_raises() -> None:
    """
    Scenario: _primary_retriever validates retriever presence
    Slice: 45 — GWT-on-touch (module theme separation)

    Given run params with an empty retrievers list
    When _primary_retriever is called
    Then ValueError is raised.

    """
    ### Given
    ### When
    ### Then
    # Given
    params = _run_param().model_copy()
    params.retrievers = []

    # When / Then
    with pytest.raises(ValueError):
        _primary_retriever(params)
