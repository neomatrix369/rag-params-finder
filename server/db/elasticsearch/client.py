"""Lazy Elasticsearch client. Imported only when the ES vector store is selected."""

from __future__ import annotations

from typing import Any

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


def is_connection_failure(exc: BaseException) -> bool:
    """True for transport timeouts and connection failures, not query 400s."""
    name = type(exc).__name__
    return name in {"ConnectionError", "ConnectionTimeout"} or isinstance(exc, OSError)


def raise_if_unreachable(exc: BaseException, url: str) -> None:
    """Re-raise connection failures with a remediation that names the URL."""
    if is_connection_failure(exc):
        raise ElasticsearchUnreachableError(
            f"Elasticsearch unreachable at {url}. "
            "Check ELASTICSEARCH_CLOUD_URL or ELASTICSEARCH_LOCAL_URL "
            "and that the service is running."
        ) from exc
