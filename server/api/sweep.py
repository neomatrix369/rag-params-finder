"""POST /api/v1/sweep — Tier 1 SIE vs Voyage ranked sweep.

Entry point for the SIE Skateboard (Slice 21).  Accepts a topic and an optional
pre-fetched corpus, embeds with the requested model (default: bge-m3 via SIE),
runs a miniature RAG pipeline, and returns ranked results.

GET /api/v1/best-config is a thin read from MongoDB sweep history (Slice 22 extension).
"""

from __future__ import annotations

import os
import time
import uuid

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

from server.core.aim_logger import AimLogger
from server.core.embedder_factory import get_embedder
from server.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

_DEFAULT_EMBEDDING_MODEL = "bge-m3"
_DEFAULT_RETRIEVAL_METHODS = ["dense", "bm25", "hybrid-rrf"]
_SIE_BASE_URL = os.getenv("SIE_BASE_URL", "http://localhost:8720")


class SweepRequest(BaseModel):
    topic: str = Field(..., description="Topic / query to embed and rank")
    corpus: list[str] = Field(
        default_factory=list,
        description=(
            "Pre-fetched corpus chunks to embed. "
            "When empty the topic itself is used as a single-chunk corpus."
        ),
    )
    embedding_model: str = Field(
        default=_DEFAULT_EMBEDDING_MODEL,
        description="SIE or Voyage model ID (default: bge-m3)",
    )
    retrieval_methods: list[str] = Field(
        default=_DEFAULT_RETRIEVAL_METHODS,
        description="Retrieval strategies to compare",
    )


class SweepResult(BaseModel):
    retrieval_method: str
    embedding_model: str
    score: float
    chunk_count: int = 0


class SweepResponse(BaseModel):
    experiment_id: str
    corpus_source: str
    best_config: dict
    results: list[dict]


def check_sie_health() -> str:
    """Probe SIE /healthz — returns 'reachable' or 'unreachable'."""
    try:
        resp = httpx.get(f"{_SIE_BASE_URL}/healthz", timeout=3.0)
        return "reachable" if resp.status_code == 200 else "unreachable"
    except Exception:
        return "unreachable"


def _run_sweep_internal(request: SweepRequest) -> dict:
    """Embed corpus chunks with the requested model and rank by naive coverage score.

    Lightweight Tier 1 pipeline:
      1. Resolve corpus (caller-supplied or fallback to topic string)
      2. Embed each chunk with the requested model
      3. Embed the topic query
      4. Rank retrieval methods by cosine similarity of top-1 result to query
    """
    experiment_id = str(uuid.uuid4())
    start = time.monotonic()

    corpus_chunks = request.corpus if request.corpus else [request.topic]
    corpus_source = "provided" if request.corpus else "topic"

    provider = _infer_provider(request.embedding_model)
    embed_docs_fn, embed_query_fn = get_embedder(provider)

    doc_embeddings = embed_docs_fn(corpus_chunks, request.embedding_model)
    query_vec = embed_query_fn(request.topic, request.embedding_model)

    ranked = _rank_methods(request.retrieval_methods, doc_embeddings, query_vec)

    latency_ms = int((time.monotonic() - start) * 1000)

    for rank_result in ranked:
        AimLogger.log_run(
            {
                "experiment_id": experiment_id,
                "model_name": request.embedding_model,
                "model_source": provider,
                "retrieval_method": rank_result["retrieval_method"],
                "score": rank_result["score"],
                "latency_ms": latency_ms,
                "topic": request.topic,
            }
        )

    return {
        "experiment_id": experiment_id,
        "corpus_source": corpus_source,
        "best_config": {**ranked[0], "embedding_model": request.embedding_model},
        "results": [{**r, "embedding_model": request.embedding_model} for r in ranked],
    }


def _infer_provider(model_id: str) -> str:
    """Resolve provider from model registry; default to 'sie' for unknown SIE models."""
    try:
        from server.core.model_registry import get_provider

        return get_provider(model_id)
    except ValueError:
        return "sie"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Dot product of two pre-normalised vectors (SIE and Voyage both normalise)."""
    if len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def _rank_methods(
    methods: list[str],
    doc_embeddings: list[list[float]],
    query_vec: list[float],
) -> list[dict]:
    """Rank retrieval methods by top-1 cosine similarity score.

    In a real Tier 2 sweep this would run actual vector DB queries.  For the
    skateboard, embedding similarity is used as a cheap proxy score so all the
    wiring (embed → rank → Aim log) can be validated end-to-end without
    requiring Atlas search indexes to be set up for the topic corpus.
    """
    if not doc_embeddings:
        return [{"retrieval_method": m, "score": 0.0} for m in methods]

    scores = [_cosine_similarity(query_vec, doc) for doc in doc_embeddings]
    top_score = max(scores) if scores else 0.0

    results: list[dict[str, str | float]] = []
    for method in methods:
        method_score = _apply_method_modifier(method, top_score)
        results.append({"retrieval_method": method, "score": round(method_score, 4)})

    results.sort(key=lambda r: float(r["score"]), reverse=True)
    return results


def _apply_method_modifier(method: str, base_score: float) -> float:
    """Apply a small empirical modifier per retrieval method for ranking diversity.

    hybrid-rrf typically beats dense + bm25 alone (RRF merges rank lists).
    This is a pedagogical approximation; real comparisons need Atlas vector search.
    """
    modifiers = {"hybrid-rrf": 1.03, "dense": 1.00, "bm25": 0.97}
    return base_score * modifiers.get(method, 1.00)


@router.post("/sweep", response_model=SweepResponse)
async def sweep(request: SweepRequest) -> dict:
    """Run a Tier 1 SIE vs Voyage embedding sweep over the supplied corpus.

    Returns ranked retrieval configs comparing embedding models on the given topic.
    All runs are logged to Aim.
    """
    logger.info("sweep request — topic=%r model=%s", request.topic, request.embedding_model)
    result = _run_sweep_internal(request)
    logger.info(
        "sweep done — experiment=%s best=%s score=%.3f",
        result["experiment_id"],
        result["best_config"].get("retrieval_method"),
        result["best_config"].get("score", 0),
    )
    return result


@router.get("/best-config")
async def best_config(task: str | None = None) -> dict:
    """Return the best RAG config from sweep history (placeholder for Slice 22).

    Queries MongoDB sweep history for the highest-scoring config for the given task.
    """
    return {
        "task": task,
        "message": "best-config history query is implemented in Slice 22 (SIE Scooter)",
        "best_config": None,
    }
