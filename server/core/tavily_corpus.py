"""Tavily live web corpus builder — standalone primitive reused across SIE slices.

Fetches and normalises web search results for a given topic into plain-text
chunks that can feed directly into the RAG pipeline.

Usage:
    chunks = fetch_corpus("machine learning embeddings", max_results=5)

Requires TAVILY_API_KEY in environment (or .env file loaded by settings).
"""

from __future__ import annotations

import os

from tavily import TavilyClient  # type: ignore[import-untyped]

from server.utils.logger import get_logger

logger = get_logger(__name__)


def fetch_corpus(topic: str, max_results: int = 5) -> list[str]:
    """Fetch live web content for *topic* and return non-empty text chunks.

    Each result's ``content`` field becomes one chunk in the returned list.
    Empty or whitespace-only content is filtered out.

    Args:
        topic: Search query / topic to retrieve content for.
        max_results: Maximum number of web results to request from Tavily.

    Returns:
        List of non-empty content strings, one per Tavily result.

    Raises:
        ValueError: If TAVILY_API_KEY is not set in the environment.
        RuntimeError: If the Tavily API call fails.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError(
            "TAVILY_API_KEY is not set in environment. "
            "Add it to your .env file to use live Tavily corpus fetching."
        )

    logger.info("tavily corpus fetch — topic=%r max_results=%d", topic, max_results)
    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(topic, max_results=max_results)
        results = response.get("results", [])
        chunks = [r["content"] for r in results if r.get("content", "").strip()]
        logger.info("tavily corpus OK — topic=%r chunks=%d", topic, len(chunks))
        return chunks
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Tavily fetch failed for topic '{topic}': {exc}") from exc
