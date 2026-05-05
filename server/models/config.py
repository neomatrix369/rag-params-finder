from itertools import product
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from server.core.model_registry import EMBEDDING_MODELS, RERANKER_MODELS
from server.models.enums import ChunkingMethod, RetrievalMethod

Provider = Literal["local", "voyage"]
DatabaseProvider = Literal["mongodb"]  # Future: "pinecone", "weaviate", "qdrant"


class ChunkParams(BaseModel):
    chunk_sizes: list[int] = Field(default=[512])
    overlaps: list[int] = Field(default=[50])


class EmbeddingConfig(BaseModel):
    provider: Provider = Field(default="local")
    models: list[str] = Field(default=["all-MiniLM-L6-v2"])

    @model_validator(mode="after")
    def validate_models_match_provider(self) -> "EmbeddingConfig":
        for model_id in self.models:
            if model_id not in EMBEDDING_MODELS:
                known = ", ".join(EMBEDDING_MODELS)
                raise ValueError(f"Unknown embedding model '{model_id}'. Known: {known}")
            registered_provider = EMBEDDING_MODELS[model_id]["provider"]
            if registered_provider != self.provider:
                raise ValueError(
                    f"Embedding model '{model_id}' belongs to provider "
                    f"'{registered_provider}', but config specifies "
                    f"provider '{self.provider}'"
                )
        return self


class ChunkingConfig(BaseModel):
    methods: list[ChunkingMethod] = Field(default=[ChunkingMethod.RECURSIVE])
    params: ChunkParams = Field(default_factory=ChunkParams)


class RetrievalConfig(BaseModel):
    methods: list[RetrievalMethod] = Field(default=[RetrievalMethod.DENSE])
    top_k_initial: int = Field(default=20)
    top_k_final: int = Field(default=5)
    rerank_provider: Provider = Field(default="local")
    rerank_model: str | None = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")

    @model_validator(mode="after")
    def validate_rerank_model_matches_provider(self) -> "RetrievalConfig":
        if self.rerank_model is None:
            return self
        if self.rerank_model not in RERANKER_MODELS:
            known = ", ".join(RERANKER_MODELS)
            raise ValueError(f"Unknown reranker model '{self.rerank_model}'. Known: {known}")
        registered_provider = RERANKER_MODELS[self.rerank_model]["provider"]
        if registered_provider != self.rerank_provider:
            raise ValueError(
                f"Reranker model '{self.rerank_model}' belongs to provider "
                f"'{registered_provider}', but config specifies "
                f"rerank_provider '{self.rerank_provider}'"
            )
        return self


class ExecutionConfig(BaseModel):
    parallelism: int = Field(default=1)
    on_error: str = Field(default="continue")


class ExperimentConfig(BaseModel):
    experiment_name: str
    data_paths: list[str]
    queries_file: str
    database_provider: DatabaseProvider = Field(default="mongodb")
    embedding: EmbeddingConfig
    chunking: ChunkingConfig
    retrieval: RetrievalConfig
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)


class RunParams(BaseModel):
    """Single-valued parameter set for one sweep run."""

    database_provider: DatabaseProvider
    embedding_provider: Provider
    embedding_model: str
    chunking_method: ChunkingMethod
    chunk_size: int
    overlap: int
    retrieval_method: RetrievalMethod
    rerank_provider: Provider
    rerank_model: str | None
    top_k_initial: int
    top_k_final: int
    data_paths: list[str]
    queries_file: str


def expand_sweep(config: ExperimentConfig) -> list[RunParams]:
    """Cartesian product of all sweep dimensions into individual RunParams."""
    combos = product(
        config.embedding.models,
        config.chunking.methods,
        config.chunking.params.chunk_sizes,
        config.chunking.params.overlaps,
        config.retrieval.methods,
    )
    return [
        RunParams(
            database_provider=config.database_provider,
            embedding_provider=config.embedding.provider,
            embedding_model=model,
            chunking_method=method,
            chunk_size=size,
            overlap=overlap,
            retrieval_method=retrieval,
            rerank_provider=config.retrieval.rerank_provider,
            rerank_model=config.retrieval.rerank_model,
            top_k_initial=config.retrieval.top_k_initial,
            top_k_final=config.retrieval.top_k_final,
            data_paths=config.data_paths,
            queries_file=config.queries_file,
        )
        for model, method, size, overlap, retrieval in combos
    ]
