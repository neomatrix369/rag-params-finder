import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from server.api import experiments, runs
from server.api.sweep import router as sweep_router
from server.core.executors import shutdown_executors
from server.core.health_check import storage_health
from server.core.sie_guard import check_sie_health
from server.core.startup_reconciliation import reconcile_orphaned_experiments
from server.db.indexes import bootstrap_indexes
from server.settings import LOCALHOST_CORS_ORIGIN_REGEX, normalize_storage_backend, settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure indexes exist on startup."""
    logger.info("boot — server starting")
    settings.ensure_storage_ready()
    # Atlas search indexes are a Mongo concern. Postgres applies schema.sql
    # (including HNSW) when its pool opens — reaching for Mongo here would fail
    # a --postgres stack that has no MONGODB_URI / no Atlas Local container.
    if normalize_storage_backend(settings.storage_backend) == "mongodb":
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
    try:
        reconcile_orphaned_experiments()
    except Exception as e:
        logger.error("boot — orphan reconciliation failed: %s", e, exc_info=True)
    if settings.recover_on_boot:
        logger.info(
            "boot — RECOVER_ON_BOOT enabled; automatic retry not implemented "
            "(see docs/plan/slices/SLICE-10-RUN-RECOVERY.md)"
        )
    logger.info("boot OK — server ready")
    yield
    logger.info("shutdown — server stopping")
    shutdown_executors()


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
    """
    body = storage_health()
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
app.include_router(sweep_router, prefix="/api/v1", tags=["sweep"])
