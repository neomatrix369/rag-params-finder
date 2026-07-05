import warnings
from itertools import product
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from server.core.model_registry import EMBEDDING_MODELS, RERANKER_MODELS
from server.models.enums import ChunkingMethod, RetrievalMethod, RetrieverType

Provider = Literal["local", "voyage", "sie", "kimchi"]
DatabaseProvider = Literal["mongodb"]  # Future: "pinecone", "weaviate", "qdrant"


class ChunkParams(BaseModel):
    chunk_sizes: list[int] = Field(default=[512])
    overlaps: list[int] = Field(default=[50])
    # Minimum chunk character length. Undersized chunks are merged forward into
    # the next chunk until they reach this length. 0 disables padding (no-op).
    paddings: list[int] = Field(default=[0])

    @model_validator(mode="after")
    def warn_padding_exceeds_chunk_size(self) -> "ChunkParams":
        min_size = min(self.chunk_sizes)
        bad = [p for p in self.paddings if p > min_size]
        if bad:
            warnings.warn(
                f"paddings {bad} exceed min chunk_size {min_size}: "
                "chunks may all merge into a single blob",
                stacklevel=2,
            )
        return self


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


class RetrieverConfig(BaseModel):
    """Single retriever configuration for one sweep run.

    Each entry in ``retrieval.retrievers`` becomes its own run — retrievers are never chained.
    Traditional types (dense/sparse/hybrid) search directly; rerankers fetch dense candidates
    internally then rerank (implementation detail, not a second retriever on the run).
    """

    type: RetrieverType
    provider: Provider | None = Field(default=None)
    model: str | None = Field(default=None)

    @model_validator(mode="after")
    def validate_provider_model_for_rerankers(self) -> "RetrieverConfig":
        """Reranker and cross-encoder types require provider and model."""
        if self.type in {RetrieverType.RERANKER, RetrieverType.CROSS_ENCODER}:
            if self.provider is None:
                raise ValueError(f"{self.type} requires 'provider' field")
            if self.model is None:
                raise ValueError(f"{self.type} requires 'model' field")

            # Validate against reranker registry
            if self.model not in RERANKER_MODELS:
                known = ", ".join(RERANKER_MODELS)
                raise ValueError(f"Unknown reranker model '{self.model}'. Known: {known}")

            registered_provider = RERANKER_MODELS[self.model]["provider"]
            if registered_provider != self.provider:
                raise ValueError(
                    f"Reranker model '{self.model}' belongs to provider "
                    f"'{registered_provider}', but config specifies "
                    f"provider '{self.provider}'"
                )
        return self


