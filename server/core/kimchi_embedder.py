"""Kimchi OpenAI-compatible embedding client."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx

from server.core.rate_limiter import RateLimiter, estimate_tokens
from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

MAX_RETRIES = 5
INITIAL_BACKOFF_S = 2.0

_client: httpx.Client | None = None
_limiter: RateLimiter | None = None
_dimensions_cache: dict[str, int] = {}


def get_client() -> httpx.Client:
    """Get Kimchi HTTP client singleton."""
    global _client
    if _client is None:
        if not settings.kimchi_base_url:
            raise ValueError("KIMCHI_BASE_URL not set in .env or environment")
        if not settings.kimchi_api_key:
            raise ValueError("KIMCHI_API_KEY not set in .env or environment")

        _client = httpx.Client(
            base_url=settings.kimchi_base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {settings.kimchi_api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
        logger.info("Kimchi embedding client initialized")
    return _client


def get_limiter() -> RateLimiter:
    """Get shared Kimchi rate limiter singleton."""
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter(
            rpm=settings.kimchi_rpm_limit,
            tpm=settings.kimchi_tpm_limit,
        )
        logger.info(
            f"Kimchi rate limiter initialized: {settings.kimchi_rpm_limit} RPM, "
            f"{settings.kimchi_tpm_limit} TPM"
        )
    return _limiter


def get_dimensions(model: str) -> int:
    """Probe and cache the embedding dimension for a Kimchi model."""
    if model not in _dimensions_cache:
        _dimensions_cache[model] = len(embed_query_kimchi("dimension probe", model))
    return _dimensions_cache[model]


def embed_documents_kimchi(texts: list[str], model: str) -> list[list[float]]:
    """Embed documents with Kimchi."""
    logger.info(f"Embedding {len(texts)} documents with Kimchi model={model}")
    embeddings = _embed(texts, model)
    if embeddings:
        _dimensions_cache[model] = len(embeddings[0])
    logger.info(f"Generated {len(embeddings)} Kimchi embeddings, dim={len(embeddings[0])}")
    return embeddings


def embed_query_kimchi(text: str, model: str) -> list[float]:
    """Embed a single query with Kimchi."""
    logger.info(f"Embedding query with Kimchi model={model}")
    embedding = _embed([text], model)[0]
    _dimensions_cache[model] = len(embedding)
    logger.info(f"Generated Kimchi query embedding, dim={len(embedding)}")
    return embedding


def _embed(texts: list[str], model: str) -> list[list[float]]:
    if not texts:
        return []

    client = get_client()
    tokens = estimate_tokens(texts)
    payload = {"model": model, "input": texts}

    def _request() -> httpx.Response:
        return client.post("/v1/embeddings", json=payload)

    response = _call_with_retry(_request, estimated_tokens=tokens)
    body = response.json()
    return _parse_embeddings(body, expected_count=len(texts))


def _call_with_retry(
    fn: Callable[[], httpx.Response],
    estimated_tokens: int = 0,
) -> httpx.Response:
    backoff = INITIAL_BACKOFF_S
    for attempt in range(1, MAX_RETRIES + 1):
        get_limiter().wait(estimated_tokens=estimated_tokens)
        try:
            response: httpx.Response = fn()
            if response.status_code == 429 or response.status_code >= 500:
                raise httpx.HTTPStatusError(
                    f"Retryable Kimchi HTTP status {response.status_code}",
                    request=response.request,
                    response=response,
                )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            retryable = status == 429 or status >= 500
            if not retryable or attempt == MAX_RETRIES:
                raise
            logger.warning(
                f"Kimchi HTTP {status} on attempt {attempt}/{MAX_RETRIES}, "
                f"backing off {backoff:.0f}s"
            )
            time.sleep(backoff)
            backoff *= 2
    raise RuntimeError("unreachable")


def _parse_embeddings(body: dict[str, Any], expected_count: int) -> list[list[float]]:
    data = body.get("data")
    if not isinstance(data, list):
        raise ValueError("Kimchi embeddings response missing list field 'data'")

    ordered = sorted(
        data,
        key=lambda item: item.get("index", 0) if isinstance(item, dict) else 0,
    )
    embeddings: list[list[float]] = []
    for item in ordered:
        if not isinstance(item, dict) or not isinstance(item.get("embedding"), list):
            raise ValueError("Kimchi embeddings response contained an invalid embedding item")
        embeddings.append([float(value) for value in item["embedding"]])

    if len(embeddings) != expected_count:
        raise ValueError(
            f"Kimchi returned {len(embeddings)} embeddings for {expected_count} input texts"
        )
    return embeddings
