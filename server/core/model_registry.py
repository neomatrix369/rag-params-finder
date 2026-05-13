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
    provider: str  # "voyage" | "local" | "kimchi"
    dimensions: int | None
    huggingface_id: str | None
    description: str
    contextualized: bool  # uses contextualized_embed() API (e.g. voyage-context-3)


class RerankerModelInfo(TypedDict):
    provider: str  # "voyage" | "local"
    huggingface_id: str | None
    description: str


_KIMCHI_EMBEDDING_MODELS = [
    ("mistral/codestral-embed", "Kimchi-hosted Mistral Codestral embedding"),
    ("mistral/mistral-embed", "Kimchi-hosted Mistral embedding"),
    ("mistral/codestral-embed-2505", "Kimchi-hosted Mistral Codestral 2505 embedding"),
    ("databricks/databricks-gte-large-en", "Kimchi-hosted Databricks GTE large English"),
    ("databricks/databricks-bge-large-en", "Kimchi-hosted Databricks BGE large English"),
    (
        "vertex_ai-language-models/gemini-flash-experimental",
        "Kimchi-hosted Vertex AI Gemini Flash experimental embedding",
    ),
    ("gemini/gemini-embedding-2-preview", "Kimchi-hosted Gemini embedding 2 preview"),
    ("gemini/gemini-embedding-001", "Kimchi-hosted Gemini embedding 001"),
    ("gemini/gemini-embedding-2", "Kimchi-hosted Gemini embedding 2"),
    ("perplexity/pplx-embed-v1-0.6b", "Kimchi-hosted Perplexity PPLX embed v1 0.6B"),
    ("perplexity/pplx-embed-v1-4b", "Kimchi-hosted Perplexity PPLX embed v1 4B"),
    ("azure/text-embedding-3-large", "Kimchi-hosted Azure text-embedding-3-large"),
    ("azure/text-embedding-ada-002", "Kimchi-hosted Azure text-embedding-ada-002"),
    ("azure/ada", "Kimchi-hosted Azure Ada embedding"),
    ("bedrock/marengo-embed-2-7", "Kimchi-hosted Bedrock Marengo Embed 2.7"),
    ("bedrock/titan-embed-text-v2", "Kimchi-hosted Bedrock Titan Embed Text v2"),
    ("bedrock/embed-v4:0", "Kimchi-hosted Bedrock Embed v4"),
    ("bedrock/embed-english-v3", "Kimchi-hosted Bedrock Embed English v3"),
    ("bedrock/embed-multilingual-v3", "Kimchi-hosted Bedrock Embed Multilingual v3"),
    ("bedrock/titan-embed-image-v1", "Kimchi-hosted Bedrock Titan Embed Image v1"),
    (
        "bedrock/nova-2-multimodal-embeddings-v1:0",
        "Kimchi-hosted Bedrock Nova 2 multimodal embeddings v1",
    ),
    ("bedrock/titan-embed-text-v1", "Kimchi-hosted Bedrock Titan Embed Text v1"),
    ("openai/text-embedding-3-large", "Kimchi-hosted OpenAI text-embedding-3-large"),
    ("openai/text-embedding-ada-002", "Kimchi-hosted OpenAI text-embedding-ada-002"),
    ("openai/text-embedding-3-small", "Kimchi-hosted OpenAI text-embedding-3-small"),
    ("openai/text-embedding-ada-002-v2", "Kimchi-hosted OpenAI text-embedding-ada-002-v2"),
    ("hosted_vllm/gte-qwen2-7b-instruct", "Kimchi-hosted vLLM GTE Qwen2 7B instruct"),
    (
        "hosted_vllm/multilingual-e5-large-instruct",
        "Kimchi-hosted vLLM multilingual E5 large instruct",
    ),
    ("hosted_vllm/bge-base-en-v1.5", "Kimchi-hosted vLLM BGE base English v1.5"),
    ("hosted_vllm/multilingual-e5-large", "Kimchi-hosted vLLM multilingual E5 large"),
    ("hosted_vllm/bge-m3", "Kimchi-hosted vLLM BGE M3"),
    (
        "azure_ai/Cohere-embed-v3-multilingual",
        "Kimchi-hosted Azure AI Cohere Embed v3 multilingual",
    ),
    ("azure_ai/embed-v-4-0", "Kimchi-hosted Azure AI Embed v4.0"),
    ("azure_ai/Cohere-embed-v3-english", "Kimchi-hosted Azure AI Cohere Embed v3 English"),
]


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
    **{
        model_id: {
            "provider": "kimchi",
            "dimensions": None,
            "huggingface_id": None,
            "description": description,
        }
        for model_id, description in _KIMCHI_EMBEDDING_MODELS
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
    dimensions = get_model_info(model_id)["dimensions"]
    if dimensions is None:
        raise ValueError(
            f"Embedding model '{model_id}' has runtime-detected dimensions. "
            "Use get_index_name_for_dimensions(len(embedding)) after embedding."
        )
    return dimensions


def is_contextualized_embedding(model_id: str) -> bool:
    return get_model_info(model_id)["contextualized"]


def list_embedding_models(*, provider: str | None = None) -> list[str]:
    if provider is None:
        return list(EMBEDDING_MODELS)
    return [mid for mid, info in EMBEDDING_MODELS.items() if info["provider"] == provider]


def get_index_name(model_id: str) -> str:
    dims = get_dimensions(model_id)
    return f"vector_index_{dims}"


def get_index_name_for_dimensions(dimensions: int) -> str:
    return f"vector_index_{dimensions}"


def get_reranker_info(model_id: str) -> RerankerModelInfo:
    info = RERANKER_MODELS.get(model_id)
    if info is None:
        known = ", ".join(RERANKER_MODELS)
        raise ValueError(f"Unknown reranker model '{model_id}'. Known: {known}")
    return info


def get_reranker_provider(model_id: str) -> str:
    return get_reranker_info(model_id)["provider"]
