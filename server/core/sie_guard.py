"""Deprecated import path — use ``server.core.guards.sie_guard``."""

from server.core.guards.sie_guard import (
    SIEUnavailableError,
    check_sie_health,
    probe_sie_reachable,
    requires_sie,
    sie_auth_headers,
    validate_sie_readiness,
)

__all__ = [
    "SIEUnavailableError",
    "check_sie_health",
    "probe_sie_reachable",
    "requires_sie",
    "sie_auth_headers",
    "validate_sie_readiness",
]
