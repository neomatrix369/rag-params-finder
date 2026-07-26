"""Health probes for /healthz and Docker Compose.

The active ``STORAGE_BACKEND`` decides which dependency must be reachable.
Mongo mode still pings Atlas / Atlas Local; Postgres mode pings the configured
``DATABASE_URL``. Mixing the two — e.g. failing a Mongo ping when the server
is running on pgvector — marks a healthy stack as unhealthy and blocks Compose.
"""

from __future__ import annotations

import psycopg
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from server.db.mongodb_uri import mongo_client_kwargs
from server.db.postgres_uri import postgres_connect_kwargs
from server.settings import normalize_storage_backend, settings

_MONGODB_PLACEHOLDER_MARKERS = (
    "your_mongodb_atlas_uri_here",
    "<user>",
    "<pass>",
    "<cluster>",
)

# Keep well under the Docker HEALTHCHECK timeout (10s).
_POSTGRES_CONNECT_TIMEOUT_S = 5


def mongodb_health_status() -> str:
    """Return ok, error, or skipped for Atlas connectivity."""
    uri = (settings.mongodb_uri or "").strip()
    if not uri:
        return "skipped"
    lowered = uri.lower()
    if any(marker in lowered for marker in _MONGODB_PLACEHOLDER_MARKERS):
        return "error"
    try:
        # Short timeout — default MongoClient waits ~30s; Docker healthcheck allows 10s.
        client: MongoClient = MongoClient(
            uri,
            **mongo_client_kwargs(
                uri,
                serverSelectionTimeoutMS=settings.health_check_mongodb_timeout_ms,
            ),
        )
        client.admin.command("ping")
        return "ok"
    except (PyMongoError, ValueError, OSError):
        return "error"


def postgres_health_status() -> str:
    """Return ok, error, or skipped for Postgres / pgvector connectivity."""
    uri = (settings.database_url or "").strip()
    if not uri:
        return "skipped"
    try:
        with psycopg.connect(
            uri,
            connect_timeout=_POSTGRES_CONNECT_TIMEOUT_S,
            **postgres_connect_kwargs(uri),
        ) as conn:
            conn.execute("SELECT 1")
        return "ok"
    except (psycopg.Error, ValueError, OSError):
        return "error"


def storage_health() -> dict[str, str | bool]:
    """Probe the configured storage backend and decide whether the process is ready.

    Returns a body fragment for ``/healthz`` / ``/health``:
    ``ok``, ``storage_backend``, and either ``mongodb`` or ``postgres``.
    """
    backend = normalize_storage_backend(settings.storage_backend or "mongodb")
    if backend == "postgres":
        postgres = postgres_health_status()
        return {
            "ok": postgres == "ok",
            "storage_backend": "postgres",
            "postgres": postgres,
        }
    if backend == "mongodb":
        mongodb = mongodb_health_status()
        return {
            "ok": mongodb in ("ok", "skipped"),
            "storage_backend": "mongodb",
            "mongodb": mongodb,
        }
    return {
        "ok": False,
        "storage_backend": backend,
        "error": f"unknown storage backend {backend!r}",
    }
