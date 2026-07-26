"""Dense, sparse, and hybrid retrieval over Postgres / pgvector.

**Invariant:** every query filters by ``embedding_model``. Vectors from
different models share one ``chunks`` table, so comparing across models would
produce silently meaningless scores. The filter is not optional — it is built
into every WHERE clause, and an empty model is rejected before any SQL runs.

Sparse uses ``tsvector`` / ``ts_rank_cd`` (BM25-equivalent keyword search).
Hybrid fuses dense + sparse ranks with Reciprocal Rank Fusion CTEs
(Supabase-documented shape; ``rrf_k`` defaults to 60 to match Mongo).
"""

from __future__ import annotations

from pgvector import Vector
from psycopg import sql

from server.db.postgres import fetch_all
from server.db.postgres_docs import vector_column_for
from server.models.enums import RetrievalMethod
from server.models.results import Chunk, SearchResult
from server.utils.logger import get_logger

logger = get_logger(__name__)

# Match Mongo ``retriever._RRF_K`` for cross-backend rank comparison (Slice 38).
_DEFAULT_RRF_K = 60
_CANDIDATE_MULTIPLIER = 2


def _require_embedding_model(embedding_model: str, *, context: str) -> None:
    if not embedding_model:
        raise ValueError(
            f"embedding_model is required for {context} — chunks from different "
            "models share one table and must never be compared"
        )


def _dense_query(vector_column: str) -> sql.Composed:
    """Build the dense SQL for one vector column.

    ``score`` mirrors Atlas $vectorSearch's cosine scoring, which returns
    ``(1 + cosine_similarity) / 2``. With pgvector's cosine *distance* operator
    that is ``1 - distance / 2``, so scores from both backends land on the same
    0..1 scale and the Slice 38 comparison stays meaningful.

    ORDER BY repeats the distance expression rather than reusing the alias so
    the planner can serve it from the HNSW index.
    """
    column = sql.Identifier(vector_column)
    return sql.SQL("""
        SELECT chunk_id,
               text,
               chunk_index AS index,
               embedding_model,
               chunk_method,
               1 - ({column} <=> %(query)s) / 2 AS score
          FROM chunks
         WHERE experiment_id = %(experiment_id)s
           AND embedding_model = %(embedding_model)s
           AND run_id = %(run_id)s
           AND {column} IS NOT NULL
         ORDER BY {column} <=> %(query)s
         LIMIT %(top_k)s
    """).format(column=column)


def _sparse_query() -> sql.SQL:
    return sql.SQL("""
        SELECT chunk_id,
               text,
               chunk_index AS index,
               embedding_model,
               chunk_method,
               ts_rank_cd(text_search, websearch_to_tsquery('english', %(query)s))
                   AS score
          FROM chunks
         WHERE experiment_id = %(experiment_id)s
           AND embedding_model = %(embedding_model)s
           AND run_id = %(run_id)s
           AND text_search @@ websearch_to_tsquery('english', %(query)s)
         ORDER BY score DESC
         LIMIT %(top_k)s
    """)


def _hybrid_query(vector_column: str) -> sql.Composed:
    """RRF fusion of full-text and semantic ranks (Supabase hybrid-search shape).

    Both CTEs filter by experiment_id, embedding_model, and run_id. Weights and
    ``rrf_k`` are query parameters so callers can tune without a plpgsql function
    per vector width.
    """
    column = sql.Identifier(vector_column)
    return sql.SQL("""
        WITH full_text AS (
            SELECT chunk_id,
                   row_number() OVER (
                       ORDER BY ts_rank_cd(
                           text_search,
                           websearch_to_tsquery('english', %(query_text)s)
                       ) DESC
                   ) AS rank_ix
              FROM chunks
             WHERE experiment_id = %(experiment_id)s
               AND embedding_model = %(embedding_model)s
               AND run_id = %(run_id)s
               AND text_search @@ websearch_to_tsquery('english', %(query_text)s)
             ORDER BY rank_ix
             LIMIT %(candidate_limit)s
        ),
        semantic AS (
            SELECT chunk_id,
                   row_number() OVER (ORDER BY {column} <=> %(query)s) AS rank_ix
              FROM chunks
             WHERE experiment_id = %(experiment_id)s
               AND embedding_model = %(embedding_model)s
               AND run_id = %(run_id)s
               AND {column} IS NOT NULL
             ORDER BY rank_ix
             LIMIT %(candidate_limit)s
        )
        SELECT c.chunk_id,
               c.text,
               c.chunk_index AS index,
               c.embedding_model,
               c.chunk_method,
               coalesce(1.0 / (%(rrf_k)s + full_text.rank_ix), 0.0)
                   * %(full_text_weight)s
                 + coalesce(1.0 / (%(rrf_k)s + semantic.rank_ix), 0.0)
                   * %(semantic_weight)s AS score
          FROM full_text
          FULL OUTER JOIN semantic ON full_text.chunk_id = semantic.chunk_id
          JOIN chunks c
            ON c.chunk_id = coalesce(full_text.chunk_id, semantic.chunk_id)
         ORDER BY score DESC
         LIMIT %(top_k)s
    """).format(column=column)


