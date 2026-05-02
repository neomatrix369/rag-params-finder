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
    on_error: str = Field(default="continue")  # "continue" | "stop"


class ExperimentConfig(BaseModel):
    experiment_name: str
    pdf_path: str
    queries_file: str
    embedding: EmbeddingConfig
    chunking: ChunkingConfig
    retrieval: RetrievalConfig
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
