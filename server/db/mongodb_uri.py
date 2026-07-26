"""MongoDB connection-string helpers (cloud Atlas vs local/other backends)."""

from __future__ import annotations

from datetime import UTC
from typing import Any

STORAGE_MODE_MONGODB_LOCAL = "mongodb-local"
STORAGE_MODE_MONGODB_CLOUD = "mongodb-cloud"


def is_atlas_uri(uri: str) -> bool:
    """True when the URI targets MongoDB Atlas cloud (*.mongodb.net)."""
    return ".mongodb.net" in uri.strip()


def mongodb_storage_mode(uri: str) -> str:
    """Classify the backend as ``mongodb-cloud`` or ``mongodb-local``.

    Values match planned ``./start-services.sh --{storage_mode}`` flag compounds
    (Slice 36 / Slice 27 absorption). Atlas cloud uses ``*.mongodb.net``;
    everything else (Atlas Local, plain localhost) is local.
    """
    return STORAGE_MODE_MONGODB_CLOUD if is_atlas_uri(uri) else STORAGE_MODE_MONGODB_LOCAL


def mongo_client_kwargs(uri: str, **extra: Any) -> dict[str, Any]:
    """Build pymongo MongoClient kwargs — TLS only for Atlas cloud URIs."""
    kwargs: dict[str, Any] = {"tz_aware": True, "tzinfo": UTC, **extra}
    if is_atlas_uri(uri):
        import certifi

        kwargs["tlsCAFile"] = certifi.where()
    return kwargs


def parse_atlas_cluster_name(uri: str) -> str | None:
    """Extract Atlas cluster name from an SRV connection string host."""
    trimmed = uri.strip()
    if not trimmed or ".mongodb.net" not in trimmed:
        return None
    without_scheme = trimmed.split("://", 1)[-1]
    host_part = without_scheme.split("@")[-1].split("/")[0].split("?")[0]
    if not host_part.endswith(".mongodb.net"):
        return None
    cluster_part = host_part.removesuffix(".mongodb.net")
    name = cluster_part.split(".")[0]
    return name or None
