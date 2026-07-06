"""Aggregate raw QueryResult docs into ranked, normalized explorer data."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from server.settings import settings
from server.utils.log_throttle import info_throttled
from server.utils.logger import get_logger

logger = get_logger(__name__)


def _effective_score(result: dict) -> float:
    """Pick rerank_score if available, otherwise dense_score."""
    rerank = result.get("rerank_score")
    if rerank is not None:
        return float(rerank)
    return float(result.get("dense_score", 0.0))


def _run_config_key(run: dict) -> tuple[str, str, str, str, int, int, int, str, str, str]:
    retriever_type = run["retrieval_method"]
    retriever_model = run.get("retrieval_model") or ""
    if run.get("retrievers"):
        primary = run["retrievers"][0]
        retriever_type = primary.get("type", retriever_type)
        retriever_model = primary.get("model") or retriever_model
    return (
        run.get("database_provider", "mongodb"),
        run.get("embedding_provider", "local"),
        run["embedding_model"],
        run["chunking_method"],
        int(run["chunk_size"]),
        int(run["overlap"]),
        int(run.get("padding", 0)),
        retriever_type,
        run.get("retrieval_provider", "local"),
        retriever_model,
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
        query_results = [qr for qr in query_results if qr.get("query_text") == selected_query]

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

    info_throttled(
        logger,
        "poll:score-normalization",
        "Score normalization: min=%.2f, max=%.2f, range=%.2f, scores=%s",
        min_raw,
        max_raw,
        score_range,
        len(all_scores),
    )

    config_scores: dict[tuple, list[float]] = defaultdict(list)
    config_result_counts: dict[tuple, int] = defaultdict(int)
    # NEW: Track per-query scores for weighted averaging
    config_query_scores: dict[tuple, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    detailed: list[dict[str, Any]] = []
    queries_seen: set[str] = set()

    for qr in query_results:
        run_id = qr["run_id"]
        run = run_params.get(run_id, {})
        query_text = qr.get("query_text", "")
        queries_seen.add(query_text)

        key = (
            _run_config_key(run)
            if run
            else ("unknown", "unknown", "unknown", "unknown", 0, 0, 0, "unknown", "unknown", "")
        )

        for sr in qr.get("results", []):
            raw = _effective_score(sr)
            # Use min-max normalization to handle scores that span negative to positive ranges
            normalized = round(((raw - min_raw) / score_range) * 100)

            config_scores[key].append(normalized)
            config_result_counts[key] += 1
            # Track per-query scores for weighted averaging
            config_query_scores[key][query_text].append(normalized)

            chunk = sr.get("chunk", {})
            detailed.append(
                {
                    "score": normalized,
                    "raw_score": round(raw, 4),
                    "database_provider": run.get("database_provider", "mongodb"),
                    "embedding_provider": run.get("embedding_provider", "local"),
                    "embedding_model": chunk.get("embedding_model", run.get("embedding_model", "")),
                    "chunking_method": chunk.get("chunk_method", run.get("chunking_method", "")),
                    "chunk_size": run.get("chunk_size", 0),
                    "overlap": run.get("overlap", 0),
                    "padding": run.get("padding", 0),
                    "retrieval_method": sr.get("retrieval_method", ""),
                    "rerank_provider": run.get("retrieval_provider", "local"),
                    "retrieval_model": run.get("retrieval_model"),
                    "chunk_text": chunk.get("text", ""),
                    "query_text": query_text,
                    "run_id": run_id,
                    "rerank_score": sr.get("rerank_score"),
                    "dense_score": sr.get("dense_score", 0),
                }
            )

    detailed.sort(key=lambda d: d["score"], reverse=True)
    for i, d in enumerate(detailed, start=1):
        d["rank"] = i

    ranked_configs: list[dict[str, Any]] = []
    for key, scores in config_scores.items():
        (
            db_provider,
            emb_provider,
            model,
            chunker,
            chunk_size,
            overlap,
            padding,
            retrieval,
            rerank_provider,
            retrieval_model,
        ) = key

        # Calculate weighted average: average each query first, then average across queries
        query_scores_dict = config_query_scores[key]
        query_averages = [
            sum(query_scores) / len(query_scores)
            for query_scores in query_scores_dict.values()
            if query_scores
        ]
        weighted_avg = round(sum(query_averages) / len(query_averages)) if query_averages else 0

        ranked_configs.append(
            {
                "database_provider": db_provider,
                "embedding_provider": emb_provider,
                "embedding_model": model,
                "chunking_method": chunker,
                "chunk_size": chunk_size,
                "overlap": overlap,
                "padding": padding,
                "retrieval_method": retrieval,
                "rerank_provider": rerank_provider,
                "retrieval_model": retrieval_model or None,
                "max_score": max(scores) if scores else 0,
                "avg_score": round(sum(scores) / len(scores))
                if scores
                else 0,  # Unweighted (chunk-level)
                "query_avg_score": weighted_avg,  # NEW: Weighted (query-level)
                "result_count": config_result_counts[key],
            }
        )

    # Sort by: max_score DESC, then avg_score (configurable) DESC,
    # then chunk_size ASC, then overlap ASC, then padding ASC
    # Tiebreaker rationale:
    #   1. max_score: primary quality metric
    #   2. avg_score: consistency (configurable: query_avg or chunk_avg)
    #      - query_avg (default): weighted per-query average
    #        (fairer — each query contributes equally)
    #      - chunk_avg (legacy): unweighted chunk-level average
    #        (queries with more results dominate)
    #   3. chunk_size: smaller = faster processing + less storage
    #   4. overlap: smaller = fewer duplicate chunks
    #   5. padding: smaller = less merge-forward padding

    # Choose which avg metric to use for tiebreaking based on TIEBREAKER_METRIC setting
    use_query_avg = settings.tiebreaker_metric == "query_avg"
    avg_metric_key = "query_avg_score" if use_query_avg else "avg_score"

    logger.info(
        "Sorting configs with tiebreaker_metric=%s (using %s)",
        settings.tiebreaker_metric,
        avg_metric_key,
    )

    ranked_configs.sort(
        key=lambda c: (
            -c["max_score"],  # Higher is better (negate for DESC)
            -c[avg_metric_key],  # Higher is better (configurable metric)
            c["chunk_size"],  # Lower is better (ASC)
            c["overlap"],  # Lower is better (ASC)
            c["padding"],  # Lower is better (ASC)
        )
    )
    for i, c in enumerate(ranked_configs, start=1):
        c["rank"] = i

    best = ranked_configs[0] if ranked_configs else None

    # Add tie metadata: count how many configs share the same max_score as #1
    if best and ranked_configs:
        best_max = best["max_score"]
        tied_count = sum(1 for c in ranked_configs if c["max_score"] == best_max)
        best["tied_count"] = tied_count  # Add to best_params for UI explanation

    unique_queries = sorted(queries_seen)

    return {
        "query_count": len(unique_queries),
        "total_matches": len(detailed),
        "queries": unique_queries,
        "best_params": best,
        "ranked_configs": ranked_configs,
        "detailed_results": detailed,
    }
