"""SIE (Superlinked Inference Engine) embeddings via HTTP.

Preferred: remote SIE gateway — set SIE_ENDPOINT + SIE_API_KEY in .env (no Docker).
Fallback: self-hosted Docker on :8720 — see docs/user-guide/sie-setup.md.

Configure via .env (same three vars for remote gateway and local Docker):
    SIE_ENABLED=true                              # master on/off
    SIE_ENDPOINT=https://your-sie-gateway...      # where (or http://localhost:8720 for Docker)
    SIE_API_KEY=...                               # auth when gateway requires it

Mirrors the interface of local_embedder.py — plain module-level functions so
embedder_factory.py can wire them without any class hierarchy.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any, cast

from sie_sdk import SIEClient  # type: ignore[import-untyped]

from server.core.experiment_control import ExperimentCancelledError, ExperimentPausedError
from server.core.model_registry import get_model_info
from server.core.sie_guard import SIEUnavailableError
from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

# SIE gateway rejects encode requests when pending + new items exceed 512.
# Stay well under so concurrent runs or in-flight work do not hit the cap.
_SIE_ENCODE_BATCH_SIZE = 128
_SIE_MAX_IN_FLIGHT_REQUESTS = 2
_SIE_ENCODE_MAX_RETRIES = 3
_SIE_INITIAL_RETRY_DELAY_S = 0.5

_SIE_ENCODE_SEMAPHORE = threading.Semaphore(_SIE_MAX_IN_FLIGHT_REQUESTS)


def _get_client() -> SIEClient:
    """Create a SIE client for the configured endpoint.

    Client objects are lightweight (no network connection until encode() is called),
    so we create one per call rather than caching — keeps tests simple and avoids
    stale-state bugs across test boundaries.
    """
    api_key = settings.sie_api_key or None
    client = SIEClient(settings.sie_endpoint, api_key=api_key)
    logger.debug(
        "SIE client created — endpoint=%s auth=%s",
        settings.sie_endpoint,
        "bearer" if api_key else "none",
    )
    return client


def _resolve_sie_model_name(model_id: str) -> str:
    """Return the full HuggingFace model name for the SIE SDK call.

    The model registry stores short IDs (e.g. "bge-m3") mapped to full
    HuggingFace IDs (e.g. "BAAI/bge-m3") in the huggingface_id field.
    """
    info = get_model_info(model_id)
    return info["huggingface_id"] or model_id


def _is_retryable_sie_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "503" in message or "unavailable" in message or "service unavailable" in message


def _encode_with_retries(
    client: SIEClient,
    model: str,
    items: list[dict[str, str]],
) -> list[dict[str, Any]]:
    delay = _SIE_INITIAL_RETRY_DELAY_S
    for attempt in range(1, _SIE_ENCODE_MAX_RETRIES + 1):
        try:
            with _SIE_ENCODE_SEMAPHORE:
                return cast(list[dict[str, Any]], client.encode(model, items))
        except Exception as exc:
            if not _is_retryable_sie_error(exc) or attempt == _SIE_ENCODE_MAX_RETRIES:
                raise
            logger.warning(
                "SIE encode retrying — attempt=%d/%d delay=%.2fs error=%s",
                attempt,
                _SIE_ENCODE_MAX_RETRIES,
                delay,
                exc,
            )
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("SIE encode retries exhausted.")


def _to_float_vector(raw: object) -> list[float]:
    if hasattr(raw, "tolist"):
        return [float(x) for x in raw.tolist()]  # type: ignore[operator]
    if isinstance(raw, list):
        return [float(x) for x in raw]
    raise TypeError(f"Expected vector-like object, got {type(raw)!r}")


def embed_documents_sie(
    texts: list[str],
    model_id: str,
    *,
    cancel_check: Callable[[], None] | None = None,
) -> list[list[float]]:
    """Embed a batch of document texts using SIE (dense output only).

    Args:
        texts: Document chunks to embed.
        model_id: Registry model ID (e.g. "bge-m3").

    Returns:
        List of 1024-dim float vectors, one per input text.

    Raises:
        SIEUnavailableError: If SIE server is unreachable or encode fails.
    """
    if not texts:
        return []

    sie_model = _resolve_sie_model_name(model_id)
    logger.info("SIE embed batch — texts=%d model=%s", len(texts), sie_model)
    try:
        client = _get_client()
        vectors: list[list[float]] = []
        batch_count = (len(texts) + _SIE_ENCODE_BATCH_SIZE - 1) // _SIE_ENCODE_BATCH_SIZE
        if batch_count > 1:
            logger.info(
                "SIE embed sharded — %d texts split into %d batches (queue limit)",
                len(texts),
                batch_count,
            )
        for idx in range(0, len(texts), _SIE_ENCODE_BATCH_SIZE):
            if cancel_check is not None:
                cancel_check()
            batch = texts[idx : idx + _SIE_ENCODE_BATCH_SIZE]
            batch_num = idx // _SIE_ENCODE_BATCH_SIZE + 1
            logger.debug(
                "SIE embed progress — batch %d/%d texts=%d",
                batch_num,
                batch_count,
                len(batch),
            )
            # SDK returns one {dense, timing} dict per input item — not a batched ndarray.
            results = _encode_with_retries(client, sie_model, [{"text": t} for t in batch])
            vectors.extend(_to_float_vector(item["dense"]) for item in results)
        logger.info("SIE embed OK — count=%d dim=%d", len(vectors), len(vectors[0]))
        return vectors
    except (ExperimentCancelledError, ExperimentPausedError):
        raise
    except Exception as exc:
        raise SIEUnavailableError(f"SIE unreachable or encode failed: {exc}") from exc


def embed_query_sie(text: str, model_id: str) -> list[float]:
    """Embed a single query text using SIE (dense output only).

    Args:
        text: Query string to embed.
        model_id: Registry model ID (e.g. "bge-m3").

    Returns:
        1024-dim float vector.

    Raises:
        SIEUnavailableError: If SIE server is unreachable or encode fails.
    """
    sie_model = _resolve_sie_model_name(model_id)
    logger.debug("SIE query embed — model=%s", sie_model)
    try:
        client = _get_client()
        results = _encode_with_retries(client, sie_model, [{"text": text}])
        vector = _to_float_vector(results[0]["dense"])
        logger.debug("SIE query embed OK — dim=%d", len(vector))
        return vector
    except (ExperimentCancelledError, ExperimentPausedError):
        raise
    except Exception as exc:
        raise SIEUnavailableError(f"SIE unreachable or encode failed: {exc}") from exc
