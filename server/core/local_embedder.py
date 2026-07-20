"""Local embedding via sentence-transformers (no API key, no rate limits).

Models are downloaded from HuggingFace on first use (~23MB for MiniLM)
and cached locally.  Subsequent runs load from cache instantly.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Callable, Iterator

import torch
from sentence_transformers import SentenceTransformer

from server.core.model_registry import get_model_info
from server.utils.logger import get_logger

logger = get_logger(__name__)

_models: dict[str, SentenceTransformer] = {}


def _local_thread_budget(parallelism: int) -> int | None:
    if parallelism <= 1:
        return None

    cpu_count = os.cpu_count() or 1
    return max(1, cpu_count // max(1, parallelism))


@contextlib.contextmanager
def _limited_thread_pool(parallelism: int) -> Iterator[None]:
    budget = _local_thread_budget(parallelism)
    if budget is None:
        yield
        return

    previous = torch.get_num_threads()
    if budget == previous:
        yield
        return

    torch.set_num_threads(budget)
    try:
        yield
    finally:
        torch.set_num_threads(previous)


def _get_model(model_id: str) -> SentenceTransformer:
    if model_id not in _models:
        info = get_model_info(model_id)
        hf_id = info["huggingface_id"] or model_id
        logger.info("local embed model load — %s", hf_id)
        _models[model_id] = SentenceTransformer(hf_id)
        logger.info("local embed model ready — %s", hf_id)
    return _models[model_id]


def embed_documents_local(
    texts: list[str],
    model_id: str,
    *,
    cancel_check: Callable[[], None] | None = None,
    parallelism: int = 1,
) -> list[list[float]]:
    """Embed documents using a local SentenceTransformer model."""
    if cancel_check is not None:
        cancel_check()
    logger.info("embedding local batch — texts=%s model=%s", len(texts), model_id)
    model = _get_model(model_id)
    with _limited_thread_pool(parallelism):
        embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    result = [emb.tolist() for emb in embeddings]
    logger.info(
        "local embed OK — count=%s dim=%s",
        len(result),
        len(result[0]),
    )
    return result


def embed_query_local(text: str, model_id: str) -> list[float]:
    """Embed a single query using a local SentenceTransformer model."""
    logger.debug("local query embed — model=%s", model_id)
    model = _get_model(model_id)
    embedding = model.encode(text, show_progress_bar=False, normalize_embeddings=True)
    result = embedding.tolist()
    logger.debug("local query embed OK — dim=%s", len(result))
    return result
