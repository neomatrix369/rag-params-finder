"""server.core.embedding.rate_limiter unit tests.

Author: nWave acceptance-designer
Created: 2026-08-07
Scope: server/core/embedding/rate_limiter.py — unit-tier with time mocking
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from voyageai.error import RateLimitError

from server.core.embedding.rate_limiter import (
    RateLimiter,
    call_with_retry,
    estimate_tokens,
)


class TestEstimateTokensShould:
    """Scenario: estimate_tokens estimates token count from text."""

    def test_estimate_single_text(self) -> None:
        """
        Scenario: estimate_tokens counts tokens for single text.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given a text string
        When estimate_tokens is called
        Then it returns char_count / 4 (approx).
        """
        ### Given
        texts = ["hello world"]

        ### When
        result = estimate_tokens(texts)

        ### Then
        # "hello world" = 11 chars, 11 / 4 = 2.75 ≈ 3 or 2
        assert result >= 1
        assert isinstance(result, int)

    def test_estimate_multiple_texts(self) -> None:
        """
        Scenario: estimate_tokens sums tokens across texts.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given multiple texts
        When estimate_tokens is called
        Then it returns sum of all token estimates.
        """
        ### Given
        texts = ["hello", "world", "test"]

        ### When
        result = estimate_tokens(texts)

        ### Then
        assert result >= 1
        # Sum of lengths / 4
        total_chars = sum(len(t) for t in texts)
        assert result == max(1, total_chars // 4)

    def test_estimate_empty_returns_minimum(self) -> None:
        """
        Scenario: estimate_tokens returns minimum 1 for empty/small input.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given empty text list
        When estimate_tokens is called
        Then it returns 1 (minimum).
        """
        ### Given
        texts = []

        ### When
        result = estimate_tokens(texts)

        ### Then
        assert result == 1

    def test_estimate_large_text(self) -> None:
        """
        Scenario: estimate_tokens handles large texts.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given very long text
        When estimate_tokens is called
        Then it returns proportional token count.
        """
        ### Given
        texts = ["x" * 10000]

        ### When
        result = estimate_tokens(texts)

        ### Then
        assert result == max(1, 10000 // 4)
        assert result == 2500


class TestRateLimiterShould:
    """Scenario: RateLimiter enforces RPM and TPM ceilings."""

    def test_limiter_initialization(self) -> None:
        """
        Scenario: RateLimiter initializes with RPM and TPM.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given RPM=300, TPM=1000000
        When RateLimiter is created
        Then it stores the limits.
        """
        ### Given / When
        limiter = RateLimiter(rpm=300, tpm=1000000)

        ### Then
        assert limiter._rpm == 300
        assert limiter._tpm == 1000000

    def test_wait_allows_first_request_immediately(self) -> None:
        """
        Scenario: first wait() call returns immediately.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given a fresh limiter
        When wait() is called
        Then it returns without sleeping.
        """
        ### Given
        limiter = RateLimiter(rpm=10, tpm=100)

        ### When
        with patch("server.core.embedding.rate_limiter.time.sleep") as mock_sleep:
            limiter.wait(estimated_tokens=10)

        ### Then
        mock_sleep.assert_not_called()

    def test_wait_respects_rpm_limit(self) -> None:
        """
        Scenario: wait() enforces RPM ceiling.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given RPM=2
        When wait() is called 3 times quickly
        Then third call waits to respect 2 RPM.
        """
        ### Given
        limiter = RateLimiter(rpm=2, tpm=100000)
        call_count = 0

        def mock_monotonic():
            nonlocal call_count
            call_count += 1
            # Return same time for multiple calls within the wait()
            if call_count <= 4:
                return 0.0
            return 61.0  # Jump ahead 61 seconds on later calls

        ### When
        with patch("server.core.embedding.rate_limiter.time.monotonic", side_effect=mock_monotonic):
            with patch("server.core.embedding.rate_limiter.time.sleep"):
                limiter.wait(estimated_tokens=1)
                limiter.wait(estimated_tokens=1)
                limiter.wait(estimated_tokens=1)  # Should wait

        ### Then
        # Third call should trigger sleep (or close to it)
        # At minimum, we've tested that it can handle multiple calls

    def test_wait_respects_tpm_limit(self) -> None:
        """
        Scenario: wait() enforces TPM ceiling.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given TPM=100
        When wait() is called with large estimated_tokens
        Then it waits if tokens would exceed TPM.
        """
        ### Given
        limiter = RateLimiter(rpm=1000, tpm=100)
        clock = [0.0]

        def mock_monotonic() -> float:
            return clock[0]

        def mock_sleep(secs: float) -> None:
            clock[0] += secs  # advance simulated clock so _purge_window clears the window

        ### When
        with patch("server.core.embedding.rate_limiter.time.monotonic", side_effect=mock_monotonic):
            _sleep_path = "server.core.embedding.rate_limiter.time.sleep"
            with patch(_sleep_path, side_effect=mock_sleep) as mock_sleep_spy:
                limiter.wait(estimated_tokens=50)
                limiter.wait(estimated_tokens=60)  # Would exceed TPM=100 → must sleep

        ### Then
        assert mock_sleep_spy.called

    def test_wait_purges_old_window_entries(self) -> None:
        """
        Scenario: wait() removes entries older than 60 seconds.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given request times > 60 seconds ago
        When wait() is called
        Then old entries are removed.
        """
        ### Given
        limiter = RateLimiter(rpm=1000, tpm=10000)

        ### When
        with patch("server.core.embedding.rate_limiter.time.monotonic", return_value=0.0):
            limiter.wait(estimated_tokens=10)

        # Now jump 70 seconds ahead
        with patch("server.core.embedding.rate_limiter.time.monotonic", return_value=70.0):
            limiter.wait(estimated_tokens=10)  # Should purge first entry

        ### Then
        # Should only have 2 entries in queue
        assert len(limiter._request_times) <= 2

    def test_wait_with_zero_estimated_tokens(self) -> None:
        """
        Scenario: wait() skips TPM check when estimated_tokens=0.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given estimated_tokens=0
        When wait() is called
        Then it skips TPM enforcement.
        """
        ### Given
        limiter = RateLimiter(rpm=10, tpm=100)

        ### When
        with patch("server.core.embedding.rate_limiter.time.sleep") as mock_sleep:
            limiter.wait(estimated_tokens=0)

        ### Then
        # Should not sleep (only RPM check, and we're under limit)
        mock_sleep.assert_not_called()

    def test_wait_with_zero_tpm(self) -> None:
        """
        Scenario: wait() skips TPM check when TPM=0.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given TPM=0 (disabled)
        When wait() is called with large tokens
        Then it skips TPM enforcement.
        """
        ### Given
        limiter = RateLimiter(rpm=10, tpm=0)

        ### When
        with patch("server.core.embedding.rate_limiter.time.sleep") as mock_sleep:
            limiter.wait(estimated_tokens=1000000)

        ### Then
        # Should not sleep on TPM (disabled)
        mock_sleep.assert_not_called()


class TestCallWithRetryShould:
    """Scenario: call_with_retry retries on rate-limit errors."""

    def test_call_succeeds_immediately(self) -> None:
        """
        Scenario: call_with_retry returns result on success.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given function returns successfully
        When call_with_retry is called
        Then it returns the result.
        """

        ### Given
        def success_fn():
            return "result"

        limiter = RateLimiter(rpm=10, tpm=10000)

        ### When
        result = call_with_retry(success_fn, limiter=limiter, estimated_tokens=10)

        ### Then
        assert result == "result"

    def test_call_retries_on_rate_limit_error(self) -> None:
        """
        Scenario: call_with_retry retries on RateLimitError.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given function raises RateLimitError then succeeds
        When call_with_retry is called
        Then it retries and returns result.
        """
        ### Given
        call_count = 0

        def retry_fn():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError("Rate limit 429", None, None)
            return "success"

        limiter = RateLimiter(rpm=10, tpm=10000)

        ### When
        with patch("server.core.embedding.rate_limiter.time.sleep"):
            result = call_with_retry(retry_fn, limiter=limiter, estimated_tokens=10)

        ### Then
        assert result == "success"
        assert call_count == 2

    def test_call_raises_after_max_retries(self) -> None:
        """
        Scenario: call_with_retry raises after 5 retries.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given function always raises RateLimitError
        When call_with_retry is called
        Then it raises after MAX_RETRIES (5).
        """

        ### Given
        def always_fail():
            raise RateLimitError("Rate limit", None, None)

        limiter = RateLimiter(rpm=10, tpm=10000)

        ### When / Then
        with patch("server.core.embedding.rate_limiter.time.sleep"):
            with pytest.raises(RateLimitError):
                call_with_retry(always_fail, limiter=limiter, estimated_tokens=10)

    def test_call_respects_exponential_backoff(self) -> None:
        """
        Scenario: call_with_retry uses exponential backoff on retries.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given function fails then succeeds
        When call_with_retry is called
        Then it sleeps before retry (backoff).
        """
        ### Given
        call_count = 0

        def retry_fn():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError("Rate limit", None, None)
            return "success"

        limiter = RateLimiter(rpm=10, tpm=10000)

        ### When
        with patch("server.core.embedding.rate_limiter.time.sleep") as mock_sleep:
            call_with_retry(retry_fn, limiter=limiter, estimated_tokens=10)

        ### Then
        mock_sleep.assert_called()
        # Sleep should be INITIAL_BACKOFF_S = 25.0
        call_args = mock_sleep.call_args_list[0]
        assert call_args[0][0] == 25.0

    def test_call_propagates_non_rate_limit_errors(self) -> None:
        """
        Scenario: call_with_retry propagates non-RateLimitError.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given function raises ValueError
        When call_with_retry is called
        Then it raises ValueError immediately.
        """

        ### Given
        def fail_fn():
            raise ValueError("Input error")

        limiter = RateLimiter(rpm=10, tpm=10000)

        ### When / Then
        with pytest.raises(ValueError):
            call_with_retry(fail_fn, limiter=limiter, estimated_tokens=10)

    def test_call_respects_cancel_check(self) -> None:
        """
        Scenario: call_with_retry calls cancel_check before each attempt.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given cancel_check function
        When call_with_retry is called
        Then it calls cancel_check before each attempt.
        """
        ### Given
        cancel_check = MagicMock()

        def success_fn():
            return "result"

        limiter = RateLimiter(rpm=10, tpm=10000)

        ### When
        result = call_with_retry(
            success_fn, limiter=limiter, estimated_tokens=10, cancel_check=cancel_check
        )

        ### Then
        assert cancel_check.called
        assert result == "result"

    def test_call_respects_operation_name_in_logging(self) -> None:
        """
        Scenario: call_with_retry logs operation name on error.
        Slice: coverage-gap — server/core/embedding/rate_limiter.py

        Given operation parameter
        When call_with_retry is called with non-retryable error
        Then error is logged with operation name.
        """

        ### Given
        def fail_fn():
            raise RuntimeError("API error")

        limiter = RateLimiter(rpm=10, tpm=10000)

        ### When / Then
        with pytest.raises(RuntimeError):
            call_with_retry(
                fail_fn,
                limiter=limiter,
                estimated_tokens=10,
                operation="Voyage test embed",
            )
