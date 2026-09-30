"""Lazy Redis client — imported only when the Redis vector store is selected."""

from __future__ import annotations

from typing import Any

INSTALL_EXTRA_MESSAGE = (
    'Redis client is not installed. Install the optional extra: pip install -e ".[redis]"'
)


class RedisClientMissingError(RuntimeError):
    """Raised when VECTOR_STORE_BACKEND=redis but the extra is absent."""


class RedisUnreachableError(ConnectionError):
    """Raised when Redis cannot be reached. Never a silent empty hit list."""


def import_redis() -> Any:
    """Import the redis-py package, or raise install guidance."""
    try:
        import redis  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RedisClientMissingError(INSTALL_EXTRA_MESSAGE) from exc
    return redis


def build_client(url: str) -> Any:
    """Open a Redis client from a URL. Credentials inside the URL are not logged."""
    redis = import_redis()
    client = redis.Redis.from_url(url, socket_timeout=10, socket_connect_timeout=10)
    return client


def is_connection_failure(exc: BaseException) -> bool:
    """True for connection errors and timeouts, not query/command errors."""
    name = type(exc).__name__
    return name in {
        "ConnectionError",
        "TimeoutError",
        "BusyLoadingError",
    } or isinstance(exc, OSError)


def raise_if_unreachable(exc: BaseException, url: str) -> None:
    """Re-raise connection failures with a remediation hint that names the URL."""
    if is_connection_failure(exc):
        from server.db.redis.uri import redis_storage_mode

        mode = redis_storage_mode(url)
        hint = (
            "Check REDIS_URL and that the Redis service is running "
            "(./start-services.sh --redis-local for local, or REDIS_URL=rediss://… for cloud). "
            "See docs/user-guide/redis-setup.md."
        )
        raise RedisUnreachableError(f"Redis unreachable at {mode!r}. {hint}") from exc
