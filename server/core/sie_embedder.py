"""SIE (Superlinked Inference Engine) embeddings via HTTP (local Docker or remote gateway).

Mirrors the interface of local_embedder.py — plain module-level functions so
embedder_factory.py can wire them without any class hierarchy.

Configure via .env:
    SIE_ENABLED=true
    SIE_ENDPOINT=http://localhost:8720          # or https://your-sie-gateway
    SIE_API_KEY=...                             # optional; required when gateway auth is on

Local Docker quickstart (see docs/user-guide/sie-setup.md):
    docker run -p 8720:8080 -v sie-hf-cache:/app/.cache/huggingface --platform linux/amd64 \
        -e HF_TOKEN=$HF_TOKEN ghcr.io/superlinked/sie-server:latest-cpu-default

Models route through the SIE registry full-name (e.g. "BAAI/bge-m3").
The model_registry maps short IDs ("bge-m3") to huggingface_id for the SDK call.
"""

from __future__ import annotations

from collections.abc import Callable

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
            results = client.encode(sie_model, [{"text": t} for t in batch])
            vectors.extend(item["dense"].tolist() for item in results)
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
        results = client.encode(sie_model, [{"text": text}])
        vector: list[float] = results[0]["dense"].tolist()
        logger.debug("SIE query embed OK — dim=%d", len(vector))
        return vector
    except (ExperimentCancelledError, ExperimentPausedError):
        raise
    except Exception as exc:
        raise SIEUnavailableError(f"SIE unreachable or encode failed: {exc}") from exc
