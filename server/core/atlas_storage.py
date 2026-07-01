"""Resolve MongoDB Atlas cluster storage quota for dashboard UI."""

from __future__ import annotations

import time
from typing import Any

import httpx

from server.db.mongodb_uri import is_atlas_uri, parse_atlas_cluster_name
from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

ATLAS_API_BASE = "https://cloud.mongodb.com/api/atlas/v2"
ATLAS_ACCEPT = "application/vnd.atlas.2023-01-01+json"
CACHE_TTL_SECONDS = 300

# Shared-tier logical storage caps (MB). Dedicated tiers use diskSizeGB from the API.
# Atlas API returns diskSizeGB=null for M0/M2/M5, so these fallback values are necessary.
TIER_STORAGE_LIMIT_MB: dict[str, float] = {
    "M0": 512.0,
    "M2": 2048.0,
    "M5": 5120.0,
}

_limit_cache: tuple[float | None, float] | None = None
_tier_cache: tuple[dict[str, str | float | None] | None, float] | None = None


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


def resolve_tier_specs() -> dict[str, str | float | None] | None:
    """Return tier specifications from Atlas API (instance size, storage, provider, region).

    Returns only fields available from Atlas Admin API:
    - instance_size: from API instanceSizeName (e.g., "M0", "M10")
    - storage_mb: from API diskSizeGB (dedicated) or TIER_STORAGE_LIMIT_MB (shared fallback)
    - tier_type: derived from API providerName ("TENANT" = shared)
    - provider: from API backingProviderName (e.g., "AWS", "GCP")
    - region: from API regionName (e.g., "US_EAST_1")

    Does NOT return (not exposed by Atlas API):
    - RAM specifications
    - vCPU specifications
    - Cost/pricing
    """
    global _tier_cache
    now = time.monotonic()

    # Check cache first
    if _tier_cache is not None:
        specs, expires_at = _tier_cache
        if now < expires_at:
            return specs

    # Manual override — storage only
    override = settings.mongodb_storage_limit_mb
    if override > 0:
        specs = {
            "instance_size": "manual",
            "storage_mb": override,
            "tier_type": "manual",
            "provider": None,
            "region": None,
        }
        _tier_cache = (specs, now + CACHE_TTL_SECONDS)
        return specs

    if not is_atlas_uri(settings.mongodb_uri):
        return None

    if not _atlas_api_configured():
        return None

    # Fetch from Atlas API
    specs = _fetch_atlas_tier_specs()
    _tier_cache = (specs, now + CACHE_TTL_SECONDS)
    return specs


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
        logger.warning(
            "atlas storage quota skip — cluster name unavailable from MONGODB_URI",
        )
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
        logger.warning(
            "atlas storage quota lookup failed — cluster=%s error=%s",
            cluster_name,
            exc,
        )
        return None

    return _storage_limit_mb_from_cluster(payload)


def _fetch_atlas_tier_specs() -> dict[str, str | float | None] | None:
    """Fetch tier specifications from Atlas API.

    Returns only API-available fields (instance_size, storage_mb, provider, region).
    Storage fallback from TIER_STORAGE_LIMIT_MB for shared tiers where API returns null.
    """
    cluster_name = settings.atlas_cluster_name.strip() or parse_atlas_cluster_name(
        settings.mongodb_uri
    )
    if not cluster_name:
        logger.warning(
            "atlas tier specs skip — cluster name unavailable from MONGODB_URI",
        )
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
            cluster = response.json()
    except httpx.HTTPError as exc:
        logger.warning(
            "atlas tier specs lookup failed — cluster=%s error=%s",
            cluster_name,
            exc,
        )
        return None

    return _tier_specs_from_cluster(cluster)


def _tier_specs_from_cluster(cluster: dict[str, Any]) -> dict[str, str | float | None] | None:
    """Extract tier specifications from Atlas API cluster response.

    Returns only fields available from the API response:
    - instance_size, provider, region: from API
    - storage_mb: from API (dedicated) or TIER_STORAGE_LIMIT_MB fallback (shared)
    - tier_type: derived from providerName
    """
    provider_settings = cluster.get("providerSettings") or {}
    instance_size = _instance_size_name(cluster)

    if not instance_size:
        logger.warning(
            "atlas tier specs incomplete — instance_size unavailable in API payload",
        )
        return None

    # Provider and region from API
    provider_name = provider_settings.get("providerName")  # "TENANT" or "AWS"/"GCP"/"AZURE"
    backing_provider = provider_settings.get("backingProviderName")  # "AWS", "GCP", "AZURE"
    region = provider_settings.get("regionName")  # "US_EAST_1", etc.

    # Determine tier type
    is_shared = provider_name == "TENANT"
    tier_type = "shared" if is_shared else "dedicated"

    # Storage: from API (dedicated) or fallback (shared)
    disk_gb = _disk_size_gb(cluster)
    if disk_gb is not None and disk_gb > 0:
        storage_mb = round(disk_gb * 1024, 2)
    elif instance_size in TIER_STORAGE_LIMIT_MB:
        storage_mb = TIER_STORAGE_LIMIT_MB[instance_size]
    else:
        logger.info("atlas tier storage unknown — falling back tier=%s", instance_size)
        storage_mb = None

    return {
        "instance_size": instance_size,
        "storage_mb": storage_mb,
        "tier_type": tier_type,
        "provider": backing_provider,
        "region": region,
    }


def _storage_limit_mb_from_cluster(cluster: dict[str, Any]) -> float | None:
    disk_gb = _disk_size_gb(cluster)
    if disk_gb is not None and disk_gb > 0:
        return round(disk_gb * 1024, 2)

    tier = _instance_size_name(cluster)
    if tier and tier in TIER_STORAGE_LIMIT_MB:
        return TIER_STORAGE_LIMIT_MB[tier]

    if tier:
        logger.info("atlas storage quota unknown tier — quota hidden tier=%s", tier)
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
