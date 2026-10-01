from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from server.models.config import DatabaseProvider, Provider, RetrieverConfig
from server.models.enums import ChunkingMethod, Phase, RetrievalMethod


class VectorStoreSnapshot(BaseModel):
    """Immutable snapshot of the vector store's identity at experiment-creation time.

    Captured once (at preflight) and stored on the experiment document. Historical
    experiments retain the infra identity that was true when they ran, even after
    the vector store's live configuration changes (Slice 55, ADR-008).
    """

    model_config = ConfigDict(frozen=True)

    provider: str
    storage_mode: str
    cluster_host: str | None = None
    collection_name: str | None = None
    index_names: list[str] = Field(default_factory=list)
    container: str | None = None
    image: str | None = None


class PreEmbedBatchRecord(BaseModel):
    """Record of a DoubleWord pre-embedding batch."""

    batch_id: str
    role: str  # "doc" | "query"
    status: str  # "in_progress" | "completed" | "failed"
    completed: int = 0
    total: int = 0
    dashboard_url: str | None = None


class PreEmbedStatus(BaseModel):
    """Status of DoubleWord pre-embedding for an experiment."""

    state: Literal["waiting", "ready", "failed"]
    batches: list[PreEmbedBatchRecord] = Field(default_factory=list)
    reason: str | None = None  # for failed state


class RunStatus(BaseModel):
    run_id: str
    experiment_id: str
    phase: Phase
    database_provider: DatabaseProvider
    embedding_provider: Provider
    embedding_model: str
    chunking_method: ChunkingMethod
    chunk_size: int
    overlap: int
    padding: int = 0
    retrievers: list[RetrieverConfig] = Field(default_factory=list)
    retrieval_method: RetrievalMethod
    retrieval_provider: Provider
    retrieval_model: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    elapsed_ms: int = 0
    error_message: str | None = None
    embedding_dimensions: int | None = None
