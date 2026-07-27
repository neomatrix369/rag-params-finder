"""Deprecated import path — use ``server.core.guards.health_check``."""

from server.core.guards.health_check import (
    mongodb_health_status,
    postgres_health_status,
    resolve_storage_mode,
    storage_health,
)

__all__ = [
    "mongodb_health_status",
    "postgres_health_status",
    "resolve_storage_mode",
    "storage_health",
]
