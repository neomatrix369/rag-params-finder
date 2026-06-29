"""SIE (Superlinked Inference Engine) embeddings via self-hosted Docker on :8720.

Mirrors the interface of local_embedder.py — plain module-level functions so
embedder_factory.py can wire them without any class hierarchy.

SIE server must be running:
    docker run -p 8720:8080 -v sie-hf-cache:/app/.cache/huggingface --platform linux/amd64 \
        -e HF_TOKEN=$HF_TOKEN ghcr.io/superlinked/sie-server:latest-cpu-default

Port 8720 is chosen to avoid the widely-used 8080 (Jenkins, Tomcat, Hadoop, etc.).
The SIE container internally listens on 8080; the host side maps to 8720.

Models route through the SIE registry full-name (e.g. "BAAI/bge-m3").
The model_registry maps short IDs ("bge-m3") to huggingface_id for the SDK call.
"""

from __future__ import annotations

from sie_sdk import SIEClient  # type: ignore[import-untyped]

from server.core.model_registry import get_model_info
from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

# SIE gateway rejects encode requests when pending + new items exceed 512.
# Stay well under so concurrent runs or in-flight work do not hit the cap.
_SIE_ENCODE_BATCH_SIZE = 128


def _get_client() -> SIEClient:
    """Create a SIE client for the configured base URL.

    Client objects are lightweight (no network connection until encode() is called),
    so we create one per call rather than caching — keeps tests simple and avoids
    stale-state bugs across test boundaries.
    """
    client = SIEClient(settings.sie_base_url)
    logger.debug("SIE client created — base_url=%s", settings.sie_base_url)
    return client


def _resolve_sie_model_name(model_id: str) -> str:
    """Return the full HuggingFace model name for the SIE SDK call.

    The model registry stores short IDs (e.g. "bge-m3") mapped to full
    HuggingFace IDs (e.g. "BAAI/bge-m3") in the huggingface_id field.
    """
    info = get_model_info(model_id)
    return info["huggingface_id"] or model_id


def embed_documents_sie(texts: list[str], model_id: str) -> list[list[float]]:
    """Embed a batch of document texts using SIE (dense output only).

    Args:
        texts: Document chunks to embed.
        model_id: Registry model ID (e.g. "bge-m3").

    Returns:
        List of 1024-dim float vectors, one per input text.

    Raises:
        RuntimeError: If SIE server is unreachable or encode fails.
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
    except Exception as exc:
        raise RuntimeError(f"SIE unreachable or encode failed: {exc}") from exc


def embed_query_sie(text: str, model_id: str) -> list[float]:
    """Embed a single query text using SIE (dense output only).

    Args:
        text: Query string to embed.
        model_id: Registry model ID (e.g. "bge-m3").

    Returns:
        1024-dim float vector.

    Raises:
        RuntimeError: If SIE server is unreachable or encode fails.
    """
    sie_model = _resolve_sie_model_name(model_id)
    logger.debug("SIE query embed — model=%s", sie_model)
    try:
        client = _get_client()
        results = client.encode(sie_model, [{"text": text}])
        vector: list[float] = results[0]["dense"].tolist()
        logger.debug("SIE query embed OK — dim=%d", len(vector))
        return vector
    except Exception as exc:
        raise RuntimeError(f"SIE unreachable or encode failed: {exc}") from exc
