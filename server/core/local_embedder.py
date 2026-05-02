"""Local embedding via sentence-transformers (no API key, no rate limits).

Models are downloaded from HuggingFace on first use (~23MB for MiniLM)
and cached locally.  Subsequent runs load from cache instantly.
"""

from __future__ import annotations

from sentence_transformers import SentenceTransformer

from server.core.model_registry import get_model_info
from server.utils.logger import get_logger

logger = get_logger(__name__)

_models: dict[str, SentenceTransformer] = {}


def _get_model(model_id: str) -> SentenceTransformer:
    if model_id not in _models:
        info = get_model_info(model_id)
        hf_id = info["huggingface_id"] or model_id
        logger.info(f"Loading local embedding model: {hf_id}")
        _models[model_id] = SentenceTransformer(hf_id)
        logger.info(f"Local embedding model loaded: {hf_id}")
    return _models[model_id]


def embed_documents_local(texts: list[str], model_id: str) -> list[list[float]]:
    """Embed documents using a local SentenceTransformer model."""
    logger.info(f"Embedding {len(texts)} documents locally with {model_id}")
    model = _get_model(model_id)
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    result = [emb.tolist() for emb in embeddings]
    logger.info(f"Generated {len(result)} local embeddings, dim={len(result[0])}")
    return result


def embed_query_local(text: str, model_id: str) -> list[float]:
    """Embed a single query using a local SentenceTransformer model."""
    logger.info(f"Embedding query locally with {model_id}")
    model = _get_model(model_id)
    embedding = model.encode(text, show_progress_bar=False, normalize_embeddings=True)
    result = embedding.tolist()
    logger.info(f"Generated local query embedding, dim={len(result)}")
    return result
