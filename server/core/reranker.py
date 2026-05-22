from server.core.embedder import get_client, get_limiter
from server.core.rate_limiter import call_with_retry, estimate_tokens
from server.models.results import SearchResult
from server.utils.logger import get_logger

logger = get_logger(__name__)


def rerank_results(
    query: str,
    search_results: list[SearchResult],
    model: str,
    top_k: int,
    provider: str = "local",
) -> list[SearchResult]:
    """Rerank search results, dispatching to local or Voyage based on provider."""
    if not search_results:
        return []

    if provider == "local":
        from server.core.local_reranker import rerank_local

        return rerank_local(query, search_results, model, top_k)
    return _rerank_voyage(query, search_results, model, top_k)


def _rerank_voyage(
    query: str,
    search_results: list[SearchResult],
    model: str,
    top_k: int,
) -> list[SearchResult]:
    """Rerank search results using Voyage reranker and return top_k."""
    logger.debug(f"Reranking {len(search_results)} results with {model}, top_k={top_k}")

    client = get_client()
    documents = [r.chunk.text for r in search_results]

    tokens = estimate_tokens([query] + documents)
    rerank_response = call_with_retry(
        lambda: client.rerank(query, documents, model=model, top_k=top_k),
        limiter=get_limiter(),
        estimated_tokens=tokens,
        operation=f"Voyage rerank model={model} docs={len(documents)} top_k={top_k}",
    )

    reranked: list[SearchResult] = []
    for rank, hit in enumerate(rerank_response.results, start=1):
        original = search_results[hit.index]
        reranked.append(
            original.model_copy(
                update={
                    "rerank_score": hit.relevance_score,
                    "rank": rank,
                }
            )
        )

    logger.debug(f"Reranking complete: {len(reranked)} results returned")
    return reranked
