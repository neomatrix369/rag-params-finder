from enum import StrEnum


class ChunkingMethod(StrEnum):
    FIXED = "fixed"
    RECURSIVE = "recursive"
    TOKEN = "token"
    SENTENCE = "sentence"
    SEMANTIC = "semantic"


class RetrievalMethod(StrEnum):
    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID = "hybrid"


class Phase(StrEnum):
    QUEUED = "queued"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    QUERYING = "querying"
    RERANKING = "reranking"
    COMPLETE = "complete"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
