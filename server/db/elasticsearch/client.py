"""Lazy Elasticsearch client. Imported only when the ES vector store is selected."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse, urlunparse

INSTALL_EXTRA_MESSAGE = (
    "Elasticsearch client is not installed. Install the optional extra: "
    'pip install -e ".[elasticsearch]"'
)


class ElasticsearchClientMissingError(RuntimeError):
    """Raised when VECTOR_STORE_BACKEND=elasticsearch but the extra is absent."""


class ElasticsearchUnreachableError(ConnectionError):
    """Raised when Elasticsearch cannot be reached. Never a silent empty hit list."""


def import_elasticsearch_class() -> Any:
    """Import the official client, or raise install guidance."""
    try:
        from elasticsearch import Elasticsearch  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ElasticsearchClientMissingError(INSTALL_EXTRA_MESSAGE) from exc
    return Elasticsearch


def build_client(url: str, api_key: str) -> Any:
    """Open a client. API key is passed through and must not be logged."""
    client_cls = import_elasticsearch_class()
    kwargs: dict[str, Any] = {"hosts": [url], "request_timeout": 10}
    if api_key.strip():
        kwargs["api_key"] = api_key
    return client_cls(**kwargs)


class ElasticsearchAuthError(RuntimeError):
    """Raised when Elasticsearch returns 401 or 403."""


class ElasticsearchRateLimitError(RuntimeError):
    """Raised when Elasticsearch returns 429."""


class ElasticsearchServiceUnavailableError(RuntimeError):
    """Raised when Elasticsearch returns 503 (cluster red/unavailable)."""


def mask_url(url: str) -> str:
    """Strip credentials from a URL for safe logging."""
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        host = parsed.hostname or ""
        port_suffix = f":{parsed.port}" if parsed.port else ""
        replaced = parsed._replace(netloc=f"***@{host}{port_suffix}")
        return urlunparse(replaced)
    return url


def is_connection_failure(exc: BaseException) -> bool:
    """True for transport timeouts and connection failures, not query 400s."""
    name = type(exc).__name__
    return name in {"ConnectionError", "ConnectionTimeout"} or isinstance(exc, OSError)


def _api_error_status(exc: BaseException) -> int | None:
    """Extract HTTP status from an elasticsearch ApiError (or subclass)."""
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status
    meta = getattr(exc, "meta", None)
    if meta is not None:
        st = getattr(meta, "status", None)
        if isinstance(st, int):
            return st
    return None


def raise_if_unreachable(exc: BaseException, url: str) -> None:
    """Re-raise connection/auth/rate-limit failures with actionable messages."""
    safe_url = mask_url(url)
    if is_connection_failure(exc):
        raise ElasticsearchUnreachableError(
            f"Elasticsearch unreachable at {safe_url}. "
            "Check ELASTICSEARCH_CLOUD_URL or ELASTICSEARCH_LOCAL_URL "
            "and that the service is running."
        ) from exc
    status = _api_error_status(exc)
    if status in (401, 403):
        raise ElasticsearchAuthError(
            f"Elasticsearch authentication failed (HTTP {status}) at {safe_url}. "
            "Check ELASTICSEARCH_API_KEY and cluster security settings."
        ) from exc
    if status == 429:
        raise ElasticsearchRateLimitError(
            f"Elasticsearch rate-limited (HTTP 429) at {safe_url}. "
            "Reduce bulk batch size or add retry/backoff."
        ) from exc
    if status == 503:
        raise ElasticsearchServiceUnavailableError(
            f"Elasticsearch unavailable (HTTP 503) at {safe_url}. "
            "Cluster may be starting up or in a red state."
        ) from exc
    if status is not None:
        raise ElasticsearchUnreachableError(
            f"Elasticsearch error (HTTP {status}) at {safe_url}. See server logs for details."
        ) from exc
