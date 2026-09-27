"""Shared retrieval constants and client-side Reciprocal Rank Fusion.

Mongo hybrid search and the Elasticsearch adapter both fuse ranked lists here.
Postgres keeps fusing in SQL and imports only ``RRF_K`` and
``CANDIDATES_MULTIPLIER`` so the three backends cannot drift apart.

Elasticsearch cosine ``_score`` is already ``(1 + cosine) / 2`` (the same
scale Atlas ``$vectorSearch`` returns). ``cosine_to_unit_score`` is that
formula, used to assert parity — callers do not apply it a second time to an
engine score that is already on this scale.
"""

from __future__ import annotations

from server.models.results import SearchResult

RRF_K = 60
CANDIDATES_MULTIPLIER = 2


def cosine_to_unit_score(cosine: float) -> float:
    """Map raw cosine similarity in [-1, 1] onto the shared 0..1 score scale."""
    return (1.0 + cosine) / 2.0


def rrf_fuse(
    dense_results: list[SearchResult],
    sparse_results: list[SearchResult],
    *,
    top_k: int,
    k: int = RRF_K,
) -> list[SearchResult]:
    """Fuse two ranked lists with RRF: ``score = sum(1 / (rank + k))``.

    Rank is 1-based. The fused ``dense_score`` is the RRF score (the same
    field Mongo hybrid search stored before this helper was extracted).
    Ties keep the first-seen chunk (dense list, then sparse-only).
    """
    rrf_scores: dict[str, float] = {}
    chunk_by_id: dict[str, SearchResult] = {}
    _accumulate(rrf_scores, chunk_by_id, dense_results, k)
    _accumulate(rrf_scores, chunk_by_id, sparse_results, k)
    ranked_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)[:top_k]
    return [
        _fused_hit(chunk_by_id[cid], rrf_scores[cid], rank)
        for rank, cid in enumerate(ranked_ids, start=1)
    ]


def _accumulate(
    rrf_scores: dict[str, float],
    chunk_by_id: dict[str, SearchResult],
    results: list[SearchResult],
    k: int,
) -> None:
    for rank, result in enumerate(results, start=1):
        cid = result.chunk.id
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (rank + k)
        chunk_by_id[cid] = result


def _fused_hit(base: SearchResult, score: float, rank: int) -> SearchResult:
    return SearchResult(
        chunk=base.chunk,
        dense_score=score,
        rerank_score=None,
        retrieval_method="hybrid",
        rank=rank,
    )
