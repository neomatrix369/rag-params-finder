"""Elasticsearch URL classification — local loopback vs cloud."""

from __future__ import annotations

from urllib.parse import urlparse

STORAGE_MODE_ELASTICSEARCH_LOCAL = "elasticsearch-local"
STORAGE_MODE_ELASTICSEARCH_CLOUD = "elasticsearch-cloud"

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def elasticsearch_storage_mode(url: str) -> str:
    """Return ``elasticsearch-local`` or ``elasticsearch-cloud``."""
    host = (urlparse(url.strip()).hostname or "").lower()
    if host in _LOCAL_HOSTS:
        return STORAGE_MODE_ELASTICSEARCH_LOCAL
    if host:
        return STORAGE_MODE_ELASTICSEARCH_CLOUD
    return STORAGE_MODE_ELASTICSEARCH_LOCAL


def cluster_host(url: str) -> str | None:
    """Hostname for db-stats, or None when the URL has none."""
    host = urlparse(url.strip()).hostname
    return host or None
