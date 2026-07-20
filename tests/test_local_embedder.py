"""GWT tests for local embedder thread-budget behavior under parallel sweep execution.

Author: Codex
Created: 2026-07-20
Scope: Verify per-worker thread budgeting for local sentence-transformer encoding.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from server.core import local_embedder


class _FakeEmbedding:
    """Minimal embedding output object with `tolist` contract."""

    def __init__(self, values: list[float]):
        self._values = values

    def tolist(self) -> list[float]:
        return list(self._values)


def test_local_embedding_caps_threads_when_parallelism_gt1() -> None:
    """
    Given parallelism > 1 and a multi-core host
    When embed_documents_local encodes documents
    Then torch.set_num_threads is set to a shared budget.
    """
    texts = ["chunk one", "chunk two", "chunk three"]
    fake_model = MagicMock()
    fake_model.encode.return_value = [
        _FakeEmbedding([0.1, 0.2]),
        _FakeEmbedding([0.3, 0.4]),
        _FakeEmbedding([0.5, 0.6]),
    ]

    with (
        patch("server.core.local_embedder._get_model", return_value=fake_model),
        patch("server.core.local_embedder.os.cpu_count", return_value=8),
        patch("server.core.local_embedder.torch.get_num_threads", return_value=8),
        patch("server.core.local_embedder.torch.set_num_threads") as mock_set_num_threads,
    ):
        result = local_embedder.embed_documents_local(
            texts,
            model_id="all-MiniLM-L6-v2",
            parallelism=4,
        )

    assert mock_set_num_threads.call_count == 2
    assert mock_set_num_threads.call_args_list[0].args == (2,)
    assert mock_set_num_threads.call_args_list[1].args == (8,)
    assert len(result) == 3


def test_local_embedding_no_thread_override_when_parallelism_is_one() -> None:
    """
    Given parallelism=1
    When embed_documents_local is called
    Then torch.set_num_threads is not forced.
    """
    fake_model = MagicMock()
    fake_model.encode.return_value = [
        _FakeEmbedding([0.1, 0.2]),
    ]

    with (
        patch("server.core.local_embedder._get_model", return_value=fake_model),
        patch("server.core.local_embedder.torch.set_num_threads") as mock_set_num_threads,
    ):
        result = local_embedder.embed_documents_local(
            ["chunk"],
            model_id="all-MiniLM-L6-v2",
            parallelism=1,
        )

    assert not mock_set_num_threads.called
    assert len(result) == 1
