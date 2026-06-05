"""Tests for sentence-granular overlap in the semantic chunker.

These cover the overlap-seeding logic only (``_overlap_sentences``), which is
deterministic and dependency-free. The full ``chunk_semantic`` path requires
downloading NLTK data and the sentence-transformers model, so it is exercised
in integration runs rather than here.
"""

from server.core.chunkers.semantic import _overlap_sentences


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
