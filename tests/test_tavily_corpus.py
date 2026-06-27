"""GWT tests for Tavily corpus builder — all Tavily client calls are mocked."""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestTavilyCorpusBuilder:
    """Scenario: Tavily corpus builder returns text chunks."""

    def test_fetch_corpus_returns_non_empty_list_of_strings(self):
        """
        Given TAVILY_API_KEY is set and Tavily API is reachable
        When fetch_corpus(topic="machine learning embeddings", max_results=5) is called
        Then a non-empty list of strings (text chunks) is returned, each non-empty.
        """
        mock_results = [
            {"content": "Machine learning text one"},
            {"content": "Machine learning text two"},
            {"content": "Machine learning text three"},
        ]
        with (
            patch.dict("os.environ", {"TAVILY_API_KEY": "tvly-test-key"}),
            patch("server.core.tavily_corpus.TavilyClient") as mock_tavily_cls,
        ):
            mock_tavily_cls.return_value.search.return_value = {"results": mock_results}

            from server.core.tavily_corpus import fetch_corpus

            result = fetch_corpus(topic="machine learning embeddings", max_results=5)

        assert isinstance(result, list)
        assert len(result) > 0
        for chunk in result:
            assert isinstance(chunk, str)
            assert len(chunk) > 0

    def test_fetch_corpus_filters_empty_content(self):
        """
        When Tavily returns results with empty content entries
        Then those entries are excluded from the returned list.
        """
        mock_results = [
            {"content": "Valid content here"},
            {"content": ""},
            {"content": "   "},
            {"content": "Another valid chunk"},
        ]
        with (
            patch.dict("os.environ", {"TAVILY_API_KEY": "tvly-test-key"}),
            patch("server.core.tavily_corpus.TavilyClient") as mock_tavily_cls,
        ):
            mock_tavily_cls.return_value.search.return_value = {"results": mock_results}

            from server.core.tavily_corpus import fetch_corpus

            result = fetch_corpus(topic="test topic", max_results=5)

        assert len(result) == 2
        assert "Valid content here" in result
        assert "Another valid chunk" in result


class TestTavilyCorpusMissingKey:
    """Scenario: Tavily corpus builder raises on missing API key."""

    def test_fetch_corpus_raises_value_error_when_key_missing(self):
        """
        Given TAVILY_API_KEY is not set in env
        When fetch_corpus is called
        Then a ValueError is raised with message containing "TAVILY_API_KEY".
        """
        with patch.dict("os.environ", {}, clear=True):
            import os

            os.environ.pop("TAVILY_API_KEY", None)

            import importlib

            import server.core.tavily_corpus as tc_module

            importlib.reload(tc_module)

            with pytest.raises(ValueError, match="TAVILY_API_KEY"):
                tc_module.fetch_corpus(topic="test", max_results=3)
