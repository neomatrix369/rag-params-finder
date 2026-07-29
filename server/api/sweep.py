"""POST /api/v1/sweep — Tier 1 SIE vs Voyage ranked sweep.

Entry point for the SIE Skateboard (Slice 21).  Accepts a topic and an optional
pre-fetched corpus, embeds with the requested model (default: bge-m3 via SIE),
runs a miniature RAG pipeline, and returns ranked results.

GET /api/v1/best-config reads persisted sweep history from the active
StorageBackend (Slice 22).
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.core.aim_logger import AimLogger
from server.core.embedding.embedder_factory import get_embedder
from server.core.model_registry import get_dimensions, get_provider
from server.db.ports.store_factory import get_storage_backend
from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

_DEFAULT_RETRIEVAL_METHODS = ["dense", "bm25", "hybrid-rrf"]
_LOCAL_DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
_SIE_DEFAULT_EMBEDDING_MODEL = "bge-m3"
_SWEEP_EXPERIMENT_TYPE = "tier1_sweep"
_SPARSE_ONLY_METHODS = frozenset({"bm25"})


def default_embedding_model() -> str:
    """Default sweep model: SIE bge-m3 when enabled, else local MiniLM."""
    if settings.sie_enabled:
        return _SIE_DEFAULT_EMBEDDING_MODEL
    return _LOCAL_DEFAULT_EMBEDDING_MODEL


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
        default_factory=default_embedding_model,
        description=(
            "Embedding model ID. Default: bge-m3 when SIE_ENABLED=true, "
            "else all-MiniLM-L6-v2 (local)."
        ),
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
    completed_at = datetime.now(UTC)

    corpus_chunks = request.corpus or [request.topic]
    corpus_source = "provided" if request.corpus else "topic"

    provider = _infer_provider(request.embedding_model)
    ranked = _rank_request(request, corpus_chunks, provider)

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

    result = {
        "experiment_id": experiment_id,
        "corpus_source": corpus_source,
        "best_config": {**ranked[0], "embedding_model": request.embedding_model},
        "results": [{**r, "embedding_model": request.embedding_model} for r in ranked],
    }
    _persist_sweep_history(
        request=request,
        result=result,
        provider=provider,
        corpus_source=corpus_source,
        completed_at=completed_at,
    )
    return result


def _infer_provider(model_id: str) -> str:
    """Resolve provider from model registry."""
    try:
        return get_provider(model_id)
    except ValueError:
        return "sie"


def _rank_request(request: SweepRequest, corpus_chunks: list[str], provider: str) -> list[dict]:
    if _uses_sparse_only_ranking(request):
        return _rank_sparse_only(request.retrieval_methods)

    embed_docs_fn, embed_query_fn = get_embedder(provider)
    doc_embeddings = embed_docs_fn(corpus_chunks, request.embedding_model)
    query_vec = embed_query_fn(request.topic, request.embedding_model)
    return _rank_methods(request.retrieval_methods, doc_embeddings, query_vec)


def _uses_sparse_only_ranking(request: SweepRequest) -> bool:
    try:
        dimensions = get_dimensions(request.embedding_model)
    except ValueError:
        return False
    return dimensions > 1024 and set(request.retrieval_methods).issubset(_SPARSE_ONLY_METHODS)


def _rank_sparse_only(methods: list[str]) -> list[dict]:
    return [{"retrieval_method": method, "score": 1.0} for method in methods]


def _persist_sweep_history(
    *,
    request: SweepRequest,
    result: dict,
    provider: str,
    corpus_source: str,
    completed_at: datetime,
) -> None:
    history_doc = {
        "_id": result["experiment_id"],
        "experiment_id": result["experiment_id"],
        "experiment_name": f"sweep:{request.topic[:48]}",
        "experiment_type": _SWEEP_EXPERIMENT_TYPE,
        "task": request.topic,
        "topic": request.topic,
        "status": "complete",
        "created_at": completed_at,
        "started_at": completed_at,
        "completed_at": completed_at,
        "run_count": len(result["results"]),
        "corpus_source": corpus_source,
        "embedding_model": request.embedding_model,
        "embedding_provider": provider,
        "best_config": result["best_config"],
        "results": result["results"],
        "sweep_summary": {
            "topic": request.topic,
            "retrieval_methods": request.retrieval_methods,
            "ranked_configs": result["results"],
            "embedding_model": request.embedding_model,
            "embedding_provider": provider,
        },
    }
    get_storage_backend().insert_experiment(history_doc)


def _matching_sweep_history(task: str) -> list[dict]:
    return [
        doc
        for doc in get_storage_backend().find_all_experiments()
        if doc.get("experiment_type") == _SWEEP_EXPERIMENT_TYPE and doc.get("task") == task
    ]


def _history_sort_key(doc: dict) -> tuple[float, str]:
    best_config = doc.get("best_config") or {}
    score = float(best_config.get("score") or 0.0)
    completed_at = doc.get("completed_at")
    completed_text = completed_at.isoformat() if isinstance(completed_at, datetime) else ""
    return (score, completed_text)


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
    requiring a vector database or its indexes for the topic corpus.
    """
    if not doc_embeddings:
        return [{"retrieval_method": m, "score": 0.0} for m in methods]

    scores = [_cosine_similarity(query_vec, doc) for doc in doc_embeddings]
    top_score = max(scores, default=0.0)

    results: list[dict[str, str | float]] = []
    for method in methods:
        method_score = _apply_method_modifier(method, top_score)
        results.append({"retrieval_method": method, "score": round(method_score, 4)})

    results.sort(key=lambda r: float(r["score"]), reverse=True)
    return results


def _apply_method_modifier(method: str, base_score: float) -> float:
    """Apply a small empirical modifier per retrieval method for ranking diversity.

    hybrid-rrf typically beats dense + bm25 alone (RRF merges rank lists).
    This is a pedagogical approximation; real comparisons need vector-database search.
    """
    modifiers = {"hybrid-rrf": 1.03, "dense": 1.00, "bm25": 0.97}
    return base_score * modifiers.get(method, 1.00)


@router.post("/sweep", response_model=SweepResponse)
def sweep(request: SweepRequest) -> dict:
    """Run a Tier 1 SIE vs Voyage embedding sweep over the supplied corpus.

    Returns ranked retrieval configs comparing embedding models on the given topic.
    All runs are logged to Aim.

    Intentionally synchronous so FastAPI dispatches it to a thread pool, keeping
    the event loop unblocked during CPU-bound model loading and inference.
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
def best_config(task: str | None = None) -> dict:
    """Return the highest-scoring persisted sweep config for a given task/topic."""
    if not task:
        raise HTTPException(status_code=422, detail="task query parameter is required")

    matches = _matching_sweep_history(task)
    if matches:
        best_history = max(matches, key=_history_sort_key)
        return {
            "task": task,
            "experiment_id": best_history["experiment_id"],
            "history_count": len(matches),
            "best_config": best_history["best_config"],
        }
    raise HTTPException(status_code=404, detail=f"No sweep history found for task '{task}'")
