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
    provider: str  # "voyage" | "local" | "sie"
    dimensions: int
    huggingface_id: str | None
    description: str
    contextualized: bool  # uses contextualized_embed() API (e.g. voyage-context-3)


class RerankerModelInfo(TypedDict):
    provider: str  # "voyage" | "local"
    huggingface_id: str | None
    description: str


EMBEDDING_MODELS: dict[str, EmbeddingModelInfo] = {
    # Voyage 4 series (1024-dim default; shared embedding space)
    "voyage-4-large": {
        "provider": "voyage",
        "dimensions": 1024,
        "huggingface_id": None,
        "description": "Voyage 4 flagship embedding (1024-dim)",
        "contextualized": False,
    },
    "voyage-4": {
        "provider": "voyage",
        "dimensions": 1024,
        "huggingface_id": None,
        "description": "Voyage 4 general-purpose embedding (1024-dim)",
        "contextualized": False,
    },
    "voyage-4-lite": {
        "provider": "voyage",
        "dimensions": 1024,
        "huggingface_id": None,
        "description": "Voyage 4 latency/cost-optimized embedding (1024-dim)",
        "contextualized": False,
    },
    # Domain-specific (1024-dim)
    "voyage-code-3": {
        "provider": "voyage",
        "dimensions": 1024,
        "huggingface_id": None,
        "description": "Voyage code retrieval embedding (1024-dim)",
        "contextualized": False,
    },
    "voyage-finance-2": {
        "provider": "voyage",
        "dimensions": 1024,
        "huggingface_id": None,
        "description": "Voyage finance domain embedding (1024-dim)",
        "contextualized": False,
    },
    "voyage-law-2": {
        "provider": "voyage",
        "dimensions": 1024,
        "huggingface_id": None,
        "description": "Voyage legal domain embedding (1024-dim)",
        "contextualized": False,
    },
    "voyage-context-3": {
        "provider": "voyage",
        "dimensions": 1024,
        "huggingface_id": None,
        "description": "Voyage contextualized chunk embedding (1024-dim)",
        "contextualized": True,
    },
    # Voyage 3 series (legacy API; 1024-dim default)
    "voyage-3-large": {
        "provider": "voyage",
        "dimensions": 1024,
        "huggingface_id": None,
        "description": "Voyage 3 large embedding (1024-dim, legacy)",
        "contextualized": False,
    },
    "voyage-3.5-lite": {
        "provider": "voyage",
        "dimensions": 1024,
        "huggingface_id": None,
        "description": "Voyage 3.5 lightweight embedding (1024-dim, legacy)",
        "contextualized": False,
    },
    "voyage-3.5": {
        "provider": "voyage",
        "dimensions": 1024,
        "huggingface_id": None,
        "description": "Voyage 3.5 standard embedding (1024-dim, legacy)",
        "contextualized": False,
    },
    "voyage-3": {
        "provider": "voyage",
        "dimensions": 1024,
        "huggingface_id": None,
        "description": "Voyage 3 general-purpose embedding (1024-dim, legacy)",
        "contextualized": False,
    },
    "voyage-multilingual-2": {
        "provider": "voyage",
        "dimensions": 1024,
        "huggingface_id": None,
        "description": "Voyage multilingual retrieval embedding (1024-dim, legacy)",
        "contextualized": False,
    },
    # Local
    "all-MiniLM-L6-v2": {
        "provider": "local",
        "dimensions": 384,
        "huggingface_id": "sentence-transformers/all-MiniLM-L6-v2",
        "description": "Fast general-purpose sentence embeddings (384-dim, ~23MB)",
        "contextualized": False,
    },
    # SIE (Superlinked Inference Engine) — self-hosted Docker on :8720
    "bge-m3": {
        "provider": "sie",
        "dimensions": 1024,
        "huggingface_id": "BAAI/bge-m3",
        "description": "BGE-M3 multi-lingual dense+sparse+multi-vector (1024-dim, SIE)",
        "contextualized": False,
    },
    "stella-v5": {
        "provider": "sie",
        "dimensions": 1024,
        "huggingface_id": "NovaSearch/stella_en_1.5B_v5",
        "description": "Stella v5 1.5B English dense embeddings (1024-dim, SIE)",
        "contextualized": False,
    },
    "splade-v3": {
        "provider": "sie",
        "dimensions": 30522,
        "huggingface_id": "naver/splade-v3",
        "description": "SPLADE v3 learned sparse embeddings (30522-dim, SIE)",
        "contextualized": False,
    },
}

RERANKER_MODELS: dict[str, RerankerModelInfo] = {
    "rerank-2.5-lite": {
        "provider": "voyage",
        "huggingface_id": None,
        "description": "Voyage 2.5 lightweight reranker (recommended)",
    },
    "rerank-2.5": {
        "provider": "voyage",
        "huggingface_id": None,
        "description": "Voyage 2.5 standard reranker (recommended)",
    },
    "rerank-2-lite": {
        "provider": "voyage",
        "huggingface_id": None,
        "description": "Voyage 2 lightweight reranker (legacy)",
    },
    "rerank-2": {
        "provider": "voyage",
        "huggingface_id": None,
        "description": "Voyage 2 standard reranker (legacy)",
    },
    "rerank-lite-1": {
        "provider": "voyage",
        "huggingface_id": None,
        "description": "Voyage 1 lightweight reranker (legacy)",
    },
    "rerank-1": {
        "provider": "voyage",
        "huggingface_id": None,
        "description": "Voyage 1 standard reranker (legacy)",
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


def is_contextualized_embedding(model_id: str) -> bool:
    return get_model_info(model_id)["contextualized"]


def list_embedding_models(*, provider: str | None = None) -> list[str]:
    if provider is None:
        return list(EMBEDDING_MODELS)
    return [mid for mid, info in EMBEDDING_MODELS.items() if info["provider"] == provider]


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
