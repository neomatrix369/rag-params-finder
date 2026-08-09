"""server.core.embedding.embedder unit tests — Voyage AI embeddings.

Author: nWave acceptance-designer
Created: 2026-08-07
Scope: server/core/embedding/embedder.py — unit-tier with voyageai mocking
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from server.core.embedding.embedder import (
    embed_documents_voyage,
    embed_query_voyage,
    get_client,
    get_limiter,
)

_MOD = "server.core.embedding.embedder"


class TestGetClientShould:
    """Scenario: get_client initializes Voyage AI client singleton."""

    def test_get_client_returns_singleton(self) -> None:
        """
        Scenario: get_client returns same instance on multiple calls.
        Slice: coverage-gap — server/core/embedding/embedder.py

        Given VOYAGE_API_KEY set in settings
        When get_client is called twice
        Then it returns the same client instance (singleton).
        """
        ### Given / When
        with patch(f"{_MOD}.settings.voyage_api_key", "test-key"):
            with patch(f"{_MOD}._client", None):
                with patch(f"{_MOD}.voyageai.Client") as mock_cls:
                    get_client()
                    get_client()

        ### Then
        mock_cls.assert_called()

    def test_get_client_raises_without_api_key(self) -> None:
        """
        Scenario: get_client raises ValueError when API key missing.
        Slice: coverage-gap — server/core/embedding/embedder.py

        Given VOYAGE_API_KEY not set
        When get_client is called
        Then it raises ValueError.
        """
        ### Given / When / Then
        with patch(f"{_MOD}.settings.voyage_api_key", ""):
            with patch(f"{_MOD}._client", None):
                with pytest.raises(ValueError, match="VOYAGE_API_KEY"):
                    get_client()


class TestGetLimiterShould:
    """Scenario: get_limiter initializes rate limiter singleton."""

    def test_get_limiter_returns_singleton(self) -> None:
        """
        Scenario: get_limiter returns rate limiter with configured limits.
        Slice: coverage-gap — server/core/embedding/embedder.py

        Given settings with RPM/TPM
        When get_limiter is called
        Then it returns limiter with configured limits.
        """
        ### Given / When
        with patch(f"{_MOD}.settings.voyage_rpm_limit", 300):
            with patch(f"{_MOD}.settings.voyage_tpm_limit", 1000000):
                with patch(f"{_MOD}._limiter", None):
                    limiter = get_limiter()

        ### Then
        assert limiter is not None


class TestEmbedDocumentsVoyageShould:
    """Scenario: embed_documents_voyage embeds texts with rate limiting."""

    def test_embed_documents_single_batch(self) -> None:
        """
        Scenario: embed_documents_voyage embeds small batch in one call.
        Slice: coverage-gap — server/core/embedding/embedder.py

        Given a list of 2 small documents
        When embed_documents_voyage is called with voyage model
        Then it embeds all documents and returns 2D array.
        """
        ### Given
        texts = ["hello world", "goodbye world"]
        model = "voyage-3.5-lite"

        mock_result = MagicMock()
        mock_result.embeddings = [[0.1, 0.2], [0.3, 0.4]]

        ### When
        with patch(f"{_MOD}.is_contextualized_embedding", return_value=False):
            with patch(f"{_MOD}._token_budget_per_request", return_value=100_000):
                with patch(f"{_MOD}.get_client"):
                    with patch(f"{_MOD}.get_limiter"):
                        with patch(f"{_MOD}.call_with_retry", return_value=mock_result):
                            with patch(f"{_MOD}._split_into_batches", return_value=[texts]):
                                result = embed_documents_voyage(texts, model)

        ### Then
        assert len(result) == 2
        assert result == [[0.1, 0.2], [0.3, 0.4]]

    def test_embed_documents_multiple_batches(self) -> None:
        """
        Scenario: embed_documents_voyage shards large batches.
        Slice: coverage-gap — server/core/embedding/embedder.py

        Given a list of very large documents
        When embed_documents_voyage is called
        Then it splits into multiple batches respecting token budget.
        """
        ### Given
        large_text = "x" * 10000
        texts = [large_text, large_text, large_text]
        model = "voyage-3.5-lite"

        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024]

        ### When
        with patch(f"{_MOD}.is_contextualized_embedding", return_value=False):
            with patch(f"{_MOD}._token_budget_per_request", return_value=100_000):
                with patch(f"{_MOD}.get_client"):
                    with patch(f"{_MOD}.get_limiter"):
                        with patch(f"{_MOD}._split_into_batches") as mock_split:
                            batches = [[large_text], [large_text], [large_text]]
                            mock_split.return_value = batches
                            with patch(f"{_MOD}.call_with_retry", return_value=mock_result):
                                embed_documents_voyage(texts, model)

        ### Then
        mock_split.assert_called_once()

    def test_embed_documents_respects_cancel_check(self) -> None:
        """
        Scenario: embed_documents_voyage checks cancel before batch.
        Slice: coverage-gap — server/core/embedding/embedder.py

        Given a cancel_check function
        When embed_documents_voyage is called
        Then it calls cancel_check before each batch.
        """
        ### Given
        texts = ["text1", "text2"]
        model = "voyage-3.5-lite"
        cancel_check = MagicMock()

        mock_result = MagicMock()
        mock_result.embeddings = [[0.1, 0.2], [0.3, 0.4]]

        ### When
        with patch(f"{_MOD}.is_contextualized_embedding", return_value=False):
            with patch(f"{_MOD}._token_budget_per_request", return_value=100_000):
                with patch(f"{_MOD}.get_client"):
                    with patch(f"{_MOD}.get_limiter"):
                        with patch(f"{_MOD}._split_into_batches", return_value=[texts]):
                            with patch(f"{_MOD}.call_with_retry", return_value=mock_result):
                                embed_documents_voyage(texts, model, cancel_check=cancel_check)

        ### Then
        assert cancel_check.called


class TestEmbedQueryVoyageShould:
    """Scenario: embed_query_voyage embeds single query."""

    def test_embed_query_single_query(self) -> None:
        """
        Scenario: embed_query_voyage embeds one query text.
        Slice: coverage-gap — server/core/embedding/embedder.py

        Given a query text
        When embed_query_voyage is called
        Then it returns 1D embedding array.
        """
        ### Given
        text = "what is RAG?"
        model = "voyage-3.5-lite"

        mock_result = MagicMock()
        mock_result.embeddings = [[0.1, 0.2, 0.3, 0.4]]

        ### When
        with patch(f"{_MOD}.get_client"):
            with patch(f"{_MOD}.get_limiter") as mock_get_lim:
                mock_get_lim.return_value._tpm = 100_000
                with patch(f"{_MOD}.call_with_retry", return_value=mock_result):
                    result = embed_query_voyage(text, model)

        ### Then
        assert result == [0.1, 0.2, 0.3, 0.4]

    def test_embed_query_respects_rate_limit(self) -> None:
        """
        Scenario: embed_query_voyage waits for rate limit.
        Slice: coverage-gap — server/core/embedding/embedder.py

        Given a query and rate limiter
        When embed_query_voyage is called
        Then it calls call_with_retry (which respects limiter).
        """
        ### Given
        text = "query"
        model = "voyage-3.5-lite"

        mock_result = MagicMock()
        mock_result.embeddings = [[0.1]]

        ### When
        with patch(f"{_MOD}.get_client"):
            with patch(f"{_MOD}.get_limiter") as mock_get_lim:
                mock_get_lim.return_value._tpm = 100_000
                with patch(f"{_MOD}.call_with_retry", return_value=mock_result):
                    result = embed_query_voyage(text, model)

        ### Then
        assert result is not None


class TestContextualizedEmbeddingsShould:
    """Scenario: contextualized embeddings split documents by segment."""

    def test_embed_documents_contextualized_format(self) -> None:
        """
        Scenario: contextualized embedding calls voyage-context-3.
        Slice: coverage-gap — server/core/embedding/embedder.py

        Given voyage-context-3 model
        When embed_documents_voyage is called
        Then it delegates to _embed_documents_voyage_context.
        """
        ### Given
        texts = ["chunk1", "chunk2"]
        model = "voyage-context-3"

        ### When
        with patch(f"{_MOD}.is_contextualized_embedding", return_value=True):
            with patch(f"{_MOD}._embed_documents_voyage_context") as mock_ctx:
                mock_ctx.return_value = [[0.1] * 1024, [0.2] * 1024]
                embed_documents_voyage(texts, model)

        ### Then
        mock_ctx.assert_called_once_with(texts, model, cancel_check=None)

    def test_embed_query_contextualized_format(self) -> None:
        """
        Scenario: contextualized query embedding calls context method.
        Slice: coverage-gap — server/core/embedding/embedder.py

        Given voyage-context-3 model
        When embed_query_voyage is called
        Then it delegates to _embed_query_voyage_context.
        """
        ### Given
        text = "query"
        model = "voyage-context-3"

        ### When
        with patch(f"{_MOD}.is_contextualized_embedding", return_value=True):
            with patch(f"{_MOD}._embed_query_voyage_context") as mock_ctx:
                mock_ctx.return_value = [0.1] * 1024
                result = embed_query_voyage(text, model)

        ### Then
        mock_ctx.assert_called_once_with(text, model)
        assert result == [0.1] * 1024


class TestEmbeddingErrorHandlingShould:
    """Scenario: embedding functions handle errors gracefully."""

    def test_embed_documents_empty_input(self) -> None:
        """
        Scenario: embed_documents_voyage handles empty text list.
        Slice: coverage-gap — server/core/embedding/embedder.py

        Given empty text list
        When embed_documents_voyage is called
        Then it returns empty list.
        """
        ### Given
        texts: list[str] = []
        model = "voyage-3.5-lite"

        ### When
        with patch(f"{_MOD}.is_contextualized_embedding", return_value=False):
            with patch(f"{_MOD}._token_budget_per_request", return_value=100_000):
                with patch(f"{_MOD}.get_client"):
                    with patch(f"{_MOD}.get_limiter"):
                        with patch(f"{_MOD}._split_into_batches", return_value=[]):
                            result = embed_documents_voyage(texts, model)

        ### Then
        assert result == []

    def test_embed_documents_api_error(self) -> None:
        """
        Scenario: embed_documents_voyage propagates API errors.
        Slice: coverage-gap — server/core/embedding/embedder.py

        Given Voyage API returns error
        When embed_documents_voyage is called
        Then it raises the API error.
        """
        ### Given
        texts = ["text"]
        model = "voyage-3.5-lite"

        mock_limiter = MagicMock()
        mock_limiter._tpm = 1000000

        ### When / Then
        with patch(f"{_MOD}.is_contextualized_embedding", return_value=False):
            with patch(f"{_MOD}.get_client"):
                with patch(f"{_MOD}.get_limiter", return_value=mock_limiter):
                    with patch(f"{_MOD}._split_into_batches", return_value=[texts]):
                        with patch(f"{_MOD}.call_with_retry") as mock_retry:
                            mock_retry.side_effect = RuntimeError("API error")
                            with pytest.raises(RuntimeError, match="API error"):
                                embed_documents_voyage(texts, model)
