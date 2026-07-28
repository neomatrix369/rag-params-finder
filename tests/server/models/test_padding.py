"""Tests for the padding chunking dimension (issue #45).

Padding enforces a minimum chunk character length by merging undersized chunks
forward. Covers both the post-processing helper and its expansion as a sweep
dimension.
"""

import pytest

from server.core.chunkers import _apply_padding
from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
    RetrieverConfig,
    expand_sweep,
)
from server.models.enums import ChunkingMethod, RetrieverType

# --- _apply_padding -------------------------------------------------------


def test_zero_padding_is_noop() -> None:
    """
    Scenario: zero padding is noop.
    Slice: 45 — GWT-on-touch (module theme separation)
    """
    ### Given
    ### When
    ### Then
    chunks = ["a", "bb", "ccc"]
    assert _apply_padding(chunks, 0) == chunks


def test_negative_padding_is_noop() -> None:
    """
    Scenario: negative padding is noop.
    Slice: 45 — GWT-on-touch (module theme separation)
    """
    ### Given
    ### When
    ### Then
    chunks = ["a", "bb", "ccc"]
    assert _apply_padding(chunks, -5) == chunks


def test_single_chunk_unchanged() -> None:
    """
    Scenario: single chunk unchanged.
    Slice: 45 — GWT-on-touch (module theme separation)
    """
    ### Given
    ### When
    ### Then
    assert _apply_padding(["short"], 100) == ["short"]


def test_empty_list_unchanged() -> None:
    """
    Scenario: empty list unchanged.
    Slice: 45 — GWT-on-touch (module theme separation)
    """
    ### Given
    ### When
    ### Then
    assert _apply_padding([], 10) == []


def test_undersized_chunks_merge_forward_to_threshold() -> None:
    """
    Scenario: undersized chunks merge forward to threshold.
    Slice: 45 — GWT-on-touch (module theme separation)
    """
    ### Given
    ### When
    ### Then
    # "aaa" + " " + "bbb" = 7 chars → meets threshold.
    chunks = ["aaa", "bbb", "ccc", "ddd"]
    assert _apply_padding(chunks, 7) == ["aaa bbb", "ccc ddd"]


def test_trailing_remainder_attaches_to_last_chunk() -> None:
    """
    Scenario: trailing remainder attaches to last chunk.
    Slice: 45 — GWT-on-touch (module theme separation)
    """
    ### Given
    ### When
    ### Then
    # "ee" never reaches threshold and has nothing after it → folded into prev.
    chunks = ["aaaa", "bbbb", "ee"]
    assert _apply_padding(chunks, 4) == ["aaaa", "bbbb ee"]


def test_chunks_already_above_threshold_unchanged() -> None:
    """
    Scenario: chunks already above threshold unchanged.
    Slice: 45 — GWT-on-touch (module theme separation)
    """
    ### Given
    ### When
    ### Then
    chunks = ["aaaaaa", "bbbbbb"]
    assert _apply_padding(chunks, 4) == chunks


# --- expand_sweep ---------------------------------------------------------


def _config_with_paddings(paddings: list[int]) -> ExperimentConfig:
    return ExperimentConfig(
        experiment_name="test-padding",
        data_paths=["./input_data/pdfs/sample.pdf"],
        queries_file="./configs/questions.example.json",
        embedding=EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
        chunking=ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[256], overlaps=[50], paddings=paddings),
        ),
        retrieval=RetrievalConfig(retrievers=[RetrieverConfig(type=RetrieverType.DENSE)]),
        execution=ExecutionConfig(),
    )


def test_padding_default_adds_single_zero_run() -> None:
    """
    Scenario: padding default adds single zero run.
    Slice: 45 — GWT-on-touch (module theme separation)
    """
    ### Given
    ### When
    ### Then
    # Default ChunkParams has paddings=[0]: one run, padding 0.
    config = _config_with_paddings([0])
    runs = expand_sweep(config)
    assert len(runs) == 1
    assert runs[0].padding == 0


def test_padding_is_a_swept_dimension() -> None:
    """
    Scenario: padding is a swept dimension.
    Slice: 45 — GWT-on-touch (module theme separation)
    """
    ### Given
    ### When
    ### Then
    config = _config_with_paddings([0, 100, 200])
    runs = expand_sweep(config)
    assert len(runs) == 3
    assert sorted(run.padding for run in runs) == [0, 100, 200]


def test_padding_exceeds_chunk_size_emits_warning() -> None:
    """
    Scenario: padding exceeds chunk size emits warning.
    Slice: 45 — GWT-on-touch (module theme separation)
    """
    ### Given
    ### When
    ### Then
    with pytest.warns(
        UserWarning,
        match=r"paddings \[300\] exceed min chunk_size 256",
    ):
        ChunkParams(chunk_sizes=[256], paddings=[300])
