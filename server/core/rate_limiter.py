"""Sliding-window rate limiter + retry-with-backoff for Voyage AI API calls."""

import threading
import time
from collections import deque
from collections.abc import Callable

from voyageai.error import RateLimitError

from server.utils.logger import get_logger

logger = get_logger(__name__)

CHARS_PER_TOKEN_ESTIMATE = 4
MAX_RETRIES = 5
INITIAL_BACKOFF_S = 25.0
_WINDOW_S = 60.0  # sliding window duration (one minute)


class RateLimiter:
    """Thread-safe sliding-window limiter enforcing RPM and TPM ceilings."""

    def __init__(self, rpm: int, tpm: int) -> None:
        self._rpm = rpm
        self._tpm = tpm
        self._request_times: deque[float] = deque()
        self._token_log: deque[tuple[float, int]] = deque()
        self._lock = threading.Lock()

    def _purge_window(self, now: float) -> None:
        while self._request_times and now - self._request_times[0] > _WINDOW_S:
            self._request_times.popleft()
        while self._token_log and now - self._token_log[0][0] > _WINDOW_S:
            self._token_log.popleft()

    def _tokens_in_window(self) -> int:
        return sum(t for _, t in self._token_log)

    def wait(self, estimated_tokens: int = 0) -> None:
        """Block until the next request can be made within both limits."""
        with self._lock:
            self._wait_for_rpm()
            self._wait_for_tpm(estimated_tokens)
            now = time.monotonic()
            self._request_times.append(now)
            if estimated_tokens > 0:
                self._token_log.append((now, estimated_tokens))

    def _wait_for_rpm(self) -> None:
        while True:
            now = time.monotonic()
            self._purge_window(now)
            if len(self._request_times) < self._rpm:
                return
            sleep_for = self._request_times[0] + _WINDOW_S - now + 0.1
            if sleep_for <= 0:
                return
            logger.debug(f"Rate limiter: RPM ceiling ({self._rpm}), sleeping {sleep_for:.1f}s")
            self._lock.release()
            time.sleep(sleep_for)
            self._lock.acquire()

    def _wait_for_tpm(self, estimated_tokens: int) -> None:
        if self._tpm <= 0 or estimated_tokens <= 0:
            return
        while True:
            now = time.monotonic()
            self._purge_window(now)
            if self._tokens_in_window() + estimated_tokens <= self._tpm:
                return
            if not self._token_log:
                return
            sleep_for = self._token_log[0][0] + _WINDOW_S - now + 0.1
            if sleep_for <= 0:
                return
            logger.debug(f"Rate limiter: TPM ceiling ({self._tpm}), sleeping {sleep_for:.1f}s")
            self._lock.release()
            time.sleep(sleep_for)
            self._lock.acquire()


def call_with_retry[T](
    fn: Callable[[], T],
    limiter: RateLimiter,
    estimated_tokens: int = 0,
    *,
    operation: str = "Voyage API call",
) -> T:
    """Wait for rate-limit clearance, call *fn*, and retry on 429s with backoff."""
    backoff = INITIAL_BACKOFF_S
    for attempt in range(1, MAX_RETRIES + 1):
        limiter.wait(estimated_tokens=estimated_tokens)
        try:
            return fn()
        except RateLimitError as exc:
            if attempt == MAX_RETRIES:
                raise
            logger.warning(
                f"Voyage 429 on attempt {attempt}/{MAX_RETRIES}, backing off {backoff:.0f}s — {exc}"
            )
            time.sleep(backoff)
            backoff *= 2
        except Exception:
            logger.error(
                "%s failed on attempt %s/%s",
                operation,
                attempt,
                MAX_RETRIES,
                exc_info=True,
            )
            raise
    raise RuntimeError("unreachable")  # satisfies type checker


def estimate_tokens(texts: list[str]) -> int:
    return max(1, sum(len(t) for t in texts) // CHARS_PER_TOKEN_ESTIMATE)
