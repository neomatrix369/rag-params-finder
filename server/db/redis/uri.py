"""Redis URL classification — local loopback vs cloud (TLS)."""

from __future__ import annotations

from urllib.parse import urlparse

STORAGE_MODE_REDIS_LOCAL = "redis-local"
STORAGE_MODE_REDIS_CLOUD = "redis-cloud"

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "redis-local"})


def redis_storage_mode(url: str) -> str:
    """Return ``redis-local`` or ``redis-cloud``.

    TLS (``rediss://``) always indicates a managed / cloud endpoint.
    Loopback and the Compose service name are local.
    An empty URL stays local so a missing setting does not pretend to be cloud.
    """
    cleaned = url.strip()
    if cleaned.startswith("rediss://"):
        return STORAGE_MODE_REDIS_CLOUD
    host = (urlparse(cleaned).hostname or "").lower()
    if not host or host in _LOCAL_HOSTS or "." not in host:
        return STORAGE_MODE_REDIS_LOCAL
    return STORAGE_MODE_REDIS_CLOUD


def cluster_host(url: str) -> str | None:
    """Hostname for db-stats display, or None when the URL has none."""
    host = urlparse(url.strip()).hostname
    return host or None


def redact_url(url: str) -> str:
    """Return the URL with the password replaced by ``***``, for safe logging."""
    cleaned = url.strip()
    if not cleaned:
        return cleaned
    try:
        parsed = urlparse(cleaned)
        if parsed.password:
            cleaned = cleaned.replace(f":{parsed.password}@", ":***@")
    except Exception:  # pragma: no cover
        pass
    return cleaned
