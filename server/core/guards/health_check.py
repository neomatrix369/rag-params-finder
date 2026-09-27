"""Health probes for /healthz and Docker Compose.

The active ``STORAGE_BACKEND`` decides which dependency must be reachable.
Mongo mode still pings Atlas / Atlas Local; Postgres mode pings the configured
``DATABASE_URL``. Mixing the two — e.g. failing a Mongo ping when the server
is running on pgvector — marks a healthy stack as unhealthy and blocks Compose.
"""

from __future__ import annotations

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from server.db.mongo.mongodb_uri import mongo_client_kwargs, mongodb_storage_mode
from server.db.ports.registry import resolve_adapter
from server.db.postgres.postgres_uri import postgres_connect_kwargs, postgres_storage_mode
from server.settings import normalize_storage_backend, settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

_MONGODB_PLACEHOLDER_MARKERS = (
    "your_mongodb_atlas_uri_here",
    "<user>",
    "<pass>",
    "<cluster>",
)

# Keep well under the Docker HEALTHCHECK timeout (10s).
_POSTGRES_CONNECT_TIMEOUT_S = 5

_POSTGRES_CLOUD_ERROR_REMEDIATION = (
    "Postgres unreachable — if this is a free-tier Supabase project, resume it "
    "in the dashboard or upgrade; prefer Session-mode pooler URI "
    "(see docs/user-guide/postgres-setup.md Path B)."
)


def _is_postgres_backend(backend: str) -> bool:
    """Route the engine decision through the registry — no literal comparison.

    Compares the resolved adapter *class* (not the backend string) so this
    stops being a `== "postgres"` / `== "mongodb"` branch (Slice 49A output
    contract). An unrecognised backend degrades to False (today's implicit
    "anything that isn't postgres falls to the mongo path" behaviour).
    """
    try:
        return resolve_adapter(backend) is resolve_adapter("postgres")
    except ValueError:
        return False


def _is_mongodb_backend(backend: str) -> bool:
    """Same registry-routed decision for the Mongo side (see ``_is_postgres_backend``)."""
    try:
        return resolve_adapter(backend) is resolve_adapter("mongodb")
    except ValueError:
        return False


def resolve_storage_mode() -> str:
    """Return the four-value storage_mode for the active backend + URI."""
    backend = normalize_storage_backend(settings.storage_backend or "mongodb")
    if _is_postgres_backend(backend):
        return postgres_storage_mode(settings.database_url or "")
    return mongodb_storage_mode(settings.mongodb_uri or "")


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
    # Lazy import (same convention as store_factory.py): this module is shared
    # by both backends' health probes, so importing psycopg at module scope
    # would leak the Postgres driver into a Mongo-only process (GWT-1).
    import psycopg

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
    ``ok``, ``storage_backend``, ``storage_mode``, and either ``mongodb`` or ``postgres``.
    """
    backend = normalize_storage_backend(settings.storage_backend or "mongodb")
    mode = resolve_storage_mode()
    if _is_postgres_backend(backend):
        postgres = postgres_health_status()
        body: dict[str, str | bool] = {
            "ok": postgres == "ok",
            "storage_backend": "postgres",
            "storage_mode": mode,
            "postgres": postgres,
        }
        if postgres == "error":
            body["remediation"] = _POSTGRES_CLOUD_ERROR_REMEDIATION
            logger.warning("%s storage_mode=%s", _POSTGRES_CLOUD_ERROR_REMEDIATION, mode)
        return body
    if _is_mongodb_backend(backend):
        mongodb = mongodb_health_status()
        return {
            "ok": mongodb in ("ok", "skipped"),
            "storage_backend": "mongodb",
            "storage_mode": mode,
            "mongodb": mongodb,
        }
    return {
        "ok": False,
        "storage_backend": backend,
        "storage_mode": mode,
        "error": f"unknown storage backend {backend!r}",
    }
