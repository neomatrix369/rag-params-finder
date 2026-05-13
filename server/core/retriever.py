from server.core.model_registry import get_index_name_for_dimensions
from server.db.atlas import CHUNKS_COLLECTION, get_collection
from server.db.indexes import TEXT_SEARCH_INDEX_NAME, ensure_vector_index
from server.models.enums import RetrievalMethod
from server.models.results import Chunk, SearchResult
from server.utils.logger import get_logger

logger = get_logger(__name__)
_RRF_K = 60  # Reciprocal Rank Fusion constant — higher value smooths rank differences
_CANDIDATES_MULTIPLIER = 2  # numCandidates = top_k * multiplier for Atlas $vectorSearch


def _run_search_aggregate(
    pipeline: list,
    *,
    search_kind: str,
    experiment_id: str,
    embedding_model: str,
    index_name: str,
) -> list:
    """Run Atlas search aggregation; log context before re-raising on failure."""
    chunks_collection = get_collection(CHUNKS_COLLECTION)
    try:
        return list(chunks_collection.aggregate(pipeline))
    except Exception:
        logger.error(
            "%s search failed — experiment=%s model=%s index=%s",
            search_kind.lower(),
            experiment_id,
            embedding_model,
            index_name,
            exc_info=True,
        )
        raise


def dense_search(
    query_embedding: list[float], experiment_id: str, embedding_model: str, top_k: int = 20
) -> list[SearchResult]:
    """Perform dense vector search using Atlas $vectorSearch."""

    dimensions = len(query_embedding)
    index_name = get_index_name_for_dimensions(dimensions)
    ensure_vector_index(dimensions)
    logger.debug(
        "dense search start — experiment=%s model=%s index=%s k=%s",
        experiment_id,
        embedding_model,
        index_name,
        top_k,
    )

    pipeline = [
        {
            "$vectorSearch": {
                "index": index_name,
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": top_k * _CANDIDATES_MULTIPLIER,
                "limit": top_k,
                "filter": {
                    "experiment_id": {"$eq": experiment_id},
                    "embedding_model": {"$eq": embedding_model},
                },
            }
        },
        {
            "$project": {
                "_id": 0,
                "chunk_id": 1,
                "text": 1,
                "index": 1,
                "embedding_model": 1,
                "chunk_method": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    results = _run_search_aggregate(
        pipeline,
        search_kind="Dense",
        experiment_id=experiment_id,
        embedding_model=embedding_model,
        index_name=index_name,
    )
    logger.debug("dense search OK — %s hits", len(results))

    return _to_search_results(results, retrieval_method="dense")


def sparse_search(
    query_text: str, experiment_id: str, embedding_model: str, top_k: int = 20
) -> list[SearchResult]:
    """BM25 full-text search using Atlas Search ($search).

    Requires a 'text_search_index' Atlas Search index on the chunks collection
    with field mappings for 'text' (string), 'experiment_id' (token), and
    'embedding_model' (token).  See CLAUDE.local.md for index creation steps.
    """
    logger.debug(
        "sparse search start — experiment=%s model=%s k=%s",
        experiment_id,
        embedding_model,
        top_k,
    )

    pipeline = [
        {
            "$search": {
                "index": TEXT_SEARCH_INDEX_NAME,
                "compound": {
                    "must": [{"text": {"query": query_text, "path": "text"}}],
                    "filter": [
                        {"equals": {"path": "experiment_id", "value": experiment_id}},
                        {"equals": {"path": "embedding_model", "value": embedding_model}},
                    ],
                },
            }
        },
        {"$limit": top_k},
        {
            "$project": {
                "_id": 0,
                "chunk_id": 1,
                "text": 1,
                "index": 1,
                "embedding_model": 1,
                "chunk_method": 1,
                "score": {"$meta": "searchScore"},
            }
        },
    ]

    results = _run_search_aggregate(
        pipeline,
        search_kind="Sparse",
        experiment_id=experiment_id,
        embedding_model=embedding_model,
        index_name=TEXT_SEARCH_INDEX_NAME,
    )
    logger.debug("sparse search OK — %s hits", len(results))

    return _to_search_results(results, retrieval_method="sparse")


def hybrid_search(
    query_text: str,
    query_embedding: list[float],
    experiment_id: str,
    embedding_model: str,
    top_k: int = 20,
) -> list[SearchResult]:
    """Reciprocal Rank Fusion (RRF) merge of dense + sparse results.

    Runs both searches independently (each fetching top_k candidates) then
    merges with RRF: score = sum(1 / (rank + k)) across both ranked lists.
    k=60 is the standard default from the original RRF paper; it softens the
    advantage of rank-1 results and reduces sensitivity to outliers.
    """
    logger.debug(
        "hybrid search start — experiment=%s model=%s k=%s",
        experiment_id,
        embedding_model,
        top_k,
    )

    dense_results = dense_search(query_embedding, experiment_id, embedding_model, top_k)
    sparse_results = sparse_search(query_text, experiment_id, embedding_model, top_k)

    rrf_scores: dict[str, float] = {}
    chunk_by_id: dict[str, SearchResult] = {}

    for rank, result in enumerate(dense_results, start=1):
        cid = result.chunk.id
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (rank + _RRF_K)
        chunk_by_id[cid] = result

    for rank, result in enumerate(sparse_results, start=1):
        cid = result.chunk.id
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (rank + _RRF_K)
        chunk_by_id[cid] = result

    ranked_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)[:top_k]

    merged: list[SearchResult] = []
    for final_rank, cid in enumerate(ranked_ids, start=1):
        base = chunk_by_id[cid]
        merged.append(
            SearchResult(
                chunk=base.chunk,
                dense_score=rrf_scores[cid],
                rerank_score=None,
                retrieval_method="hybrid",
                rank=final_rank,
            )
        )

    logger.debug("hybrid search OK — %s hits after RRF", len(merged))
    return merged


def search(
    method: RetrievalMethod,
    query_text: str,
    experiment_id: str,
    embedding_model: str,
    top_k: int = 20,
    query_embedding: list[float] | None = None,
) -> list[SearchResult]:
    """Dispatcher: route to dense, sparse, or hybrid search."""
    if method == RetrievalMethod.DENSE:
        if query_embedding is None:
            raise ValueError("query_embedding is required for dense search")
        return dense_search(query_embedding, experiment_id, embedding_model, top_k)

    if method == RetrievalMethod.SPARSE:
        return sparse_search(query_text, experiment_id, embedding_model, top_k)

    if method == RetrievalMethod.HYBRID:
        if query_embedding is None:
            raise ValueError("query_embedding is required for hybrid search")
        return hybrid_search(query_text, query_embedding, experiment_id, embedding_model, top_k)

    raise ValueError(f"Unknown retrieval method: {method}")


def _to_search_results(docs: list[dict], retrieval_method: str) -> list[SearchResult]:
    results: list[SearchResult] = []
    for rank, doc in enumerate(docs, start=1):
        chunk = Chunk(
            id=doc["chunk_id"],
            text=doc["text"],
            index=doc["index"],
            embedding_model=doc["embedding_model"],
            chunk_method=doc["chunk_method"],
        )
        results.append(
            SearchResult(
                chunk=chunk,
                dense_score=doc["score"],
                rerank_score=None,
                retrieval_method=retrieval_method,
                rank=rank,
            )
        )
    return results
