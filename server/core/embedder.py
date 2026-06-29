from collections.abc import Callable
from typing import cast

import tiktoken
import voyageai
from tiktoken.core import Encoding
from voyageai.object import EmbeddingsObject
from voyageai.object.contextualized_embeddings import ContextualizedEmbeddingsObject

from server.core.model_registry import is_contextualized_embedding
from server.core.rate_limiter import RateLimiter, call_with_retry, estimate_tokens
from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

# voyage-context-3 limits (https://docs.voyageai.com/docs/contextualized-chunk-embeddings)
VOYAGE_CONTEXT_WINDOW_TOKENS = 32_000
VOYAGE_CONTEXT_REQUEST_TOKEN_CAP = 120_000
VOYAGE_CONTEXT_MAX_INPUTS = 1_000
# Per-segment cap (tiktoken cl100k_base); leaves headroom vs Voyage's 32K window.
VOYAGE_CONTEXT_SEGMENT_BUDGET = 30_000

_tiktoken_encoding: Encoding | None = None

_client: voyageai.Client | None = None
_limiter: RateLimiter | None = None


def get_client() -> voyageai.Client:
    """Get Voyage AI client singleton."""
    global _client
    if _client is None:
        if not settings.voyage_api_key:
            raise ValueError("VOYAGE_API_KEY not set in .env or environment")
        _client = voyageai.Client(api_key=settings.voyage_api_key)
        logger.info("voyage client ready — singleton initialized")
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
            "voyage rate limiter ready — RPM=%s TPM=%s",
            settings.voyage_rpm_limit,
            settings.voyage_tpm_limit,
        )
    return _limiter


def _token_budget_per_request() -> int:
    """Max tokens we try to fit into a single embed call to stay within TPM."""
    limiter = get_limiter()
    return limiter._tpm if limiter._tpm > 0 else 100_000


def embed_documents_voyage(
    texts: list[str],
    model: str,
    *,
    cancel_check: Callable[[], None] | None = None,
) -> list[list[float]]:
    """Embed documents using Voyage AI — called via embedder_factory.get_embedder("voyage")."""
    if is_contextualized_embedding(model):
        return _embed_documents_voyage_context(texts, model, cancel_check=cancel_check)
    return _embed_documents_voyage(texts, model, cancel_check=cancel_check)


def embed_query_voyage(text: str, model: str) -> list[float]:
    """Embed a single query using Voyage AI — called via embedder_factory.get_embedder("voyage")."""
    if is_contextualized_embedding(model):
        return _embed_query_voyage_context(text, model)
    return _embed_query_voyage(text, model)


def _embed_documents_voyage(
    texts: list[str],
    model: str,
    *,
    cancel_check: Callable[[], None] | None = None,
) -> list[list[float]]:
    """Embed documents using Voyage AI, auto-batching to respect rate limits."""
    logger.info("embedding batch — %s documents model=%s", len(texts), model)

    client = get_client()
    budget = _token_budget_per_request()

    batches = _split_into_batches(texts, budget)
    if len(batches) > 1:
        logger.info(
            "embedding sharded — %s texts split into %s batches (rate limits)",
            len(texts),
            len(batches),
        )

    all_embeddings: list[list[float]] = []
    for idx, batch in enumerate(batches):
        if cancel_check is not None:
            cancel_check()
        tokens = estimate_tokens(batch)
        logger.debug(
            "embedding batch progress — batch %s/%s texts=%s est_tokens≈%s",
            idx + 1,
            len(batches),
            len(batch),
            tokens,
        )

        def _embed_batch() -> EmbeddingsObject:
            return client.embed(batch, model=model, input_type="document")

        result = call_with_retry(
            _embed_batch,
            limiter=get_limiter(),
            estimated_tokens=tokens,
            operation=f"Voyage embed batch {idx + 1}/{len(batches)} model={model}",
            cancel_check=cancel_check,
        )
        all_embeddings.extend(cast(list[list[float]], result.embeddings))

    logger.info("embed OK — count=%s dim=%s", len(all_embeddings), len(all_embeddings[0]))
    return all_embeddings


