from typing import cast

import voyageai
from voyageai.object import EmbeddingsObject

from server.core.rate_limiter import RateLimiter, call_with_retry, estimate_tokens
from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

_client: voyageai.Client | None = None
_limiter: RateLimiter | None = None


def get_client() -> voyageai.Client:
    """Get Voyage AI client singleton."""
    global _client
    if _client is None:
        if not settings.voyage_api_key:
            raise ValueError("VOYAGE_API_KEY not set in .env or environment")
        _client = voyageai.Client(api_key=settings.voyage_api_key)
        logger.info("Voyage AI client initialized")
    return _client


def get_limiter() -> RateLimiter:
    """Get shared Voyage AI rate limiter singleton."""
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter(
            rpm=settings.voyage_rpm_limit,
            tpm=settings.voyage_tpm_limit,
        )
        logger.info(
            f"Rate limiter initialized: {settings.voyage_rpm_limit} RPM, "
            f"{settings.voyage_tpm_limit} TPM"
        )
    return _limiter


def _token_budget_per_request() -> int:
    """Max tokens we try to fit into a single embed call to stay within TPM."""
    limiter = get_limiter()
    return limiter._tpm if limiter._tpm > 0 else 100_000


def embed_documents(texts: list[str], model: str, provider: str = "local") -> list[list[float]]:
    """Embed documents, dispatching to the configured provider."""
    if provider == "local":
        from server.core.local_embedder import embed_documents_local

        return embed_documents_local(texts, model)
    if provider == "voyage":
        return _embed_documents_voyage(texts, model)
    if provider == "kimchi":
        from server.core.kimchi_embedder import embed_documents_kimchi

        return embed_documents_kimchi(texts, model)
    raise ValueError(f"Unsupported embedding provider '{provider}'")


def embed_query(text: str, model: str, provider: str = "local") -> list[float]:
    """Embed a single query, dispatching to the configured provider."""
    if provider == "local":
        from server.core.local_embedder import embed_query_local

        return embed_query_local(text, model)
    if provider == "voyage":
        return _embed_query_voyage(text, model)
    if provider == "kimchi":
        from server.core.kimchi_embedder import embed_query_kimchi

        return embed_query_kimchi(text, model)
    raise ValueError(f"Unsupported embedding provider '{provider}'")


def _embed_documents_voyage(texts: list[str], model: str) -> list[list[float]]:
    """Embed documents using Voyage AI, auto-batching to respect rate limits."""
    logger.info(f"Embedding {len(texts)} documents with model={model}")

    client = get_client()
    budget = _token_budget_per_request()

    batches = _split_into_batches(texts, budget)
    if len(batches) > 1:
        logger.info(f"Split {len(texts)} texts into {len(batches)} batches for rate limiting")

    all_embeddings: list[list[float]] = []
    for idx, batch in enumerate(batches):
        tokens = estimate_tokens(batch)
        logger.debug(f"Batch {idx + 1}/{len(batches)}: {len(batch)} texts, ~{tokens} tokens")

        def _embed_batch() -> EmbeddingsObject:
            return client.embed(batch, model=model, input_type="document")

        result = call_with_retry(_embed_batch, limiter=get_limiter(), estimated_tokens=tokens)
        all_embeddings.extend(cast(list[list[float]], result.embeddings))

    logger.info(f"Generated {len(all_embeddings)} embeddings, dim={len(all_embeddings[0])}")
    return all_embeddings


def _embed_query_voyage(text: str, model: str) -> list[float]:
    """Embed a single query using Voyage AI."""
    logger.info(f"Embedding query with model={model}")

    client = get_client()
    tokens = estimate_tokens([text])
    result = call_with_retry(
        lambda: client.embed([text], model=model, input_type="query"),
        limiter=get_limiter(),
        estimated_tokens=tokens,
    )

    embedding = cast(list[float], result.embeddings[0])
    logger.info(f"Generated query embedding, dim={len(embedding)}")
    return embedding


def _split_into_batches(texts: list[str], token_budget: int) -> list[list[str]]:
    """Split texts into batches that each fit within the token budget."""
    batches: list[list[str]] = []
    current_batch: list[str] = []
    current_tokens = 0

    for text in texts:
        text_tokens = estimate_tokens([text])
        if current_batch and current_tokens + text_tokens > token_budget:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0
        current_batch.append(text)
        current_tokens += text_tokens

    if current_batch:
        batches.append(current_batch)
    return batches
