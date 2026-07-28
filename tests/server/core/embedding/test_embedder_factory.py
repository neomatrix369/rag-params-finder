"""GWT tests for embedder_factory — factory returns correct fns for voyage/local/sie.

We mock each provider module at the sys.modules level so that importing voyageai
(which triggers a heavy langchain → torch import chain) is never needed in tests.
This keeps the test suite fast and avoids binary-library crashes in CI.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _make_voyage_mock():
    m = MagicMock()
    m.embed_documents_voyage = MagicMock(return_value=[[0.1] * 1024])
    m.embed_query_voyage = MagicMock(return_value=[0.1] * 1024)
    return m


def _make_local_mock():
    m = MagicMock()
    m.embed_documents_local = MagicMock(return_value=[[0.2] * 384])
    m.embed_query_local = MagicMock(return_value=[0.2] * 384)
    return m


def _make_sie_mock():
    m = MagicMock()
    m.embed_documents_sie = MagicMock(return_value=[[0.3] * 1024])
    m.embed_query_sie = MagicMock(return_value=[0.3] * 1024)
    return m


class TestEmbedderFactoryRouting:
    """Scenario: factory returns correct embedding functions per provider."""

    def test_get_embedder_voyage_returns_callable_pair(self):
        """
        Scenario: get embedder voyage returns callable pair.
        Slice: 45 — GWT-on-touch (module theme separation)
        Given provider="voyage"
        When get_embedder("voyage") is called
        Then a (embed_docs_fn, embed_query_fn) tuple is returned, both callable.
        """
        ### Given
        ### When
        ### Then
        voyage_mock = _make_voyage_mock()
        with patch.dict("sys.modules", {"server.core.embedding.embedder": voyage_mock}):
            import importlib

            import server.core.embedding.embedder_factory as fmod

            importlib.reload(fmod)
            embed_docs, embed_query = fmod.get_embedder("voyage")

        assert callable(embed_docs)
        assert callable(embed_query)

    def test_get_embedder_local_returns_callable_pair(self):
        """
        Scenario: get embedder local returns callable pair.
        Slice: 45 — GWT-on-touch (module theme separation)
        Given provider="local"
        When get_embedder("local") is called
        Then a (embed_docs_fn, embed_query_fn) tuple is returned, both callable.
        """
        ### Given
        ### When
        ### Then
        local_mock = _make_local_mock()
        with patch.dict("sys.modules", {"server.core.embedding.local_embedder": local_mock}):
            import importlib

            import server.core.embedding.embedder_factory as fmod

            importlib.reload(fmod)
            embed_docs, embed_query = fmod.get_embedder("local")

        assert callable(embed_docs)
        assert callable(embed_query)

    def test_get_embedder_sie_returns_callable_pair(self):
        """
        Scenario: get embedder sie returns callable pair.
        Slice: 45 — GWT-on-touch (module theme separation)
        Given provider="sie"
        When get_embedder("sie") is called
        Then a (embed_docs_fn, embed_query_fn) tuple is returned, both callable.
        """
        ### Given
        ### When
        ### Then
        sie_mock = _make_sie_mock()
        with patch.dict("sys.modules", {"server.core.embedding.sie_embedder": sie_mock}):
            import importlib

            import server.core.embedding.embedder_factory as fmod

            importlib.reload(fmod)
            embed_docs, embed_query = fmod.get_embedder("sie")

        assert callable(embed_docs)
        assert callable(embed_query)

    def test_get_embedder_unknown_provider_raises_value_error(self):
        """
        Scenario: get embedder unknown provider raises value error.
        Slice: 45 — GWT-on-touch (module theme separation)
        Given provider="unknown_provider"
        When get_embedder("unknown_provider") is called
        Then a ValueError is raised.
        """
        ### Given
        ### When
        ### Then
        from server.core.embedding.embedder_factory import get_embedder

        with pytest.raises(ValueError, match="unknown_provider"):
            get_embedder("unknown_provider")

    def test_get_embedder_voyage_delegates_to_voyage_module(self):
        """
        Scenario: get embedder voyage delegates to voyage module.
        Slice: 45 — GWT-on-touch (module theme separation)
        When provider="voyage", the returned embed_docs function
        is embed_documents_voyage from server.core.embedding.embedder.
        """
        ### Given
        ### When
        ### Then
        voyage_mock = _make_voyage_mock()
        with patch.dict("sys.modules", {"server.core.embedding.embedder": voyage_mock}):
            import importlib

            import server.core.embedding.embedder_factory as fmod

            importlib.reload(fmod)
            embed_docs, _ = fmod.get_embedder("voyage")

        assert embed_docs is voyage_mock.embed_documents_voyage

    def test_get_embedder_sie_delegates_to_sie_module(self):
        """
        Scenario: get embedder sie delegates to sie module.
        Slice: 45 — GWT-on-touch (module theme separation)
        When provider="sie", the returned embed_docs function
        is embed_documents_sie from server.core.embedding.sie_embedder.
        """
        ### Given
        ### When
        ### Then
        sie_mock = _make_sie_mock()
        with patch.dict("sys.modules", {"server.core.embedding.sie_embedder": sie_mock}):
            import importlib

            import server.core.embedding.embedder_factory as fmod

            importlib.reload(fmod)
            embed_docs, _ = fmod.get_embedder("sie")

        assert embed_docs is sie_mock.embed_documents_sie
