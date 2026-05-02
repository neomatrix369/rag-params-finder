from datetime import datetime
from pydantic import BaseModel, Field
from server.models.enums import Phase, ChunkingMethod, RetrievalMethod


class RunStatus(BaseModel):
    run_id: str
    experiment_id: str
    phase: Phase
    embedding_model: str
    chunking_method: ChunkingMethod
    chunk_size: int
    overlap: int
    retrieval_method: RetrievalMethod
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    elapsed_ms: int = 0
    error_message: str | None = None
