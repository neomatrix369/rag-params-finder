"""GWT tests for SIE embedder — all SIEClient calls are mocked at the boundary."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest


class TestSIEEmbedderDenseEmbedding:
    """Scenario: SIE BGE-M3 dense embedding."""

    def test_embed_documents_returns_1024_dim_vectors(self):
        """
        Given SIEClient is initialised with base_url=http://localhost:8080
        When embed_documents_sie(["test query"], "bge-m3") is called
        Then a list containing one 1024-dim float vector is returned.
        """
        mock_result = {"dense": np.zeros((1, 1024), dtype=np.float32)}
        with patch("server.core.sie_embedder.SIEClient") as mock_client_cls:
            mock_client_cls.return_value.encode.return_value = mock_result

            from server.core.sie_embedder import embed_documents_sie

            result = embed_documents_sie(["test query"], "bge-m3")

        assert len(result) == 1
        assert len(result[0]) == 1024
        assert all(isinstance(v, float) for v in result[0])

    def test_embed_query_returns_1024_dim_vector(self):
        """
        Given SIEClient is initialised with base_url=http://localhost:8080
        When embed_query_sie("test query", "bge-m3") is called
        Then a 1024-dim float vector is returned.
        """
        mock_result = {"dense": np.zeros((1, 1024), dtype=np.float32)}
        with patch("server.core.sie_embedder.SIEClient") as mock_client_cls:
            mock_client_cls.return_value.encode.return_value = mock_result

            from server.core.sie_embedder import embed_query_sie

            result = embed_query_sie("test query", "bge-m3")

        assert len(result) == 1024
        assert all(isinstance(v, float) for v in result)

    def test_embed_documents_batch(self):
        """
        When embed_documents_sie is called with multiple texts
        Then a vector per text is returned.
        """
        batch_size = 3
        mock_result = {"dense": np.zeros((batch_size, 1024), dtype=np.float32)}
        with patch("server.core.sie_embedder.SIEClient") as mock_client_cls:
            mock_client_cls.return_value.encode.return_value = mock_result

            from server.core.sie_embedder import embed_documents_sie

            texts = ["text one", "text two", "text three"]
            result = embed_documents_sie(texts, "bge-m3")

        assert len(result) == batch_size
        for vec in result:
            assert len(vec) == 1024


class TestSIEEmbedderFallback:
    """Scenario: SIE encode falls back gracefully when SIE is unreachable."""

    def test_embed_documents_raises_runtime_error_on_connection_failure(self):
        """
        Given SIEClient cannot connect to http://localhost:8080
        When embed_documents_sie is called
        Then a RuntimeError is raised with message containing "SIE unreachable".
        """
        with patch("server.core.sie_embedder.SIEClient") as mock_client_cls:
            mock_client_cls.return_value.encode.side_effect = Exception("Connection refused")

            from server.core.sie_embedder import embed_documents_sie

            with pytest.raises(RuntimeError, match="SIE unreachable"):
                embed_documents_sie(["test"], "bge-m3")

    def test_embed_query_raises_runtime_error_on_connection_failure(self):
        """
        Given SIEClient cannot connect to http://localhost:8080
        When embed_query_sie is called
        Then a RuntimeError is raised with message containing "SIE unreachable".
        """
        with patch("server.core.sie_embedder.SIEClient") as mock_client_cls:
            mock_client_cls.return_value.encode.side_effect = Exception("Connection refused")

            from server.core.sie_embedder import embed_query_sie

            with pytest.raises(RuntimeError, match="SIE unreachable"):
                embed_query_sie("test", "bge-m3")
