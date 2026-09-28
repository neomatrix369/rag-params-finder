"""Health probes for /healthz and Docker Compose.

The active ``STORAGE_BACKEND`` decides which dependency must be reachable.
Mongo mode still pings Atlas / Atlas Local; Postgres mode pings the configured
``DATABASE_URL``. Mixing the two — e.g. failing a Mongo ping when the server
is running on pgvector — marks a healthy stack as unhealthy and blocks Compose.
"""

from __future__ import annotations

import time

from server.core.guards.local_runtime import local_runtime_fields
from server.db.mongo.mongodb_uri import mongo_client_kwargs, mongodb_storage_mode
from server.db.ports.registry import is_same_adapter, resolve_adapter
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
    """Return the four-value storage_mode for the active (run-state) backend + URI."""
    backend = normalize_storage_backend(settings.storage_backend or "mongodb")
    if _is_postgres_backend(backend):
        return postgres_storage_mode(settings.database_url or "")
    return mongodb_storage_mode(settings.mongodb_uri or "")


def _storage_mode_for(backend: str) -> str:
    """Four-value storage_mode for an arbitrary named backend.

    When ``backend`` is the run-state store (``STORAGE_BACKEND``), delegates
    to ``resolve_storage_mode()`` itself so callers/tests that patch
    ``resolve_storage_mode`` keep working unchanged (Slice 49A
    characterization). Only a genuinely different (split) backend computes
    its mode directly here.
    """
    run_state_backend = normalize_storage_backend(settings.storage_backend or "mongodb")
    if backend == run_state_backend:
        return resolve_storage_mode()
    if _is_postgres_backend(backend):
        return postgres_storage_mode(settings.database_url or "")
    if _is_mongodb_backend(backend):
        return mongodb_storage_mode(settings.mongodb_uri or "")
    # Not-yet-registered vector-only store (Elasticsearch/Redis, Slice 50/53)
    # — no adapter exists to derive a real four-value mode from yet.
    return f"{backend}-unconfigured"


