from server.core.model_registry import get_index_name_for_dimensions
from server.db.atlas import CHUNKS_COLLECTION, get_collection
from server.db.indexes import ensure_vector_index
from server.models.results import Chunk, SearchResult
from server.utils.logger import get_logger

logger = get_logger(__name__)


def dense_search(
    query_embedding: list[float], experiment_id: str, embedding_model: str, top_k: int = 20
) -> list[SearchResult]:
    """Perform dense vector search using Atlas $vectorSearch."""

    dimensions = len(query_embedding)
    index_name = get_index_name_for_dimensions(dimensions)
    ensure_vector_index(dimensions)
    logger.info(
        f"Dense search for experiment={experiment_id}, model={embedding_model}, "
        f"index={index_name}, k={top_k}"
    )

    chunks_collection = get_collection(CHUNKS_COLLECTION)

    pipeline = [
        {
            "$vectorSearch": {
                "index": index_name,
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": top_k * 2,  # 2x candidates for better recall
                "limit": top_k,
                "filter": {
                    "experiment_id": {"$eq": experiment_id},
                    "embedding_model": {"$eq": embedding_model},
                },
            }
        },
        {
            "$project": {
                "_id": 0,
                "chunk_id": 1,
                "text": 1,
                "index": 1,
                "embedding_model": 1,
                "chunk_method": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    results = list(chunks_collection.aggregate(pipeline))
    logger.info(f"Dense search returned {len(results)} results")

    search_results = []
    for rank, doc in enumerate(results, start=1):
        chunk = Chunk(
            id=doc["chunk_id"],
            text=doc["text"],
            index=doc["index"],
            embedding_model=doc["embedding_model"],
            chunk_method=doc["chunk_method"],
        )
        search_result = SearchResult(
            chunk=chunk,
            dense_score=doc["score"],
            rerank_score=None,  # No reranking in Slice 1
            retrieval_method="dense",
            rank=rank,
        )
        search_results.append(search_result)

    return search_results
