"""Dense kNN, BM25, and client-side RRF hybrid search over one chunks index.

Dense ``_score`` is Elasticsearch cosine similarity, already
``(1 + cosine) / 2``, comparable with Mongo and Postgres dense scores.
BM25 sparse scores are unbounded and NOT comparable across stores.
"""

from __future__ import annotations

from typing import Any

from server.core.retrieval.fusion import CANDIDATES_MULTIPLIER, rrf_fuse
from server.db.elasticsearch.mapping import field_for_dims
from server.models.enums import RetrievalMethod
from server.models.results import Chunk, SearchResult


def require_top_k(top_k: int) -> None:
    """Reject non-positive ``top_k`` before any network call."""
    if top_k <= 0:
        raise ValueError(f"top_k must be greater than 0 (got {top_k})")


def require_embedding_model(embedding_model: str) -> None:
    if not embedding_model:
        raise ValueError(
            "embedding_model is required — chunks from different models share one index "
            "and must never be compared"
        )


def term_filters(experiment_id: str, embedding_model: str, run_id: str) -> list[dict[str, Any]]:
    """Mandatory isolation filters: embedding_model, experiment_id, run_id."""
    require_embedding_model(embedding_model)
    return [
        {"term": {"experiment_id": experiment_id}},
        {"term": {"embedding_model": embedding_model}},
        {"term": {"run_id": run_id}},
    ]


def hits_to_results(response: dict[str, Any], retrieval_method: str) -> list[SearchResult]:
    hits = (response.get("hits") or {}).get("hits") or []
    return [_hit_to_result(hit, retrieval_method, rank) for rank, hit in enumerate(hits, start=1)]


def dense_search(
    client: Any,
    *,
    index: str,
    query_embedding: list[float],
    experiment_id: str,
    embedding_model: str,
    run_id: str,
    top_k: int,
) -> list[SearchResult]:
    """kNN with filters inside ``knn.filter`` (pre-filter, not a post-filter)."""
    require_top_k(top_k)
    field = field_for_dims(len(query_embedding))
    num_candidates = min(top_k * CANDIDATES_MULTIPLIER, 10_000)
    response = client.search(
        index=index,
        knn={
            "field": field,
            "query_vector": list(query_embedding),
            "k": top_k,
            "num_candidates": num_candidates,
            "filter": {"bool": {"filter": term_filters(experiment_id, embedding_model, run_id)}},
        },
        size=top_k,
    )
    return hits_to_results(response, RetrievalMethod.DENSE.value)


def sparse_search(
    client: Any,
    *,
    index: str,
    query_text: str,
    experiment_id: str,
    embedding_model: str,
    run_id: str,
    top_k: int,
) -> list[SearchResult]:
    """BM25 ``match`` on ``text``, with the same three filters."""
    require_top_k(top_k)
    response = client.search(
        index=index,
        query={
            "bool": {
                "must": [{"match": {"text": {"query": query_text}}}],
                "filter": term_filters(experiment_id, embedding_model, run_id),
            }
        },
        size=top_k,
    )
    return hits_to_results(response, RetrievalMethod.SPARSE.value)


def hybrid_search(
    client: Any,
    *,
    index: str,
    query_text: str,
    query_embedding: list[float],
    experiment_id: str,
    embedding_model: str,
    run_id: str,
    top_k: int,
) -> list[SearchResult]:
    """Client-side RRF (k=60). Server-side ``rrf`` retriever is Platinum — unused."""
    dense = dense_search(
        client,
        index=index,
        query_embedding=query_embedding,
        experiment_id=experiment_id,
        embedding_model=embedding_model,
        run_id=run_id,
        top_k=top_k,
    )
    sparse = sparse_search(
        client,
        index=index,
        query_text=query_text,
        experiment_id=experiment_id,
        embedding_model=embedding_model,
        run_id=run_id,
        top_k=top_k,
    )
    return rrf_fuse(dense, sparse, top_k=top_k)


def search(
    client: Any,
    *,
    index: str,
    method: RetrievalMethod,
    query_text: str,
    experiment_id: str,
    embedding_model: str,
    run_id: str,
    top_k: int,
    query_embedding: list[float] | None,
) -> list[SearchResult]:
    """Dispatch dense, sparse, or hybrid. Invalid ``top_k`` fails before I/O."""
    if method == RetrievalMethod.DENSE:
        if query_embedding is None:
            raise ValueError("query_embedding is required for dense search")
        return dense_search(
            client,
            index=index,
            query_embedding=query_embedding,
            experiment_id=experiment_id,
            embedding_model=embedding_model,
            run_id=run_id,
            top_k=top_k,
        )
    if method == RetrievalMethod.SPARSE:
        return sparse_search(
            client,
            index=index,
            query_text=query_text,
            experiment_id=experiment_id,
            embedding_model=embedding_model,
            run_id=run_id,
            top_k=top_k,
        )
    if method == RetrievalMethod.HYBRID:
        if query_embedding is None:
            raise ValueError("query_embedding is required for hybrid search")
        return hybrid_search(
            client,
            index=index,
            query_text=query_text,
            query_embedding=query_embedding,
            experiment_id=experiment_id,
            embedding_model=embedding_model,
            run_id=run_id,
            top_k=top_k,
        )
    raise ValueError(f"Unknown retrieval method: {method}")


def _hit_to_result(hit: dict[str, Any], retrieval_method: str, rank: int) -> SearchResult:
    source = hit.get("_source") or {}
    chunk_index = source.get("chunk_index", source.get("index", 0))
    return SearchResult(
        chunk=Chunk(
            id=str(source.get("chunk_id") or hit.get("_id") or ""),
            text=str(source.get("text") or ""),
            index=int(chunk_index),
            embedding_model=str(source.get("embedding_model") or ""),
            chunk_method=str(source.get("chunk_method") or ""),
        ),
        dense_score=float(hit.get("_score") or 0.0),
        rerank_score=None,
        retrieval_method=retrieval_method,
        rank=rank,
    )