def mongodb_health_status() -> str:
    """Return ok, error, or skipped for Atlas connectivity."""
    uri = (settings.mongodb_uri or "").strip()
    if not uri:
        return "skipped"
    lowered = uri.lower()
    if any(marker in lowered for marker in _MONGODB_PLACEHOLDER_MARKERS):
        return "error"
    # Lazy import (same convention as postgres_health_status / store_factory.py):
    # this module is shared by both backends' health probes, so importing pymongo
    # at module scope would leak the Mongo driver into a Postgres-only process (GWT-1).
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError

    try:
        # Short timeout — default MongoClient waits ~30s; Docker healthcheck allows 10s.
        client = MongoClient(
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


def _probe_store(backend: str) -> dict[str, object]:
    """Probe one named backend; return provider/mode/ok/latency_ms (+ legacy fields).

    ``_legacy_key``/``_legacy_status`` carry the pre-49B per-engine key
    (``mongodb``/``postgres``) and its raw status string (``ok``/``error``/
    ``skipped``) — internal, stripped before the ``stores.*`` body is built
    (see ``_public_probe``).
    """
    mode = _storage_mode_for(backend)
    if _is_postgres_backend(backend):
        start = time.monotonic()
        status = postgres_health_status()
        ok = status == "ok"
        entry: dict[str, object] = {
            "provider": "postgres",
            "mode": mode,
            "ok": ok,
            "latency_ms": int((time.monotonic() - start) * 1000) if ok else None,
            "_legacy_key": "postgres",
            "_legacy_status": status,
        }
        if status == "error":
            entry["remediation"] = _POSTGRES_CLOUD_ERROR_REMEDIATION
        return entry
    if _is_mongodb_backend(backend):
        start = time.monotonic()
        status = mongodb_health_status()
        ok = status in ("ok", "skipped")
        return {
            "provider": "mongodb",
            "mode": mode,
            "ok": ok,
            "latency_ms": int((time.monotonic() - start) * 1000) if ok else None,
            "_legacy_key": "mongodb",
            "_legacy_status": status,
        }
    return _probe_registered_vector_store(backend, mode)


def _probe_registered_vector_store(backend: str, fallback_mode: str) -> dict[str, object]:
    """Probe a non-Mongo, non-Postgres vector store through its adapter.

    Unregistered names stay not-ok. A registered adapter that cannot be
    constructed or pinged is not-ok with a remediation string — ``/healthz``
    stays 503 instead of crashing the probe.
    """
    try:
        adapter_class = resolve_adapter(backend)
    except ValueError:
        return _unreachable_probe(backend, fallback_mode)
    start = time.monotonic()
    try:
        store = adapter_class()
        ok = bool(store.health_check())
        mode = str(store.storage_mode())
    except Exception:
        ok = False
        mode = fallback_mode
    entry: dict[str, object] = {
        "provider": backend,
        "mode": mode,
        "ok": ok,
        "latency_ms": int((time.monotonic() - start) * 1000) if ok else None,
        "_legacy_key": backend,
        "_legacy_status": "ok" if ok else "error",
    }
    if not ok:
        entry["remediation"] = (
            f"Vector store {backend!r} is unreachable. Check its connection "
            "settings and that the service is running."
        )
    return entry


def _unreachable_probe(backend: str, mode: str) -> dict[str, object]:
    return {
        "provider": backend,
        "mode": mode,
        "ok": False,
        "latency_ms": None,
        "_legacy_key": backend,
        "_legacy_status": "error",
        "remediation": f"Check {backend.upper()}_URL / ./start-services.sh {backend} status",
    }


def _public_probe(probe: dict[str, object]) -> dict[str, object]:
    """Strip internal legacy-shim fields from a probe for the ``stores.*`` body."""
    public: dict[str, object] = {
        "provider": probe["provider"],
        "mode": probe["mode"],
        "ok": probe["ok"],
        "latency_ms": probe["latency_ms"],
    }
    if "remediation" in probe:
        public["remediation"] = probe["remediation"]
    public.update(local_runtime_fields(str(probe["provider"]), str(probe["mode"])))
    return public


def storage_health() -> dict[str, object]:
    """Probe both stores and decide whether the process is ready (Slice 49B).

    Every key present before 49B stays, with the same meaning: ``ok``,
    ``storage_backend`` (the run-state store, i.e. ``STORAGE_BACKEND``),
    ``storage_mode`` (the **vector** store's mode in a split setup — matches
    the dashboard label), and the per-engine key (``mongodb``/``postgres``,
    including Mongo's ``"skipped"``). Adds: ``vector_store_backend``,
    ``run_state_mode``, and ``stores: {vector: {...}, run_state: {...}}``.
    Returns not-ok (503 at the route) when either store is down.
    """
    vector_backend = normalize_storage_backend(
        settings.vector_store_backend or settings.storage_backend
    )
    run_state_backend = normalize_storage_backend(settings.storage_backend or "mongodb")

    vector_probe = _probe_store(vector_backend)
    run_state_probe = (
        vector_probe
        if is_same_adapter(vector_backend, run_state_backend)
        else _probe_store(run_state_backend)
    )

    body: dict[str, object] = {
        "ok": bool(vector_probe["ok"]) and bool(run_state_probe["ok"]),
        "storage_backend": run_state_backend,
        "storage_mode": vector_probe["mode"],
        str(run_state_probe["_legacy_key"]): run_state_probe["_legacy_status"],
    }
    if "remediation" in run_state_probe:
        body["remediation"] = run_state_probe["remediation"]
        logger.warning("%s storage_mode=%s", run_state_probe["remediation"], body["storage_mode"])

    body["vector_store_backend"] = vector_backend
    body["run_state_mode"] = run_state_probe["mode"]
    body["stores"] = {
        "vector": _public_probe(vector_probe),
        "run_state": _public_probe(run_state_probe),
    }
    return body
