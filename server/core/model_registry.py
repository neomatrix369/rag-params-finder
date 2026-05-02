"""Unified model registry for embedding and reranker models.

Maps model IDs to metadata (provider, dimensions, HuggingFace ID) so the
embedder and reranker modules can dispatch to the correct backend without
any changes to the orchestrator or config models.
"""

from __future__ import annotations

from typing import TypedDict

from server.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingModelInfo(TypedDict):
    provider: str  # "voyage" | "local"
    dimensions: int
    huggingface_id: str | None
    description: str


class RerankerModelInfo(TypedDict):
    provider: str  # "voyage" | "local"
    huggingface_id: str | None
    description: str


EMBEDDING_MODELS: dict[str, EmbeddingModelInfo] = {
    "voyage-3.5-lite": {
        "provider": "voyage",
        "dimensions": 1024,
        "huggingface_id": None,
        "description": "Voyage AI lightweight embedding (1024-dim)",
    },
    "voyage-3.5": {
        "provider": "voyage",
        "dimensions": 1024,
        "huggingface_id": None,
        "description": "Voyage AI standard embedding (1024-dim)",
    },
    "voyage-context-3": {
        "provider": "voyage",
        "dimensions": 1024,
        "huggingface_id": None,
        "description": "Voyage AI context-optimized embedding (1024-dim)",
    },
    "all-MiniLM-L6-v2": {
        "provider": "local",
        "dimensions": 384,
        "huggingface_id": "sentence-transformers/all-MiniLM-L6-v2",
        "description": "Fast general-purpose sentence embeddings (384-dim, ~23MB)",
    },
}

RERANKER_MODELS: dict[str, RerankerModelInfo] = {
    "rerank-2.5-lite": {
        "provider": "voyage",
        "huggingface_id": None,
        "description": "Voyage AI lightweight reranker",
    },
    "rerank-2.5": {
        "provider": "voyage",
        "huggingface_id": None,
        "description": "Voyage AI standard reranker",
    },
    "cross-encoder/ms-marco-MiniLM-L-6-v2": {
        "provider": "local",
        "huggingface_id": "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "description": "Local cross-encoder reranker (~23MB, MS MARCO trained)",
    },
}


def get_model_info(model_id: str) -> EmbeddingModelInfo:
    info = EMBEDDING_MODELS.get(model_id)
    if info is None:
        known = ", ".join(EMBEDDING_MODELS)
        raise ValueError(f"Unknown embedding model '{model_id}'. Known: {known}")
    return info


def get_provider(model_id: str) -> str:
    return get_model_info(model_id)["provider"]


def get_dimensions(model_id: str) -> int:
    return get_model_info(model_id)["dimensions"]


def get_index_name(model_id: str) -> str:
    dims = get_dimensions(model_id)
    return f"vector_index_{dims}"


def get_reranker_info(model_id: str) -> RerankerModelInfo:
    info = RERANKER_MODELS.get(model_id)
    if info is None:
        known = ", ".join(RERANKER_MODELS)
        raise ValueError(f"Unknown reranker model '{model_id}'. Known: {known}")
    return info


def get_reranker_provider(model_id: str) -> str:
    return get_reranker_info(model_id)["provider"]
