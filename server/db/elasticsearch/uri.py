"""Elasticsearch URL classification — local loopback vs cloud."""

from __future__ import annotations

from urllib.parse import urlparse

STORAGE_MODE_ELASTICSEARCH_LOCAL = "elasticsearch-local"
STORAGE_MODE_ELASTICSEARCH_CLOUD = "elasticsearch-cloud"

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "elasticsearch-local"})


def elasticsearch_storage_mode(url: str) -> str:
    """Return ``elasticsearch-local`` or ``elasticsearch-cloud``.

    Loopback and the Compose service name are local. A dotted public host
    (Elastic Cloud) is cloud. An empty URL stays local so a missing setting
    does not pretend to be a cloud cluster.
    """
    host = (urlparse(url.strip()).hostname or "").lower()
    if not host or host in _LOCAL_HOSTS or "." not in host:
        return STORAGE_MODE_ELASTICSEARCH_LOCAL
    return STORAGE_MODE_ELASTICSEARCH_CLOUD


def cluster_host(url: str) -> str | None:
    """Hostname for db-stats, or None when the URL has none."""
    host = urlparse(url.strip()).hostname
    return host or None
