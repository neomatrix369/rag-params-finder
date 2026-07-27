"""Postgres connection-string helpers (hosted Supabase vs local pgvector).

Mirrors ``server.db.mongo.mongodb_uri`` for the Postgres backend: detect where the
database lives, and derive the connection settings that differ between hosted
Supabase (TLS required) and a local Docker container (no TLS).
"""

from __future__ import annotations

from typing import Any

STORAGE_MODE_POSTGRES_LOCAL = "postgres-local"
STORAGE_MODE_POSTGRES_CLOUD = "postgres-cloud"

# Legacy aliases — remove after Slice 37 flag cutover when no callers remain.
STORAGE_MODE_LOCAL_POSTGRES = STORAGE_MODE_POSTGRES_LOCAL
STORAGE_MODE_SUPABASE = STORAGE_MODE_POSTGRES_CLOUD

_SUPABASE_HOST_SUFFIXES = (".supabase.co", ".supabase.com", ".supabase.net")


def parse_postgres_host(uri: str) -> str | None:
    """Extract the host (without port) from a Postgres connection string."""
    trimmed = uri.strip()
    if not trimmed:
        return None
    without_scheme = trimmed.split("://", 1)[-1]
    authority = without_scheme.split("/")[0].split("?")[0]
    host_port = authority.split("@")[-1]
    if host_port.startswith("["):  # IPv6 literal, e.g. [::1]:5432
        host = host_port.split("]")[0] + "]"
    else:
        host = host_port.split(":")[0]
    return host or None


def is_supabase_uri(uri: str) -> bool:
    """True when the URI targets a hosted Supabase project."""
    host = parse_postgres_host(uri)
    return host is not None and host.endswith(_SUPABASE_HOST_SUFFIXES)


def postgres_storage_mode(uri: str) -> str:
    """Classify the backend as ``postgres-cloud`` or ``postgres-local``.

    Values match planned ``./start-services.sh --{storage_mode}`` flag compounds
    (Slice 36 / 37). Exposed via ``/healthz`` and db-stats ``cluster_tier_type``.
    """
    return STORAGE_MODE_POSTGRES_CLOUD if is_supabase_uri(uri) else STORAGE_MODE_POSTGRES_LOCAL


def postgres_connect_kwargs(uri: str, **extra: Any) -> dict[str, Any]:
    """Build psycopg connection kwargs — TLS required only for hosted Supabase.

    An explicit ``sslmode`` in the URI always wins, so operators can force
    ``verify-full`` (or disable TLS on a self-managed host) without code changes.
    """
    kwargs: dict[str, Any] = {**extra}
    if is_supabase_uri(uri) and "sslmode" not in uri:
        kwargs["sslmode"] = "require"
    return kwargs
