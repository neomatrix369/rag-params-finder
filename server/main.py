import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api import experiments, runs
from server.core.startup_reconciliation import reconcile_orphaned_experiments
from server.db.indexes import ensure_indexes
from server.settings import LOCALHOST_CORS_ORIGIN_REGEX, settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure indexes exist on startup."""
    logger.info("Server starting...")
    try:
        ensure_indexes()
    except Exception as e:
        logger.warning(f"Index check failed (server will start without indexes): {e}")
    try:
        reconcile_orphaned_experiments()
    except Exception as e:
        logger.error(f"Orphaned experiment reconciliation failed: {e}", exc_info=True)
    if settings.recover_on_boot:
        logger.info(
            "RECOVER_ON_BOOT is enabled; automatic retry of interrupted runs is not "
            "implemented yet (see docs/slices/SLICE-10-RUN-RECOVERY.md)"
        )
    logger.info("Server ready")
    yield
    logger.info("Server shutting down...")


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


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return {"ok": True}


app.include_router(experiments.router, prefix="/experiments", tags=["experiments"])
app.include_router(runs.router, prefix="/runs", tags=["runs"])
