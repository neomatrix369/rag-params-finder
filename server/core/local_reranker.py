"""Local reranking via sentence-transformers CrossEncoder (no API key, no rate limits).

Uses cross-encoder/ms-marco-MiniLM-L-6-v2 by default (~23MB, MS MARCO trained).
Downloaded from HuggingFace on first use and cached locally.
"""

from __future__ import annotations

from sentence_transformers import CrossEncoder

from server.core.model_registry import get_reranker_info
from server.models.results import SearchResult
from server.utils.logger import get_logger

logger = get_logger(__name__)

_models: dict[str, CrossEncoder] = {}


def _get_model(model_id: str) -> CrossEncoder:
    if model_id not in _models:
        info = get_reranker_info(model_id)
        hf_id = info["huggingface_id"] or model_id
        logger.info(f"Loading local reranker model: {hf_id}")
        _models[model_id] = CrossEncoder(hf_id)
        logger.info(f"Local reranker model loaded: {hf_id}")
    return _models[model_id]


def rerank_local(
    query: str,
    search_results: list[SearchResult],
    model_id: str,
    top_k: int,
) -> list[SearchResult]:
    """Rerank search results using a local CrossEncoder and return top_k."""
    if not search_results:
        return []

    logger.debug(f"Reranking {len(search_results)} results locally with {model_id}, top_k={top_k}")

    model = _get_model(model_id)
    pairs = [(query, r.chunk.text) for r in search_results]
    scores = model.predict(pairs)

    scored_indices = sorted(
        enumerate(scores),
        key=lambda x: float(x[1]),
        reverse=True,
    )[:top_k]

    reranked: list[SearchResult] = []
    for rank, (orig_idx, score) in enumerate(scored_indices, start=1):
        original = search_results[orig_idx]
        reranked.append(
            original.model_copy(
                update={
                    "rerank_score": float(score),
                    "rank": rank,
                }
            )
        )

    logger.debug(f"Local reranking complete: {len(reranked)} results returned")
    return reranked
