"""Dedicated thread pools so sweep work does not starve API handlers.

FastAPI BackgroundTasks and ``asyncio.to_thread`` both use the default
ThreadPoolExecutor. Long-running sweeps and expensive vector-db aggregations
were competing with lightweight list/detail reads, so the dashboard could hang
on GET /experiments while a sweep was active.
"""

from __future__ import annotations

import atexit
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import ParamSpec

from server.utils.logger import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")

# One sweep per process — matches current parallelism: 1 semantics.
SWEEP_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rag-sweep")

# Expensive read-only aggregations (vector-db-stats, per-experiment db-stats).
HEAVY_READ_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rag-heavy-read")


def _run_sweep_safe[R, **P](fn: Callable[P, R], /, *args: P.args, **kwargs: P.kwargs) -> None:
    """Execute sweep fn; log unhandled exceptions (thread pool swallows them otherwise)."""
    experiment_id = args[0] if args else "?"
    try:
        fn(*args, **kwargs)
    except Exception:
        logger.error(
            "Sweep task failed for experiment %s (%s)",
            experiment_id,
            fn.__name__,
            exc_info=True,
        )


def schedule_sweep[R, **P](fn: Callable[P, R], /, *args: P.args, **kwargs: P.kwargs) -> None:
    """Fire-and-forget sweep execution on the isolated sweep pool."""
    SWEEP_EXECUTOR.submit(_run_sweep_safe, fn, *args, **kwargs)


def shutdown_executors() -> None:
    SWEEP_EXECUTOR.shutdown(wait=False, cancel_futures=True)
    HEAVY_READ_EXECUTOR.shutdown(wait=False, cancel_futures=True)


atexit.register(shutdown_executors)
