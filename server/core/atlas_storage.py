"""Resolve MongoDB Atlas cluster storage quota for dashboard UI."""

from __future__ import annotations

import time
from typing import Any

import httpx

from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

ATLAS_API_BASE = "https://cloud.mongodb.com/api/atlas/v2"
ATLAS_ACCEPT = "application/vnd.atlas.2023-01-01+json"
CACHE_TTL_SECONDS = 300

# Shared-tier logical storage caps (MB). Dedicated tiers use diskSizeGB from the API.
TIER_STORAGE_LIMIT_MB: dict[str, float] = {
    "M0": 512.0,
    "M2": 2048.0,
    "M5": 5120.0,
}

_limit_cache: tuple[float | None, float] | None = None


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


def is_atlas_uri(uri: str) -> bool:
    return ".mongodb.net" in uri.strip()


def resolve_storage_limit_mb() -> float | None:
    """Return cluster storage quota in MB, or None when unknown."""
    override = settings.mongodb_storage_limit_mb
    if override > 0:
        return override

    if not is_atlas_uri(settings.mongodb_uri):
        return None

    if not _atlas_api_configured():
        return None

    return _cached_atlas_storage_limit_mb()


def _atlas_api_configured() -> bool:
    return bool(
        settings.atlas_public_key.strip()
        and settings.atlas_private_key.strip()
        and settings.atlas_group_id.strip()
    )


def _cached_atlas_storage_limit_mb() -> float | None:
    global _limit_cache
    now = time.monotonic()
    if _limit_cache is not None:
        limit_mb, expires_at = _limit_cache
        if now < expires_at:
            return limit_mb

    limit_mb = _fetch_atlas_storage_limit_mb()
    _limit_cache = (limit_mb, now + CACHE_TTL_SECONDS)
    return limit_mb


def _fetch_atlas_storage_limit_mb() -> float | None:
    cluster_name = settings.atlas_cluster_name.strip() or parse_atlas_cluster_name(
        settings.mongodb_uri
    )
    if not cluster_name:
        logger.warning("Atlas storage quota: could not derive cluster name from MONGODB_URI")
        return None

    url = f"{ATLAS_API_BASE}/groups/{settings.atlas_group_id.strip()}/clusters/{cluster_name}"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                url,
                auth=(settings.atlas_public_key.strip(), settings.atlas_private_key.strip()),
                headers={"Accept": ATLAS_ACCEPT},
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        logger.warning("Atlas storage quota lookup failed for cluster %s: %s", cluster_name, exc)
        return None

    return _storage_limit_mb_from_cluster(payload)


def _storage_limit_mb_from_cluster(cluster: dict[str, Any]) -> float | None:
    disk_gb = _disk_size_gb(cluster)
    if disk_gb is not None and disk_gb > 0:
        return round(disk_gb * 1024, 2)

    tier = _instance_size_name(cluster)
    if tier and tier in TIER_STORAGE_LIMIT_MB:
        return TIER_STORAGE_LIMIT_MB[tier]

    if tier:
        logger.info("Atlas storage quota: unknown tier %s — quota hidden", tier)
    return None


def _disk_size_gb(cluster: dict[str, Any]) -> float | None:
    top_level = cluster.get("diskSizeGB")
    if isinstance(top_level, int | float) and top_level > 0:
        return float(top_level)

    for spec in cluster.get("replicationSpecs") or []:
        for region in spec.get("regionConfigs") or []:
            for electable in region.get("electableSpecs") or []:
                disk = electable.get("diskSizeGB")
                if isinstance(disk, int | float) and disk > 0:
                    return float(disk)
            disk = region.get("diskSizeGB")
            if isinstance(disk, int | float) and disk > 0:
                return float(disk)
    return None


def _instance_size_name(cluster: dict[str, Any]) -> str | None:
    provider = cluster.get("providerSettings") or {}
    name = provider.get("instanceSizeName")
    if isinstance(name, str) and name.strip():
        return name.strip().upper()

    for spec in cluster.get("replicationSpecs") or []:
        for region in spec.get("regionConfigs") or []:
            for electable in region.get("electableSpecs") or []:
                size = electable.get("instanceSize")
                if isinstance(size, str) and size.strip():
                    return size.strip().upper()
    return None
