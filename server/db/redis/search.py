"""Dense KNN, BM25, and client-side RRF hybrid search over one Redis chunks index.

Redis COSINE distance ``d`` is in [0, 2] (0 = identical).
``score = 1 - d/2`` converts it to the shared (1 + cosine) / 2 scale used by
Mongo, Postgres, and Elasticsearch so cross-backend comparison is valid.

BM25 sparse scores are engine-native relevance scores (higher = more relevant).
They are used for ranking only; RRF fusion is rank-based so the scale does not
need normalisation.
"""

from __future__ import annotations

import struct
from typing import Any

from server.core.retrieval.fusion import CANDIDATES_MULTIPLIER, rrf_fuse
from server.db.redis.schema import field_for_dims
from server.models.enums import RetrievalMethod
from server.models.results import Chunk, SearchResult

# TAG filter separator — TAGs are stored as pipe-delimited multi-values in Redis.
# Single-value filters use plain ``{value}`` syntax in FT.SEARCH.
_TAG_ESCAPE_CHARS = str.maketrans(
    {
        ",": r"\,",
        ".": r"\.",
        "<": r"\<",
        ">": r"\>",
        "{": r"\{",
        "}": r"\}",
        "[": r"\[",
        "]": r"\]",
        '"': r"\"",
        "'": r"\'",
        ":": r"\:",
        ";": r"\;",
        "!": r"\!",
        "@": r"\@",
        "#": r"\#",
        "$": r"\$",
        "%": r"\%",
        "^": r"\^",
        "&": r"\&",
        "*": r"\*",
        "(": r"\(",
        ")": r"\)",
        "-": r"\-",
        "+": r"\+",
        "=": r"\=",
        "~": r"\~",
        "|": r"\|",
        "?": r"\?",
        "/": r"\/",
        " ": r"\ ",
    }
)


def _escape_tag(value: str) -> str:
    """Escape a TAG field value for use inside ``{…}`` in a FT.SEARCH query."""
    return value.translate(_TAG_ESCAPE_CHARS)


def require_top_k(top_k: int) -> None:
    """Reject non-positive ``top_k`` before any network call."""
    if top_k <= 0:
        raise ValueError(f"top_k must be greater than 0 (got {top_k})")


def require_embedding_model(embedding_model: str) -> None:
    if not embedding_model:
        raise ValueError(
            "embedding_model is required — chunks from different models share one index "
            "and must never be compared"
        )


def _tag_filter(experiment_id: str, embedding_model: str, run_id: str) -> str:
    """Build the TAG pre-filter string for a FT.SEARCH query."""
    require_embedding_model(embedding_model)
    em = _escape_tag(embedding_model)
    ei = _escape_tag(experiment_id)
    ri = _escape_tag(run_id)
    return f"(@embedding_model:{{{em}}} @experiment_id:{{{ei}}} @run_id:{{{ri}}})"


def _to_bytes(embedding: list[float]) -> bytes:
    """Pack a float32 embedding vector as little-endian bytes."""
    return struct.pack(f"{len(embedding)}f", *embedding)


def _docs_to_results(
    docs: list[Any], retrieval_method: str, *, distance_field: str | None = None
) -> list[SearchResult]:
    results = []
    for rank, doc in enumerate(docs, start=1):
        chunk_id = getattr(doc, "chunk_id", "") or ""
        text = getattr(doc, "text", "") or ""
        embedding_model = getattr(doc, "embedding_model", "") or ""
        chunk_method = getattr(doc, "chunk_method", "") or getattr(doc, "chunking_method", "") or ""
        score_raw = getattr(doc, distance_field or "__score", None)
        if distance_field and score_raw is not None:
            # Convert COSINE distance → shared (1 + cosine) / 2 scale.
            dist = float(score_raw)
            score = 1.0 - dist / 2.0
        elif score_raw is not None:
            score = float(score_raw)
        else:
            score = getattr(doc, "__score", 0.0)
            score = float(score) if score is not None else 0.0
        results.append(
            SearchResult(
                chunk=Chunk(
                    id=str(chunk_id),
                    text=str(text),
                    index=0,
                    embedding_model=str(embedding_model),
                    chunk_method=str(chunk_method),
                ),
                dense_score=score,
                rerank_score=None,
                retrieval_method=retrieval_method,
                rank=rank,
            )
        )
    return results


