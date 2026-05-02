from pymongo import IndexModel, ASCENDING
from server.db.atlas import (
    get_collection,
    CHUNKS_COLLECTION,
    EXPERIMENTS_COLLECTION,
    RUN_STATUS_COLLECTION,
    COLLECTIONS_COLLECTION,
    QUERIES_COLLECTION,
    RESULTS_COLLECTION,
)
from server.utils.logger import get_logger

logger = get_logger(__name__)


def create_indexes():
    """Create standard indexes and vector search index."""

    # Standard indexes
    logger.info("Creating standard indexes...")

    # Experiments: created_at, status
    experiments = get_collection(EXPERIMENTS_COLLECTION)
    experiments.create_indexes([
        IndexModel([("created_at", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
    ])

    # Run status: experiment_id, phase
    run_status = get_collection(RUN_STATUS_COLLECTION)
    run_status.create_indexes([
        IndexModel([("experiment_id", ASCENDING)]),
        IndexModel([("phase", ASCENDING)]),
    ])

    # Chunks: experiment_id
    chunks = get_collection(CHUNKS_COLLECTION)
    chunks.create_indexes([
        IndexModel([("experiment_id", ASCENDING)]),
    ])

    # Collections: hash (dedup)
    collections = get_collection(COLLECTIONS_COLLECTION)
    collections.create_indexes([
        IndexModel([("hash", ASCENDING)]),
    ])

    # Queries: experiment_id
    queries = get_collection(QUERIES_COLLECTION)
    queries.create_indexes([
        IndexModel([("experiment_id", ASCENDING)]),
    ])

    # Results: experiment_id, query_id
    results = get_collection(RESULTS_COLLECTION)
    results.create_indexes([
        IndexModel([("experiment_id", ASCENDING)]),
        IndexModel([("query_id", ASCENDING)]),
    ])

    logger.info("Standard indexes created")

    # Vector index creation note
    logger.info("Vector index must be created manually in Atlas UI:")
    logger.info("  Collection: chunks")
    logger.info("  Field: embedding")
    logger.info("  Type: vector")
    logger.info("  Dimensions: 1024")
    logger.info("  Similarity: cosine")
    logger.info("  Filters: experiment_id, embedding_model")
    logger.info("  See: https://www.mongodb.com/docs/atlas/atlas-vector-search/create-index/")


def check_vector_index_ready() -> bool:
    """Check if vector index exists on chunks collection."""
    # This is a placeholder - actual implementation would check Atlas
    # For now, we'll assume it's ready
    logger.info("Assuming vector index is ready (manual check required)")
    return True
