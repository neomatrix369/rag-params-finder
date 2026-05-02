from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from server.db.indexes import create_indexes
from server.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize indexes on startup."""
    logger.info("Server starting...")
    create_indexes()
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


# Import and include routers
from server.api import experiments

app.include_router(experiments.router, prefix="/experiments", tags=["experiments"])
