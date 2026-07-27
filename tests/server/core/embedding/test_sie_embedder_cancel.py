"""Tests for SIE embedder cancel_check hook."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from server.core.experiment_control import ExperimentCancelledError


class TestSIEEmbedderCancelCheck:
    """Scenario: embedding batches honour cancel_check callbacks."""

    def test_embed_documents_invokes_cancel_check_per_batch(self):
        """
        Given 300 texts (3 SIE batches)
        When embed_documents_sie runs with cancel_check
        Then cancel_check is invoked before each batch encode.
        """
        calls = 0

        def cancel_check() -> None:
            nonlocal calls
            calls += 1

        with patch("server.core.sie_embedder.SIEClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value

            def _encode_side_effect(_model: str, items: list[dict[str, str]]) -> list[dict]:
                return [{"dense": np.zeros(1024, dtype=np.float32)} for _ in items]

            mock_client.encode.side_effect = _encode_side_effect

            from server.core.sie_embedder import embed_documents_sie

            texts = [f"text {i}" for i in range(300)]
            result = embed_documents_sie(texts, "bge-m3", cancel_check=cancel_check)

        assert len(result) == 300
        assert calls == 3

    def test_embed_documents_propagates_cancel_check_exception(self):
        """
        Given cancel_check raises ExperimentCancelledError
        When embed_documents_sie runs
        Then the cancellation propagates without wrapping.
        """

        def cancel_check() -> None:
            raise ExperimentCancelledError("cancelled")

        with patch("server.core.sie_embedder.SIEClient"):
            from server.core.sie_embedder import embed_documents_sie

            with pytest.raises(ExperimentCancelledError, match="cancelled"):
                embed_documents_sie(["text"], "bge-m3", cancel_check=cancel_check)
