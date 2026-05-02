import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from server.db.indexes import ensure_indexes
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
    logger.info("Server ready")
    yield
    logger.info("Server shutting down...")


app = FastAPI(
    title="RAG Params Finder",
    description="Parameter sweep experimentation for RAG pipelines",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return {"ok": True}


from server.api import experiments, runs

app.include_router(experiments.router, prefix="/experiments", tags=["experiments"])
app.include_router(runs.router, prefix="/runs", tags=["runs"])
