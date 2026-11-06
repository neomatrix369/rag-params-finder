import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from server.api import experiments, runs
from server.api.explore_multi import router as explore_multi_router
from server.api.stores import router as stores_router
from server.api.sweep import router as sweep_router
from server.core.health_check import storage_health
from server.core.pipeline.executors import shutdown_executors
from server.core.pipeline.startup_reconciliation import reconcile_orphaned_experiments
from server.core.sie_guard import check_sie_health
from server.db.mongo.indexes import bootstrap_indexes
from server.db.ports.registry import resolve_adapter
from server.settings import LOCALHOST_CORS_ORIGIN_REGEX, normalize_storage_backend, settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def enforce_run_state_db_present() -> None:
    """Fail closed when RUN_STATE_DB_MUST_EXIST is set but the DB is missing.

    Slice 65B duplicate-prevention guard: opt-in via ``RUN_STATE_DB_MUST_EXIST``
    (set by ``start-services.sh`` after first-run init). When armed and the
    SQLite run-state file does not exist, raise ``SystemExit(1)`` rather than let
    a later store access silently create a second empty DB. No-op when the flag
    is off, the file already exists, or the run-state backend is not SQLite.
    """
    if normalize_storage_backend(settings.storage_backend) != "sqlite":
        return
    if not settings.run_state_db_must_exist:
        return
    db_path = Path(settings.sqlite_db_path)
    if db_path.exists():
        return
    logger.error(
        "boot — RUN_STATE_DB_MUST_EXIST is set but the run-state DB is missing "
        "at %s; refusing to create a second DB file. Run the initializer "
        "(start-services.sh / merge) so the canonical file exists first.",
        db_path,
    )
    raise SystemExit(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure indexes exist on startup."""
    logger.info("boot — server starting")
    settings.ensure_storage_ready()
    # Atlas search indexes are a Mongo concern, and Mongo only owns them when
    # it is the *vector* store (Slice 49B, site 7) — a split setup
    # (VECTOR_STORE_BACKEND=elasticsearch, STORAGE_BACKEND=mongodb) must not
    # bootstrap an unused `chunks` search index that nothing ever reads.
    # Postgres applies schema.sql (including HNSW) when its pool opens —
    # reaching for Mongo here would fail a --postgres-local / --postgres-cloud
    # stack that has no MONGODB_URI and no Atlas Local container.
    _backend = normalize_storage_backend(settings.vector_store_backend or settings.storage_backend)
    try:
        _is_mongodb = resolve_adapter(_backend) is resolve_adapter("mongodb")
    except ValueError:
        _is_mongodb = False
    if _is_mongodb:
        try:
            bootstrap_indexes()
        except Exception as e:
            logger.warning(
                "boot — index check failed (starting without indexes): %s", e, exc_info=True
            )
    else:
        logger.info(
            "boot — skipping Atlas index bootstrap (storage_backend=%s)",
            settings.storage_backend,
        )
    # Slice 55: warn when SQLite is new/empty but an older backend still has data.
    _run_state = normalize_storage_backend(settings.storage_backend)
    if _run_state == "sqlite":
        _sqlite_path = Path(settings.sqlite_db_path)
        # Slice 65B opt-in guard: fail closed instead of creating a second DB.
        enforce_run_state_db_present()
        # Slice 65B boot log: resolved path, inode, journal mode, sizes,
        # quick_check and counts — one visible record that every component
        # reads and writes the same file. prime_boot_diagnostics runs the slow
        # scans (quick_check + counts) once here and caches them so /healthz
        # reports them cheaply instead of re-scanning the ~600MB DB per call (B1).
        from server.db.sqlite.sqlite_diagnostics import prime_boot_diagnostics

        logger.info(
            "boot — run-state sqlite diagnostics: %s",
            prime_boot_diagnostics(settings.sqlite_db_path),
        )
        _sqlite_is_new = not _sqlite_path.exists() or _sqlite_path.stat().st_size == 0
        _has_source = bool(settings.mongodb_uri.strip()) or bool(settings.database_url.strip())
        if _sqlite_is_new and _has_source:
            logger.warning(
                "boot — SQLite run-state file is new/empty but "
                "MONGODB_ATLAS_CLOUD_URI / MONGODB_ATLAS_LOCAL_URI or "
                "POSTGRES_CLOUD_URL / POSTGRES_LOCAL_URL is configured. "
                "Existing experiments in MongoDB/Postgres are not visible "
                "until their run-state data has been copied into the SQLite file."
            )

    # Warn (non-fatal) when the vector store is Elasticsearch and the cluster
    # is not reachable — lazy init means the first experiment submit would fail
    # mid-pipeline without this early signal.
    _vs_backend = normalize_storage_backend(
        settings.vector_store_backend or settings.storage_backend
    )
    try:
        _is_elasticsearch = resolve_adapter(_vs_backend) is resolve_adapter("elasticsearch")
    except ValueError:
        _is_elasticsearch = False
    if _is_elasticsearch:
        try:
            from server.db.ports.store_factory import get_vector_store

            _es_store = get_vector_store()
            if not _es_store.health_check():
                logger.warning(
                    "boot — Elasticsearch unreachable at %s; "
                    "sweep submissions will fail until the cluster is reachable.",
                    settings.elasticsearch_url,
                )
            else:
                logger.info("boot — Elasticsearch reachable at %s", settings.elasticsearch_url)
        except Exception as _es_boot_exc:
            logger.warning(
                "boot — Elasticsearch connectivity check failed: %s "
                "(server starts but sweep submissions may fail)",
                _es_boot_exc,
            )

    # Probe the embedding cache backend — fail-closed when EMBEDDING_CACHE_BACKEND=redis
    # and the service is unreachable (GWT: "process exits non-zero").
    settings.ensure_cache_backend_ready()
    if settings.embedding_cache_backend.strip().lower() != "sqlite":
        from server.core.embedding.embedding_cache import get_cache_backend

        try:
            get_cache_backend()
            logger.info("boot — embedding cache backend=%s ready", settings.embedding_cache_backend)
        except Exception as _cache_exc:
            logger.error("boot — embedding cache backend unreachable: %s", _cache_exc)
            raise SystemExit(1) from _cache_exc

    try:
        reconcile_orphaned_experiments()
    except Exception as e:
        logger.error("boot — orphan reconciliation failed: %s", e, exc_info=True)
    if settings.recover_on_boot:
        logger.info(
            "boot — RECOVER_ON_BOOT enabled; automatic retry not implemented "
            "(see docs/plan/slices/01-core-pipeline/SLICE-10-RUN-RECOVERY.md)"
        )

    # Start the DoubleWord watcher (if DOUBLEWORD_API_KEY is set)
    from server.core.pipeline.doubleword_watcher import start_watcher

    start_watcher()

    logger.info("boot OK — server ready")
    yield
    logger.info("shutdown — server stopping")
    _run_shutdown()


def _run_shutdown() -> None:
    """Shutdown sequence — the WAL checkpoint must run even if teardown raises.

    Slice 65B (S1): a raised exception from ``stop_watcher`` or
    ``shutdown_executors`` must not skip the ``wal_checkpoint(TRUNCATE)``, or the
    single run-state DB keeps a dangling ``-wal`` after SIGTERM. The checkpoint
    therefore runs in a ``finally`` and is a no-op for non-SQLite run-state
    backends (compose ``stop_grace_period: 30s`` gives it time to complete).
    """
    from server.core.pipeline.doubleword_watcher import stop_watcher

    try:
        stop_watcher()
        shutdown_executors()
    finally:
        if normalize_storage_backend(settings.storage_backend) == "sqlite":
            from server.db.sqlite.sqlite_diagnostics import checkpoint_truncate

            checkpoint_truncate(settings.sqlite_db_path)


app = FastAPI(
    title="RAG Params Finder",
    description="Parameter sweep experimentation for RAG pipelines",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — cors_origins (CORS_ORIGINS) plus optional localhost loopback regex for any dev port.
if settings.cors_allow_localhost_origin_regex:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_origin_regex=LOCALHOST_CORS_ORIGIN_REGEX,
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unexpected API errors with request context (HTTPException uses FastAPI default)."""
    logger.error(
        "HTTP error — unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/healthz")
async def healthz():
    """Liveness for the active storage backend (Mongo or Postgres).

    Docker Compose HEALTHCHECK depends on HTTP 200 here. Probing the wrong
    backend (Mongo while running on pgvector) would mark a working stack unhealthy.

    ``storage_health`` does blocking work (store pings; run-state file stat), so
    it runs in a threadpool rather than on the event loop — a slow probe must not
    block the API or the 10s Docker healthcheck (B1).
    """
    body = await run_in_threadpool(storage_health)
    if not body["ok"]:
        return JSONResponse(status_code=503, content=body)
    return body


def _get_version() -> str:
    try:
        from importlib.metadata import version

        return version("rag-params-finder")
    except Exception:
        return "unknown"


@app.get("/health")
async def health():
    """Health check including SIE reachability and the active storage backend."""
    storage = storage_health()
    sie = check_sie_health()
    return {
        "status": "ok" if storage["ok"] else "degraded",
        "sie": sie,
        "version": _get_version(),
        **storage,
    }


app.include_router(experiments.router, prefix="/experiments", tags=["experiments"])
app.include_router(runs.router, prefix="/runs", tags=["runs"])
app.include_router(stores_router, prefix="/api", tags=["stores"])
app.include_router(sweep_router, prefix="/api/v1", tags=["sweep"])
app.include_router(explore_multi_router, prefix="/api/v1", tags=["explore-multi"])