def _embed_documents_voyage_context(
    texts: list[str],
    model: str,
    *,
    cancel_check: Callable[[], None] | None = None,
) -> list[list[float]]:
    """Embed document chunks with voyage-context-3 (shared document context)."""
    if not texts:
        return []

    _validate_context_chunk_sizes(texts)
    logger.info("contextualized embed — %s chunks model=%s", len(texts), model)
    client = get_client()
    segments = _split_context_segments(texts)
    if len(segments) > 1:
        logger.info(
            "context segments — %s chunks → %s segments (%s-token window)",
            len(texts),
            len(segments),
            VOYAGE_CONTEXT_WINDOW_TOKENS,
        )

    all_embeddings: list[list[float]] = []
    for req_idx, request_segments in enumerate(_split_context_requests(segments)):
        if cancel_check is not None:
            cancel_check()
        flat = [chunk for segment in request_segments for chunk in segment]
        tokens = _count_context_tokens(flat)
        logger.debug(
            "contextualized batch — request %s segments=%s est_tokens≈%s",
            req_idx + 1,
            len(request_segments),
            tokens,
        )

        def _embed(batch: list[list[str]] = request_segments) -> ContextualizedEmbeddingsObject:
            return client.contextualized_embed(batch, model=model, input_type="document")

        result = call_with_retry(
            _embed,
            limiter=get_limiter(),
            estimated_tokens=tokens,
            operation=(
                f"Voyage contextualized embed request {req_idx + 1} "
                f"model={model} segments={len(request_segments)}"
            ),
            cancel_check=cancel_check,
        )
        for segment_result in result.results:
            all_embeddings.extend(cast(list[list[float]], segment_result.embeddings))

    logger.info(
        "context embed OK — count=%s dim=%s",
        len(all_embeddings),
        len(all_embeddings[0]),
    )
    return all_embeddings


def _embed_query_voyage_context(text: str, model: str) -> list[float]:
    """Embed a query with voyage-context-3."""
    logger.debug("context query embed — model=%s", model)
    client = get_client()
    tokens = estimate_tokens([text])

    def _embed() -> ContextualizedEmbeddingsObject:
        return client.contextualized_embed([[text]], model=model, input_type="query")

    result = call_with_retry(
        _embed,
        limiter=get_limiter(),
        estimated_tokens=tokens,
        operation=f"Voyage contextualized query embed model={model}",
    )
    embedding = cast(list[float], result.results[0].embeddings[0])
    logger.debug("context query OK — dim=%s", len(embedding))
    return embedding


def _embed_query_voyage(text: str, model: str) -> list[float]:
    """Embed a single query using Voyage AI."""
    logger.debug("query embed — model=%s", model)

    client = get_client()
    tokens = estimate_tokens([text])
    result = call_with_retry(
        lambda: client.embed([text], model=model, input_type="query"),
        limiter=get_limiter(),
        estimated_tokens=tokens,
        operation=f"Voyage query embed model={model}",
    )

    embedding = cast(list[float], result.embeddings[0])
    logger.debug("query embed OK — dim=%s", len(embedding))
    return embedding


def _get_tiktoken_encoding() -> Encoding:
    global _tiktoken_encoding
    if _tiktoken_encoding is None:
        _tiktoken_encoding = tiktoken.get_encoding("cl100k_base")
    return _tiktoken_encoding


def _count_context_tokens(texts: list[str]) -> int:
    """Count tokens with tiktoken (cl100k_base) for voyage-context-3 segment sizing."""
    encoding = _get_tiktoken_encoding()
    return max(1, sum(len(encoding.encode(text)) for text in texts))


def _validate_context_chunk_sizes(texts: list[str]) -> None:
    for index, text in enumerate(texts):
        tokens = _count_context_tokens([text])
        if tokens <= VOYAGE_CONTEXT_WINDOW_TOKENS:
            continue
        raise ValueError(
            f"Chunk {index} has ~{tokens} tokens, exceeding voyage-context-3's "
            f"{VOYAGE_CONTEXT_WINDOW_TOKENS}-token window (no truncation). "
            "Use a smaller chunk_size."
        )


def _split_into_batches(
    texts: list[str],
    token_budget: int,
    token_counter: Callable[[list[str]], int] | None = None,
) -> list[list[str]]:
    """Split texts into batches that each fit within the token budget."""
    count_tokens = token_counter or estimate_tokens
    batches: list[list[str]] = []
    current_batch: list[str] = []
    current_tokens = 0

    for text in texts:
        text_tokens = count_tokens([text])
        if current_batch and current_tokens + text_tokens > token_budget:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0
        current_batch.append(text)
        current_tokens += text_tokens

    if current_batch:
        batches.append(current_batch)
    return batches


def _split_context_segments(texts: list[str]) -> list[list[str]]:
    """Split document chunks into segments for voyage-context-3's per-input window."""
    return _split_into_batches(
        texts,
        VOYAGE_CONTEXT_SEGMENT_BUDGET,
        token_counter=_count_context_tokens,
    )


def _split_context_requests(segments: list[list[str]]) -> list[list[list[str]]]:
    """Group segments into API requests within total token and input limits."""
    requests: list[list[list[str]]] = []
    current_segments: list[list[str]] = []
    current_tokens = 0

    for segment in segments:
        segment_tokens = _count_context_tokens(segment)
        if current_segments and (
            current_tokens + segment_tokens > VOYAGE_CONTEXT_REQUEST_TOKEN_CAP
            or len(current_segments) >= VOYAGE_CONTEXT_MAX_INPUTS
        ):
            requests.append(current_segments)
            current_segments = []
            current_tokens = 0
        current_segments.append(segment)
        current_tokens += segment_tokens

    if current_segments:
        requests.append(current_segments)
    return requests