class RetrievalConfig(BaseModel):
    """Retrieval configuration with unified retriever list.

    New format (preferred):
        retrievers: list of RetrieverConfig — each entry is one sweep dimension (one run each)

    Old format (deprecated, auto-migrated):
        methods: list of RetrievalMethod
        retrieval_provider + retrieval_model: separate reranking config
    """

    top_k_initial: int = Field(default=20)
    top_k_final: int = Field(default=5)
    retrievers: list[RetrieverConfig] = Field(
        default_factory=lambda: [RetrieverConfig(type=RetrieverType.DENSE)]
    )

    # DEPRECATED — backward compatibility for old configs
    methods: list[RetrievalMethod] | None = Field(default=None)
    retrieval_provider: Provider | None = Field(default=None)
    retrieval_model: str | None = Field(default=None)

    @model_validator(mode="after")
    def migrate_old_config_format(self) -> "RetrievalConfig":
        """Auto-migrate old-style config (methods + rerank_*) to new retrievers format."""
        if self.methods is not None:
            # Old format detected — synthesize retrievers list
            # Only migrate if retrievers is still at default (single DENSE)
            if len(self.retrievers) == 1 and self.retrievers[0].type == RetrieverType.DENSE:
                self.retrievers = [
                    RetrieverConfig(type=RetrieverType(method.value)) for method in self.methods
                ]

                # Add reranker if configured
                if self.retrieval_model is not None and self.retrieval_provider is not None:
                    self.retrievers.append(
                        RetrieverConfig(
                            type=RetrieverType.RERANKER,
                            provider=self.retrieval_provider,
                            model=self.retrieval_model,
                        )
                    )
        return self

    @model_validator(mode="after")
    def validate_retrieval_model_matches_provider(self) -> "RetrievalConfig":
        """Validate old-format reranker config (for backward compat)."""
        if self.retrieval_model is None:
            return self
        if self.retrieval_model not in RERANKER_MODELS:
            known = ", ".join(RERANKER_MODELS)
            raise ValueError(f"Unknown reranker model '{self.retrieval_model}'. Known: {known}")
        registered_provider = RERANKER_MODELS[self.retrieval_model]["provider"]
        if self.retrieval_provider is not None and registered_provider != self.retrieval_provider:
            raise ValueError(
                f"Reranker model '{self.retrieval_model}' belongs to provider "
                f"'{registered_provider}', but config specifies "
                f"retrieval_provider '{self.retrieval_provider}'"
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
    """Single-valued parameter set for one sweep run.

    Exactly one retriever per run (``retrievers`` has length 1).
    Deprecated ``retrieval_*`` fields are synthesized for backward compatibility.
    """

    database_provider: DatabaseProvider
    embedding_provider: Provider
    embedding_model: str
    chunking_method: ChunkingMethod
    chunk_size: int
    overlap: int
    padding: int = Field(default=0)
    top_k_initial: int
    top_k_final: int
    data_paths: list[str]
    queries_file: str

    # NEW — unified retriever configuration
    retrievers: list[RetrieverConfig] = Field(
        default_factory=lambda: [RetrieverConfig(type=RetrieverType.DENSE)]
    )

    # DEPRECATED — backward compatibility (always populated, synthesized from retrievers)
    retrieval_method: RetrievalMethod
    retrieval_provider: Provider
    retrieval_model: str | None = Field(default=None)


_RERANKER_TYPES = {RetrieverType.RERANKER, RetrieverType.CROSS_ENCODER}


def _legacy_retrieval_fields(
    retriever: RetrieverConfig,
) -> tuple[RetrievalMethod, Provider, str | None]:
    """Map a single retriever to deprecated run_status fields."""
    if retriever.type in _RERANKER_TYPES:
        return RetrievalMethod.DENSE, retriever.provider or "local", retriever.model
    return RetrievalMethod(retriever.type.value), "local", None


def expand_sweep(config: ExperimentConfig) -> list[RunParams]:
    """Cartesian product of all sweep dimensions into individual RunParams.

    Sweep dimensions: embedding models × chunking methods × chunk sizes × overlaps
    × paddings × retrievers.
    Each retriever list entry becomes exactly one run — retrievers are never combined.

    Example:
        retrievers: [dense, sparse, cross_encoder]
        → Run 1: dense only
        → Run 2: sparse only
        → Run 3: cross_encoder only (dense candidate fetch is internal to the orchestrator)
    """
    retrievers_to_sweep = config.retrieval.retrievers or [RetrieverConfig(type=RetrieverType.DENSE)]

    combos = product(
        config.embedding.models,
        config.chunking.methods,
        config.chunking.params.chunk_sizes,
        config.chunking.params.overlaps,
        config.chunking.params.paddings or [0],  # fallback: YAML [] would skip padding dimension
        retrievers_to_sweep,
    )

    runs: list[RunParams] = []
    for model, method, size, overlap, padding, retriever in combos:
        legacy_method, legacy_provider, legacy_model = _legacy_retrieval_fields(retriever)
        runs.append(
            RunParams(
                database_provider=config.database_provider,
                embedding_provider=config.embedding.provider,
                embedding_model=model,
                chunking_method=method,
                chunk_size=size,
                overlap=overlap,
                padding=padding,
                top_k_initial=config.retrieval.top_k_initial,
                top_k_final=config.retrieval.top_k_final,
                data_paths=config.data_paths,
                queries_file=config.queries_file,
                retrievers=[retriever],
                retrieval_method=legacy_method,
                retrieval_provider=legacy_provider,
                retrieval_model=legacy_model,
            )
        )

    return runs
