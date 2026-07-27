"""Tests for sentence-granular overlap in the semantic chunker.

Covers the overlap-seeding helper (``_overlap_sentences``), config-load warnings
for degenerate overlap values, and the ``chunk_text(SEMANTIC)`` dispatch chain
(mocked — no NLTK or sentence-transformers required).
"""

from unittest.mock import patch

import pytest

from server.core.chunkers import chunk_text
from server.core.chunkers.semantic import _overlap_sentences
from server.models.config import ChunkParams
from server.models.enums import ChunkingMethod


def test_no_overlap_carries_nothing() -> None:
    assert _overlap_sentences(["First sentence.", "Second sentence."], 0) == []


def test_negative_overlap_carries_nothing() -> None:
    assert _overlap_sentences(["First sentence.", "Second sentence."], -10) == []


def test_empty_group_carries_nothing() -> None:
    assert _overlap_sentences([], 50) == []


def test_carries_last_sentence_even_when_over_budget() -> None:
    # The final sentence is always kept so consecutive chunks share context,
    # even if it alone exceeds the overlap budget.
    flushed = ["Short.", "A very long trailing sentence that exceeds the budget."]
    assert _overlap_sentences(flushed, 5) == [
        "A very long trailing sentence that exceeds the budget."
    ]


def test_carries_multiple_trailing_sentences_within_budget() -> None:
    flushed = ["One.", "Two.", "Three.", "Four."]
    # Trailing sentences are carried while the running length (incl. joining
    # spaces) stays within budget: Four./Three./Two. total 18 <= 20; adding
    # One. would reach 22, so it is dropped.
    assert _overlap_sentences(flushed, 20) == ["Two.", "Three.", "Four."]


def test_overlap_preserves_sentence_order() -> None:
    flushed = ["Alpha.", "Beta.", "Gamma."]
    carried = _overlap_sentences(flushed, 100)
    assert carried == ["Alpha.", "Beta.", "Gamma."]


def test_overlap_exceeds_chunk_size_emits_warning() -> None:
    with pytest.warns(
        UserWarning,
        match=r"overlaps \[512\] >= chunk_size 512",
    ):
        ChunkParams(chunk_sizes=[512], overlaps=[512])


def test_semantic_dispatch_passes_overlap_to_chunk_semantic() -> None:
    with patch("server.core.chunkers.semantic.chunk_semantic") as mock_semantic:
        mock_semantic.return_value = ["chunk-a", "chunk-b"]
        result = chunk_text("Hello world.", ChunkingMethod.SEMANTIC, chunk_size=200, overlap=60)
        mock_semantic.assert_called_once_with("Hello world.", 200, 60)
        assert result == ["chunk-a", "chunk-b"]


def test_semantic_dispatch_overlap_zero_vs_nonzero() -> None:
    """Regression guard for issue #44 — overlap must reach chunk_semantic."""
    with patch("server.core.chunkers.semantic.chunk_semantic") as mock_semantic:
        mock_semantic.return_value = []
        chunk_text("Text.", ChunkingMethod.SEMANTIC, chunk_size=200, overlap=0)
        chunk_text("Text.", ChunkingMethod.SEMANTIC, chunk_size=200, overlap=60)
        assert mock_semantic.call_args_list[0].args[2] == 0
        assert mock_semantic.call_args_list[1].args[2] == 60
