from server.core.embedder import get_client
from server.models.results import SearchResult
from server.utils.logger import get_logger

logger = get_logger(__name__)


def rerank_results(
    query: str,
    search_results: list[SearchResult],
    model: str,
    top_k: int,
) -> list[SearchResult]:
    """Rerank search results using Voyage reranker and return top_k."""
    if not search_results:
        return []

    logger.info(f"Reranking {len(search_results)} results with {model}, top_k={top_k}")

    client = get_client()
    documents = [r.chunk.text for r in search_results]

    rerank_response = client.rerank(query, documents, model=model, top_k=top_k)

    reranked: list[SearchResult] = []
    for rank, hit in enumerate(rerank_response.results, start=1):
        original = search_results[hit.index]
        reranked.append(
            original.model_copy(update={
                "rerank_score": hit.relevance_score,
                "rank": rank,
            })
        )

    logger.info(f"Reranking complete: {len(reranked)} results returned")
    return reranked
