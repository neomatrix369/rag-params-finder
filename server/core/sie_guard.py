"""Preflight guard: verify SIE is enabled and reachable before SIE embedding sweeps."""

from __future__ import annotations

import httpx

from server.models.config import ExperimentConfig
from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

_HEALTH_PROBE_TIMEOUT_S = 3.0


def sie_auth_headers() -> dict[str, str]:
    """Return Authorization header when SIE_API_KEY is configured."""
    if settings.sie_api_key:
        return {"Authorization": f"Bearer {settings.sie_api_key}"}
    return {}


class SIEUnavailableError(Exception):
    """Raised when a sweep requires SIE but the server is disabled or unreachable."""


def requires_sie(config: ExperimentConfig) -> bool:
    """Return True when the experiment config uses the SIE embedding provider."""
    return config.embedding.provider == "sie"


def probe_sie_reachable() -> bool:
    """Return True when SIE responds with HTTP 200 on /healthz."""
    try:
        resp = httpx.get(
            f"{settings.sie_endpoint.rstrip('/')}/healthz",
            headers=sie_auth_headers(),
            timeout=_HEALTH_PROBE_TIMEOUT_S,
        )
        return resp.status_code == 200
    except Exception:
        return False


def validate_sie_readiness(config: ExperimentConfig) -> None:
    """Ensure SIE is configured and reachable when the sweep needs it.

    Raises:
        SIEUnavailableError: When provider is ``sie`` but SIE is disabled or down.
    """
    if not requires_sie(config):
        return

    if not settings.sie_enabled:
        raise SIEUnavailableError(
            "SIE embedding provider requires SIE_ENABLED=true in server .env. "
            "Set SIE_ENDPOINT to your SIE gateway URL — see docs/user-guide/sie-setup.md"
        )

    if probe_sie_reachable():
        return

    raise SIEUnavailableError(
        f"SIE server unreachable at {settings.sie_endpoint}. "
        "Ensure SIE is running and SIE_ENDPOINT (and SIE_API_KEY if required) are set — "
        "see docs/user-guide/sie-setup.md"
    )


def check_sie_health() -> str:
    """Health endpoint helper: ``disabled`` | ``reachable`` | ``unreachable``."""
    if not settings.sie_enabled:
        return "disabled"
    return "reachable" if probe_sie_reachable() else "unreachable"
