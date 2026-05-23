from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from server.models.enums import ChunkingMethod, Phase, RetrievalMethod

Provider = Literal["local", "voyage", "kimchi"]
DatabaseProvider = Literal["mongodb"]  # Future: "pinecone", "weaviate", "qdrant"


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
    retrieval_method: RetrievalMethod
    retrieval_provider: Provider
    retrieval_model: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    elapsed_ms: int = 0
    error_message: str | None = None