def dense_search(
    client: Any,
    *,
    index: str,
    query_embedding: list[float],
    experiment_id: str,
    embedding_model: str,
    run_id: str,
    top_k: int,
) -> list[SearchResult]:
    """KNN search with pre-filter TAG fields."""
    require_top_k(top_k)
    field = field_for_dims(len(query_embedding))
    tag_filter = _tag_filter(experiment_id, embedding_model, run_id)
    k_candidates = top_k * CANDIDATES_MULTIPLIER
    dist_attr = f"__{field}_score"
    query_str = f"{tag_filter}=>[KNN $K @{field} $BLOB AS {dist_attr}]"

    from redis.commands.search.query import Query  # type: ignore[import-not-found]

    q = (
        Query(query_str)
        .sort_by(dist_attr, asc=True)
        .paging(0, top_k)
        .return_fields("chunk_id", "text", "embedding_model", "chunk_method", dist_attr)
        .dialect(2)
    )
    result = client.ft(index).search(
        q,
        query_params={"K": k_candidates, "BLOB": _to_bytes(query_embedding)},
    )
    return _docs_to_results(result.docs, RetrievalMethod.DENSE.value, distance_field=dist_attr)


def sparse_search(
    client: Any,
    *,
    index: str,
    query_text: str,
    experiment_id: str,
    embedding_model: str,
    run_id: str,
    top_k: int,
) -> list[SearchResult]:
    """BM25 TEXT match on ``text`` field with the same TAG pre-filters."""
    require_top_k(top_k)
    tag_filter = _tag_filter(experiment_id, embedding_model, run_id)
    escaped_text = query_text.replace("\\", "\\\\").replace('"', '\\"')
    query_str = f'{tag_filter} @text:"{escaped_text}"'

    from redis.commands.search.query import Query  # type: ignore[import-not-found]

    q = (
        Query(query_str)
        .paging(0, top_k)
        .return_fields("chunk_id", "text", "embedding_model", "chunk_method")
        .dialect(2)
    )
    result = client.ft(index).search(q)
    return _docs_to_results(result.docs, RetrievalMethod.SPARSE.value)


def hybrid_search(
    client: Any,
    *,
    index: str,
    query_text: str,
    query_embedding: list[float],
    experiment_id: str,
    embedding_model: str,
    run_id: str,
    top_k: int,
) -> list[SearchResult]:
    """Client-side RRF (k=60) over dense + sparse candidate lists."""
    dense = dense_search(
        client,
        index=index,
        query_embedding=query_embedding,
        experiment_id=experiment_id,
        embedding_model=embedding_model,
        run_id=run_id,
        top_k=top_k,
    )
    sparse = sparse_search(
        client,
        index=index,
        query_text=query_text,
        experiment_id=experiment_id,
        embedding_model=embedding_model,
        run_id=run_id,
        top_k=top_k,
    )
    return rrf_fuse(dense, sparse, top_k=top_k)


def search(
    client: Any,
    *,
    index: str,
    method: RetrievalMethod,
    query_text: str,
    experiment_id: str,
    embedding_model: str,
    run_id: str,
    top_k: int,
    query_embedding: list[float] | None,
) -> list[SearchResult]:
    """Dispatch dense, sparse, or hybrid. Invalid ``top_k`` fails before I/O."""
    if method == RetrievalMethod.DENSE:
        if query_embedding is None:
            raise ValueError("query_embedding is required for dense search")
        return dense_search(
            client,
            index=index,
            query_embedding=query_embedding,
            experiment_id=experiment_id,
            embedding_model=embedding_model,
            run_id=run_id,
            top_k=top_k,
        )
    if method == RetrievalMethod.SPARSE:
        return sparse_search(
            client,
            index=index,
            query_text=query_text,
            experiment_id=experiment_id,
            embedding_model=embedding_model,
            run_id=run_id,
            top_k=top_k,
        )
    if method == RetrievalMethod.HYBRID:
        if query_embedding is None:
            raise ValueError("query_embedding is required for hybrid search")
        return hybrid_search(
            client,
            index=index,
            query_text=query_text,
            query_embedding=query_embedding,
            experiment_id=experiment_id,
            embedding_model=embedding_model,
            run_id=run_id,
            top_k=top_k,
        )
    raise ValueError(f"Unknown retrieval method: {method}")
