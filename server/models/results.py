from pydantic import BaseModel


class Chunk(BaseModel):
    id: str
    text: str
    index: int
    embedding_model: str
    chunk_method: str


class SearchResult(BaseModel):
    chunk: Chunk
    dense_score: float
    rerank_score: float | None = None
    retrieval_method: str
    rank: int


class QueryResult(BaseModel):
    query_id: str
    experiment_id: str
    run_id: str
    query_text: str
    persona_id: str | None = None
    focus: str | None = None
    results: list[SearchResult]
    top_k: int
