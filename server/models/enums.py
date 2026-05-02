from enum import Enum


class ChunkingMethod(str, Enum):
    FIXED = "fixed"
    RECURSIVE = "recursive"
    TOKEN = "token"
    SENTENCE = "sentence"
    SEMANTIC = "semantic"


class RetrievalMethod(str, Enum):
    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID = "hybrid"


class Phase(str, Enum):
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
