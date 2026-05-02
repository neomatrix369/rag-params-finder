from itertools import product

from pydantic import BaseModel, Field

from server.models.enums import ChunkingMethod, RetrievalMethod


class ChunkParams(BaseModel):
    chunk_sizes: list[int] = Field(default=[512])
    overlaps: list[int] = Field(default=[50])


class EmbeddingConfig(BaseModel):
    models: list[str] = Field(default=["voyage-3.5-lite"])


class ChunkingConfig(BaseModel):
    methods: list[ChunkingMethod] = Field(default=[ChunkingMethod.RECURSIVE])
    params: ChunkParams = Field(default_factory=ChunkParams)


class RetrievalConfig(BaseModel):
    methods: list[RetrievalMethod] = Field(default=[RetrievalMethod.DENSE])
    top_k_initial: int = Field(default=20)
    top_k_final: int = Field(default=5)
    rerank_model: str | None = Field(default="rerank-2.5-lite")


class ExecutionConfig(BaseModel):
    parallelism: int = Field(default=1)
    on_error: str = Field(default="continue")


class ExperimentConfig(BaseModel):
    experiment_name: str
    data_paths: list[str]
    queries_file: str
    embedding: EmbeddingConfig
    chunking: ChunkingConfig
    retrieval: RetrievalConfig
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)


class RunParams(BaseModel):
    """Single-valued parameter set for one sweep run."""
    embedding_model: str
    chunking_method: ChunkingMethod
    chunk_size: int
    overlap: int
    retrieval_method: RetrievalMethod
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
            embedding_model=model,
            chunking_method=method,
            chunk_size=size,
            overlap=overlap,
            retrieval_method=retrieval,
            rerank_model=config.retrieval.rerank_model,
            top_k_initial=config.retrieval.top_k_initial,
            top_k_final=config.retrieval.top_k_final,
            data_paths=config.data_paths,
            queries_file=config.queries_file,
        )
        for model, method, size, overlap, retrieval in combos
    ]
