from enum import StrEnum


class ExperimentStatus(StrEnum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


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


class RetrieverType(StrEnum):
    """Type of retriever — traditional search or reranking.

    Traditional retrievers (dense, sparse, hybrid) produce initial candidates.
    Rerankers refine candidates from traditional retrievers.
    """

    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID = "hybrid"
    RERANKER = "reranker"
    CROSS_ENCODER = "cross_encoder"


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
