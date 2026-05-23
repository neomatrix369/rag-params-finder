"""Rate-limit repetitive INFO logs from polling endpoints (Option A messages)."""

from __future__ import annotations

import logging
import time

POLL_LOG_INTERVAL_S = 60.0

_last_info_at: dict[str, float] = {}


def info_throttled(
    logger: logging.Logger,
    key: str,
    message: str,
    *args: object,
    interval_s: float = POLL_LOG_INTERVAL_S,
) -> None:
    """Log at INFO at most once per interval; otherwise DEBUG. Message uses Option A shape."""
    now = time.monotonic()
    if now - _last_info_at.get(key, 0.0) >= interval_s:
        _last_info_at[key] = now
        logger.info(message, *args)
        return
    logger.debug(message, *args)