def dense_search(
    query_embedding: list[float],
    experiment_id: str,
    embedding_model: str,
    run_id: str,
    top_k: int = 20,
) -> list[SearchResult]:
    """Rank chunks by cosine similarity to ``query_embedding`` via pgvector HNSW.

    Raises ValueError when ``embedding_model`` is missing, or when the query
    embedding's width has no vector column.
    """
    _require_embedding_model(embedding_model, context="dense search")

    vector_column = vector_column_for(len(query_embedding))
    logger.debug(
        "dense search start — experiment=%s run=%s model=%s column=%s k=%s",
        experiment_id,
        run_id,
        embedding_model,
        vector_column,
        top_k,
    )

    try:
        rows = fetch_all(
            _dense_query(vector_column),
            {
                "query": Vector(query_embedding),
                "experiment_id": experiment_id,
                "embedding_model": embedding_model,
                "run_id": run_id,
                "top_k": top_k,
            },
        )
    except Exception:
        logger.error(
            "dense search failed — experiment=%s model=%s column=%s",
            experiment_id,
            embedding_model,
            vector_column,
            exc_info=True,
        )
        raise

    logger.debug("dense search OK — %s hits", len(rows))
    return _to_search_results(rows, retrieval_method="dense")


def sparse_search(
    query_text: str,
    experiment_id: str,
    embedding_model: str,
    run_id: str,
    top_k: int = 20,
) -> list[SearchResult]:
    """Rank chunks by full-text relevance (``ts_rank_cd`` over ``text_search``)."""
    _require_embedding_model(embedding_model, context="sparse search")

    logger.debug(
        "sparse search start — experiment=%s run=%s model=%s k=%s",
        experiment_id,
        run_id,
        embedding_model,
        top_k,
    )

    try:
        rows = fetch_all(
            _sparse_query(),
            {
                "query": query_text,
                "experiment_id": experiment_id,
                "embedding_model": embedding_model,
                "run_id": run_id,
                "top_k": top_k,
            },
        )
    except Exception:
        logger.error(
            "sparse search failed — experiment=%s model=%s",
            experiment_id,
            embedding_model,
            exc_info=True,
        )
        raise

    logger.debug("sparse search OK — %s hits", len(rows))
    return _to_search_results(rows, retrieval_method="sparse")


def hybrid_search(
    query_text: str,
    query_embedding: list[float],
    experiment_id: str,
    embedding_model: str,
    run_id: str,
    top_k: int = 20,
    *,
    rrf_k: int = _DEFAULT_RRF_K,
    full_text_weight: float = 1.0,
    semantic_weight: float = 1.0,
) -> list[SearchResult]:
    """Fuse dense and sparse ranks with Reciprocal Rank Fusion."""
    _require_embedding_model(embedding_model, context="hybrid search")

    vector_column = vector_column_for(len(query_embedding))
    candidate_limit = max(top_k * _CANDIDATE_MULTIPLIER, top_k)

    logger.debug(
        "hybrid search start — experiment=%s run=%s model=%s k=%s rrf_k=%s",
        experiment_id,
        run_id,
        embedding_model,
        top_k,
        rrf_k,
    )

    try:
        rows = fetch_all(
            _hybrid_query(vector_column),
            {
                "query_text": query_text,
                "query": Vector(query_embedding),
                "experiment_id": experiment_id,
                "embedding_model": embedding_model,
                "run_id": run_id,
                "top_k": top_k,
                "candidate_limit": candidate_limit,
                "rrf_k": rrf_k,
                "full_text_weight": full_text_weight,
                "semantic_weight": semantic_weight,
            },
        )
    except Exception:
        logger.error(
            "hybrid search failed — experiment=%s model=%s column=%s",
            experiment_id,
            embedding_model,
            vector_column,
            exc_info=True,
        )
        raise

    logger.debug("hybrid search OK — %s hits after RRF", len(rows))
    return _to_search_results(rows, retrieval_method="hybrid")


def search(
    method: RetrievalMethod,
    query_text: str,
    experiment_id: str,
    embedding_model: str,
    run_id: str,
    top_k: int = 20,
    query_embedding: list[float] | None = None,
) -> list[SearchResult]:
    """Dispatcher mirroring ``server.core.retriever_mongo.search``."""
    if method == RetrievalMethod.DENSE:
        if query_embedding is None:
            raise ValueError("query_embedding is required for dense search")
        return dense_search(query_embedding, experiment_id, embedding_model, run_id, top_k)

    if method == RetrievalMethod.SPARSE:
        return sparse_search(query_text, experiment_id, embedding_model, run_id, top_k)

    if method == RetrievalMethod.HYBRID:
        if query_embedding is None:
            raise ValueError("query_embedding is required for hybrid search")
        return hybrid_search(
            query_text, query_embedding, experiment_id, embedding_model, run_id, top_k
        )

    raise ValueError(f"Unknown retrieval method: {method}")


def _to_search_results(rows: list[dict], retrieval_method: str) -> list[SearchResult]:
    return [
        SearchResult(
            chunk=Chunk(
                id=row["chunk_id"],
                text=row["text"],
                index=row["index"],
                embedding_model=row["embedding_model"],
                chunk_method=row["chunk_method"],
            ),
            dense_score=row["score"],
            rerank_score=None,
            retrieval_method=retrieval_method,
            rank=rank,
        )
        for rank, row in enumerate(rows, start=1)
    ]
