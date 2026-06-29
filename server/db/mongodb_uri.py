"""MongoDB connection-string helpers (cloud Atlas vs local/other backends)."""

from __future__ import annotations


def is_atlas_uri(uri: str) -> bool:
    """True when the URI targets MongoDB Atlas cloud (*.mongodb.net)."""
    return ".mongodb.net" in uri.strip()


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
