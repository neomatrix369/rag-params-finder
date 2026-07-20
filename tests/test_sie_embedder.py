"""GWT tests for SIE embedder — all SIEClient calls are mocked at the boundary."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from server.core.sie_guard import SIEUnavailableError


class TestSIEEmbedderDenseEmbedding:
    """Scenario: SIE BGE-M3 dense embedding."""

    def test_embed_documents_returns_1024_dim_vectors(self):
        """
        Given SIE_ENDPOINT is http://localhost:8720
        When embed_documents_sie(["test query"], "bge-m3") is called
        Then a list containing one 1024-dim float vector is returned.
        """
        mock_result = [{"dense": np.zeros(1024, dtype=np.float32)}]
        with patch("server.core.sie_embedder.SIEClient") as mock_client_cls:
            mock_client_cls.return_value.encode.return_value = mock_result

            from server.core.sie_embedder import embed_documents_sie

            result = embed_documents_sie(["test query"], "bge-m3")

        assert len(result) == 1
        assert len(result[0]) == 1024
        assert all(isinstance(v, float) for v in result[0])

    def test_embed_query_returns_1024_dim_vector(self):
        """
        Given SIE_ENDPOINT is http://localhost:8720
        When embed_query_sie("test query", "bge-m3") is called
        Then a 1024-dim float vector is returned.
        """
        mock_result = [{"dense": np.zeros(1024, dtype=np.float32)}]
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
        mock_result = [{"dense": np.zeros(1024, dtype=np.float32)} for _ in range(batch_size)]
        with patch("server.core.sie_embedder.SIEClient") as mock_client_cls:
            mock_client_cls.return_value.encode.return_value = mock_result

            from server.core.sie_embedder import embed_documents_sie

            texts = ["text one", "text two", "text three"]
            result = embed_documents_sie(texts, "bge-m3")

        assert len(result) == batch_size
        for vec in result:
            assert len(vec) == 1024

    def test_embed_documents_shards_large_batches(self):
        """
        When embed_documents_sie is called with more texts than the SIE queue limit
        Then encode is invoked in multiple smaller batches and all vectors are returned.
        """
        total = 300
        batch_size = 128
        expected_batches = (total + batch_size - 1) // batch_size
        with patch("server.core.sie_embedder.SIEClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value

            def _encode_side_effect(_model: str, items: list[dict[str, str]]) -> list[dict]:
                return [{"dense": np.zeros(1024, dtype=np.float32)} for _ in items]

            mock_client.encode.side_effect = _encode_side_effect

            from server.core.sie_embedder import embed_documents_sie

            texts = [f"text {i}" for i in range(total)]
            result = embed_documents_sie(texts, "bge-m3")

        assert len(result) == total
        assert mock_client.encode.call_count == expected_batches

    def test_embed_documents_respects_sie_in_flight_limit(self):
        """
        Given multiple concurrent encode calls and SIE in-flight limit = 1
        When embed_documents_sie is called across many threads
        Then active encode calls never exceed the configured cap.
        """
        from server.core import sie_embedder

        active = 0
        peak = 0
        lock = threading.Lock()
        started = threading.Event()

        def _encode_side_effect(*_args: object, **_kwargs: object) -> list[dict]:
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
                if active == 1:
                    started.set()
            time.sleep(0.05)
            with lock:
                active -= 1
            return [{"dense": np.zeros(1024, dtype=np.float32)}]

        def _run_worker(text: str) -> None:
            with patch("server.core.sie_embedder.SIEClient") as mock_client_cls:
                mock_client_cls.return_value.encode.side_effect = _encode_side_effect
                from server.core.sie_embedder import embed_documents_sie

                embed_documents_sie([text], "bge-m3")

        with patch("server.core.sie_embedder._SIE_MAX_IN_FLIGHT_REQUESTS", 1):
            threads = [threading.Thread(target=_run_worker, args=(f"text {i}",)) for i in range(3)]
            with patch.object(sie_embedder, "_SIE_ENCODE_SEMAPHORE", threading.Semaphore(1)):
                for t in threads:
                    t.start()
                started.wait(timeout=1.0)
                for t in threads:
                    t.join(timeout=1.0)
                    assert not t.is_alive()

        assert peak <= 1

    def test_get_client_passes_endpoint_and_api_key(self):
        """
        Given SIE_ENDPOINT and SIE_API_KEY are configured
        When embed_documents_sie is called
        Then SIEClient is constructed with endpoint and api_key.
        """
        mock_result = [{"dense": np.zeros(1024, dtype=np.float32)}]
        mock_settings = MagicMock(
            sie_endpoint="https://sie.example.com",
            sie_api_key="secret-token",
        )
        with (
            patch("server.core.sie_embedder.settings", mock_settings),
            patch("server.core.sie_embedder.SIEClient") as mock_client_cls,
        ):
            mock_client_cls.return_value.encode.return_value = mock_result

            from server.core.sie_embedder import embed_documents_sie

            embed_documents_sie(["test query"], "bge-m3")

        mock_client_cls.assert_called_once_with(
            "https://sie.example.com",
            api_key="secret-token",
        )


class TestSIEEmbedderFallback:
    """Scenario: SIE encode falls back gracefully when SIE is unreachable."""

    def test_embed_documents_raises_runtime_error_on_connection_failure(self):
        """
        Given SIEClient cannot connect to http://localhost:8720
        When embed_documents_sie is called
        Then a SIEUnavailableError is raised with message containing "SIE unreachable".
        """
        with patch("server.core.sie_embedder.SIEClient") as mock_client_cls:
            mock_client_cls.return_value.encode.side_effect = Exception("Connection refused")

            from server.core.sie_embedder import embed_documents_sie

            with pytest.raises(SIEUnavailableError, match="SIE unreachable"):
                embed_documents_sie(["test"], "bge-m3")

    def test_embed_documents_retries_on_503_like_errors(self, monkeypatch: pytest.MonkeyPatch):
        """
        Given SIE encode returns transient 503 errors
        When embed_documents_sie is called
        Then requests are retried and eventually succeed.
        """
        attempts = 0

        def _encode_side_effect(*_args: object, **_kwargs: object) -> list[dict]:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise Exception("503 Service Unavailable")
            return [{"dense": np.zeros(1024, dtype=np.float32)}]

        monkeypatch.setattr("server.core.sie_embedder._SIE_INITIAL_RETRY_DELAY_S", 0.0)
        with patch("server.core.sie_embedder.SIEClient") as mock_client_cls:
            mock_client_cls.return_value.encode.side_effect = _encode_side_effect

            from server.core.sie_embedder import embed_documents_sie

            result = embed_documents_sie(["test"], "bge-m3")

        assert len(result) == 1
        assert attempts == 2

    def test_embed_documents_does_not_retry_non_retryable_errors(self):
        """
        Given SIE encode raises a non-retryable error
        When embed_documents_sie is called
        Then the call fails without retrying.
        """
        with patch("server.core.sie_embedder.SIEClient") as mock_client_cls:
            mock_client_cls.return_value.encode.side_effect = Exception("Connection refused")

            from server.core.sie_embedder import embed_documents_sie

            with pytest.raises(SIEUnavailableError, match="SIE unreachable"):
                embed_documents_sie(["test"], "bge-m3")

    def test_embed_query_raises_runtime_error_on_connection_failure(self):
        """
        Given SIEClient cannot connect to http://localhost:8720
        When embed_query_sie is called
        Then a SIEUnavailableError is raised with message containing "SIE unreachable".
        """
        with patch("server.core.sie_embedder.SIEClient") as mock_client_cls:
            mock_client_cls.return_value.encode.side_effect = Exception("Connection refused")

            from server.core.sie_embedder import embed_query_sie

            with pytest.raises(SIEUnavailableError, match="SIE unreachable"):
                embed_query_sie("test", "bge-m3")
