"""Aggregate raw QueryResult docs into ranked, normalized explorer data."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from server.utils.logger import get_logger

logger = get_logger(__name__)


def _effective_score(result: dict) -> float:
    """Pick rerank_score if available, otherwise dense_score."""
    rerank = result.get("rerank_score")
    if rerank is not None:
        return float(rerank)
    return float(result.get("dense_score", 0.0))


def _run_config_key(run: dict) -> tuple[str, str, str, str, int, int, str, str]:
    return (
        run.get("database_provider", "mongodb"),
        run.get("embedding_provider", "local"),
        run["embedding_model"],
        run["chunking_method"],
        int(run["chunk_size"]),
        int(run["overlap"]),
        run["retrieval_method"],
        run.get("rerank_provider", "local"),
    )


def analyze_results(
    query_results: list[dict[str, Any]],
    run_statuses: list[dict[str, Any]],
    selected_query: str | None = None,
) -> dict[str, Any]:
    """Build the explore response from raw MongoDB documents.

    Args:
        query_results: docs from the ``results`` collection.
        run_statuses: docs from the ``run_status`` collection.
        selected_query: optional query_text filter; None means all queries.

    Returns:
        Dict matching the ExploreResponse shape.
    """
    run_params = {r["run_id"]: r for r in run_statuses}

    if selected_query:
        query_results = [
            qr for qr in query_results if qr.get("query_text") == selected_query
        ]

    all_scores: list[float] = []
    for qr in query_results:
        for sr in qr.get("results", []):
            all_scores.append(_effective_score(sr))

    # Normalize scores to 0-100 range
    # For rerank scores (which can be negative), we need min-max normalization
    # For dense scores (0-1 range), max normalization is fine
    min_raw = min(all_scores) if all_scores else 0.0
    max_raw = max(all_scores) if all_scores else 1.0
    score_range = max_raw - min_raw

    if score_range == 0:
        score_range = 1.0

    logger.info(f"Score normalization: min={min_raw:.2f}, max={max_raw:.2f}, range={score_range:.2f}, scores={len(all_scores)}")

    config_scores: dict[tuple, list[float]] = defaultdict(list)
    config_result_counts: dict[tuple, int] = defaultdict(int)
    detailed: list[dict[str, Any]] = []
    queries_seen: set[str] = set()

    for qr in query_results:
        run_id = qr["run_id"]
        run = run_params.get(run_id, {})
        query_text = qr.get("query_text", "")
        queries_seen.add(query_text)

        key = _run_config_key(run) if run else ("unknown", "unknown", 0, 0, "unknown")

        for sr in qr.get("results", []):
            raw = _effective_score(sr)
            # Use min-max normalization to handle scores that span negative to positive ranges
            normalized = round(((raw - min_raw) / score_range) * 100)

            config_scores[key].append(normalized)
            config_result_counts[key] += 1

            chunk = sr.get("chunk", {})
            detailed.append({
                "score": normalized,
                "raw_score": round(raw, 4),
                "database_provider": run.get("database_provider", "mongodb"),
                "embedding_provider": run.get("embedding_provider", "local"),
                "embedding_model": chunk.get("embedding_model", run.get("embedding_model", "")),
                "chunking_method": chunk.get("chunk_method", run.get("chunking_method", "")),
                "chunk_size": run.get("chunk_size", 0),
                "overlap": run.get("overlap", 0),
                "retrieval_method": sr.get("retrieval_method", ""),
                "rerank_provider": run.get("rerank_provider", "local"),
                "chunk_text": chunk.get("text", ""),
                "query_text": query_text,
                "run_id": run_id,
                "rerank_score": sr.get("rerank_score"),
                "dense_score": sr.get("dense_score", 0),
            })

    detailed.sort(key=lambda d: d["score"], reverse=True)
    for i, d in enumerate(detailed, start=1):
        d["rank"] = i

    ranked_configs: list[dict[str, Any]] = []
    for key, scores in config_scores.items():
        db_provider, emb_provider, model, chunker, chunk_size, overlap, retrieval, rerank_provider = key
        ranked_configs.append({
            "database_provider": db_provider,
            "embedding_provider": emb_provider,
            "embedding_model": model,
            "chunking_method": chunker,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "retrieval_method": retrieval,
            "rerank_provider": rerank_provider,
            "max_score": max(scores) if scores else 0,
            "avg_score": round(sum(scores) / len(scores)) if scores else 0,
            "result_count": config_result_counts[key],
        })

    ranked_configs.sort(key=lambda c: c["max_score"], reverse=True)
    for i, c in enumerate(ranked_configs, start=1):
        c["rank"] = i

    best = ranked_configs[0] if ranked_configs else None

    unique_queries = sorted(queries_seen)

    return {
        "query_count": len(unique_queries),
        "total_matches": len(detailed),
        "queries": unique_queries,
        "best_params": best,
        "ranked_configs": ranked_configs,
        "detailed_results": detailed,
    }
