"""Aggregate raw QueryResult docs into ranked, normalized explorer data."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, NamedTuple

from server.settings import settings
from server.utils.log_throttle import info_throttled
from server.utils.logger import get_logger

logger = get_logger(__name__)


class RunConfigKey(NamedTuple):
    """Identity of one swept configuration.

    A ``NamedTuple`` (not a dataclass) on purpose: ``server.core.compare`` and
    ``scripts/walkthru/export_walkthru_results.py`` slice this key positionally
    and hash it as a JSON list into persisted group ids, so the tuple shape and
    element order are part of the published contract.
    """

    database_provider: str
    embedding_provider: str
    embedding_model: str
    chunking_method: str
    chunk_size: int
    overlap: int
    padding: int
    retrieval_method: str
    retrieval_provider: str
    retrieval_model: str

    @classmethod
    def unknown(cls) -> RunConfigKey:
        """Key used when a result references a run that is no longer present."""
        return cls(
            database_provider="unknown",
            embedding_provider="unknown",
            embedding_model="unknown",
            chunking_method="unknown",
            chunk_size=0,
            overlap=0,
            padding=0,
            retrieval_method="unknown",
            retrieval_provider="unknown",
            retrieval_model="",
        )


class _ScoreScale(NamedTuple):
    """Min-max normalization of raw scores onto a 0-100 range."""

    min_raw: float
    span: float

    def normalize(self, raw: float) -> int:
        return round(((raw - self.min_raw) / self.span) * 100)


@dataclass
class _ConfigAggregate:
    """Running totals for one configuration key."""

    scores: list[int] = field(default_factory=list)
    result_count: int = 0
    query_scores: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))

    def add(self, query_text: str, normalized: int) -> None:
        self.scores.append(normalized)
        self.result_count += 1
        self.query_scores[query_text].append(normalized)

    def weighted_average(self) -> int:
        """Average each query first, then average across queries."""
        query_averages = [
            sum(scores) / len(scores) for scores in self.query_scores.values() if scores
        ]
        return round(sum(query_averages) / len(query_averages)) if query_averages else 0

    def chunk_average(self) -> int:
        return round(sum(self.scores) / len(self.scores)) if self.scores else 0


def _effective_score(result: dict) -> float:
    """Pick rerank_score if available, otherwise dense_score."""
    rerank = result.get("rerank_score")
    if rerank is not None:
        return float(rerank)
    return float(result.get("dense_score", 0.0))


def _run_config_key(run: dict) -> RunConfigKey:
    retriever_type = run["retrieval_method"]
    retriever_model = run.get("retrieval_model") or ""
    if run.get("retrievers"):
        primary = run["retrievers"][0]
        retriever_type = primary.get("type", retriever_type)
        retriever_model = primary.get("model") or retriever_model
    return RunConfigKey(
        database_provider=run.get("database_provider", settings.default_database_provider()),
        embedding_provider=run.get("embedding_provider", "local"),
        embedding_model=run["embedding_model"],
        chunking_method=run["chunking_method"],
        chunk_size=int(run["chunk_size"]),
        overlap=int(run["overlap"]),
        padding=int(run.get("padding", 0)),
        retrieval_method=retriever_type,
        retrieval_provider=run.get("retrieval_provider", "local"),
        retrieval_model=retriever_model,
    )


def _build_score_scale(query_results: list[dict[str, Any]]) -> _ScoreScale:
    """Derive the 0-100 normalization window from every raw score present.

    Rerank scores can be negative, so min-max normalization is used; a
    degenerate (zero) range falls back to a span of 1.0.
    """
    all_scores = [_effective_score(sr) for qr in query_results for sr in qr.get("results", [])]
    min_raw = min(all_scores) if all_scores else 0.0
    max_raw = max(all_scores) if all_scores else 1.0
    span = (max_raw - min_raw) or 1.0

    info_throttled(
        logger,
        "poll:score-normalization",
        "Score normalization: min=%.2f, max=%.2f, range=%.2f, scores=%s",
        min_raw,
        max_raw,
        span,
        len(all_scores),
    )
    return _ScoreScale(min_raw=min_raw, span=span)


def _detail_row(
    search_result: dict[str, Any],
    run: dict[str, Any],
    query_text: str,
    run_id: str,
    raw: float,
    normalized: int,
) -> dict[str, Any]:
    """Project one search result into the detailed_results shape."""
    chunk = search_result.get("chunk", {})
    return {
        "score": normalized,
        "raw_score": round(raw, 4),
        "database_provider": run.get("database_provider", settings.default_database_provider()),
        "embedding_provider": run.get("embedding_provider", "local"),
        "embedding_model": chunk.get("embedding_model", run.get("embedding_model", "")),
        "chunking_method": chunk.get("chunk_method", run.get("chunking_method", "")),
        "chunk_size": run.get("chunk_size", 0),
        "overlap": run.get("overlap", 0),
        "padding": run.get("padding", 0),
        "retrieval_method": search_result.get("retrieval_method", ""),
        "rerank_provider": run.get("retrieval_provider", "local"),
        "retrieval_model": run.get("retrieval_model"),
        "chunk_text": chunk.get("text", ""),
        "query_text": query_text,
        "run_id": run_id,
        "rerank_score": search_result.get("rerank_score"),
        "dense_score": search_result.get("dense_score", 0),
    }


class _Collected(NamedTuple):
    """Everything one pass over the result documents produces."""

    aggregates: dict[RunConfigKey, _ConfigAggregate]
    detailed: list[dict[str, Any]]
    queries_seen: set[str]


def _collect(
    query_results: list[dict[str, Any]],
    run_params: dict[str, dict[str, Any]],
    scale: _ScoreScale,
) -> _Collected:
    """Group normalized scores by configuration and project detail rows."""
    aggregates: dict[RunConfigKey, _ConfigAggregate] = defaultdict(_ConfigAggregate)
    detailed: list[dict[str, Any]] = []
    queries_seen: set[str] = set()

    for qr in query_results:
        run_id = qr["run_id"]
        run = run_params.get(run_id, {})
        query_text = qr.get("query_text", "")
        queries_seen.add(query_text)
        key = _run_config_key(run) if run else RunConfigKey.unknown()

        for sr in qr.get("results", []):
            raw = _effective_score(sr)
            normalized = scale.normalize(raw)
            aggregates[key].add(query_text, normalized)
            detailed.append(_detail_row(sr, run, query_text, run_id, raw, normalized))

    return _Collected(aggregates=aggregates, detailed=detailed, queries_seen=queries_seen)


def _ranked_config(key: RunConfigKey, aggregate: _ConfigAggregate) -> dict[str, Any]:
    """Project one grouped configuration into the ranked_configs shape."""
    return {
        "database_provider": key.database_provider,
        "embedding_provider": key.embedding_provider,
        "embedding_model": key.embedding_model,
        "chunking_method": key.chunking_method,
        "chunk_size": key.chunk_size,
        "overlap": key.overlap,
        "padding": key.padding,
        "retrieval_method": key.retrieval_method,
        "rerank_provider": key.retrieval_provider,
        "retrieval_model": key.retrieval_model or None,
        "max_score": max(aggregate.scores) if aggregate.scores else 0,
        "avg_score": aggregate.chunk_average(),  # Unweighted (chunk-level)
        "query_avg_score": aggregate.weighted_average(),  # Weighted (query-level)
        "result_count": aggregate.result_count,
    }


def _rank_detailed(detailed: list[dict[str, Any]]) -> None:
    """Sort detail rows by score DESC (stable) and stamp 1-based ranks."""
    detailed.sort(key=lambda d: d["score"], reverse=True)
    for position, row in enumerate(detailed, start=1):
        row["rank"] = position


def _rank_configs(ranked_configs: list[dict[str, Any]]) -> None:
    """Sort configurations best-first and stamp 1-based ranks.

    Order: max_score DESC, then the configured avg metric DESC, then
    chunk_size ASC, overlap ASC, padding ASC.
    Tiebreaker rationale:
      1. max_score: primary quality metric
      2. avg_score: consistency (configurable: query_avg or chunk_avg)
         - query_avg (default): weighted per-query average
           (fairer — each query contributes equally)
         - chunk_avg (legacy): unweighted chunk-level average
           (queries with more results dominate)
      3. chunk_size: smaller = faster processing + less storage
      4. overlap: smaller = fewer duplicate chunks
      5. padding: smaller = less merge-forward padding
    """
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
    for position, config in enumerate(ranked_configs, start=1):
        config["rank"] = position


def _best_config(ranked_configs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the winner, annotated with how many configs share its max_score."""
    if not ranked_configs:
        return None
    best = ranked_configs[0]
    best_max = best["max_score"]
    # Tie metadata for the UI explanation
    best["tied_count"] = sum(1 for c in ranked_configs if c["max_score"] == best_max)
    return best


def analyze_results(
    query_results: list[dict[str, Any]],
    run_statuses: list[dict[str, Any]],
    selected_query: str | None = None,
) -> dict[str, Any]:
    """Build the explore response from storage-backend result documents.

    Args:
        query_results: Records from the ``results`` collection or table.
        run_statuses: Records from the ``run_status`` collection or table.
        selected_query: optional query_text filter; None means all queries.

    Returns:
        Dict matching the ExploreResponse shape.
    """
    run_params = {r["run_id"]: r for r in run_statuses}

    if selected_query:
        query_results = [qr for qr in query_results if qr.get("query_text") == selected_query]

    collected = _collect(query_results, run_params, _build_score_scale(query_results))
    detailed = collected.detailed
    _rank_detailed(detailed)

    ranked_configs = [
        _ranked_config(key, aggregate) for key, aggregate in collected.aggregates.items()
    ]
    _rank_configs(ranked_configs)

    unique_queries = sorted(collected.queries_seen)

    return {
        "query_count": len(unique_queries),
        "total_matches": len(detailed),
        "queries": unique_queries,
        "best_params": _best_config(ranked_configs),
        "ranked_configs": ranked_configs,
        "detailed_results": detailed,
    }
