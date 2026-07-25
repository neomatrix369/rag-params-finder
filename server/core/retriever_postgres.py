"""Dense retrieval over pgvector — the Postgres counterpart to ``retriever.py``.

Sparse and hybrid retrieval arrive in Slice 35; this module owns the dense path.

**Invariant:** every query filters by ``embedding_model``. Vectors from
different models share one ``chunks`` table, so comparing across models would
produce silently meaningless scores. The filter is not optional here — it is
built into the single WHERE clause every query goes through, and an empty model
is rejected before any SQL runs.
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
    if not embedding_model:
        raise ValueError(
            "embedding_model is required for dense search — chunks from different "
            "models share one table and must never be compared"
        )

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


def search(
    method: RetrievalMethod,
    query_text: str,
    experiment_id: str,
    embedding_model: str,
    run_id: str,
    top_k: int = 20,
    query_embedding: list[float] | None = None,
) -> list[SearchResult]:
    """Dispatcher mirroring ``server.core.retriever.search``.

    Sparse and hybrid raise NotImplementedError until Slice 35 rather than
    silently degrading to dense — a sweep that quietly changed retrieval method
    would invalidate its own comparison.
    """
    if method == RetrievalMethod.DENSE:
        if query_embedding is None:
            raise ValueError("query_embedding is required for dense search")
        return dense_search(query_embedding, experiment_id, embedding_model, run_id, top_k)

    if method in (RetrievalMethod.SPARSE, RetrievalMethod.HYBRID):
        raise NotImplementedError(
            f"{method.value} retrieval on Postgres is not implemented yet — "
            "available in Slice 35. Use retrieval method 'dense', or run this "
            "sweep with STORAGE_BACKEND=mongo."
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
