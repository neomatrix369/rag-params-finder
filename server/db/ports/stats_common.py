"""Backend-agnostic db-stats assembly shared by the Mongo and Postgres adapters.

Only pure functions live here: given already-queried counts, produce the dict
shapes documented on ``StorageBackend.get_experiment_db_stats`` and
``StorageBackend.get_vector_db_stats_grouped``. Each adapter supplies the
backend-specific identity (collection/table name, host, index names) and runs
its own aggregation queries.
"""

from __future__ import annotations

from typing import Any

from server.core.model_registry import EMBEDDING_MODELS, get_dimensions
from server.models.config import (
    normalize_stats_database_provider as _normalize_stats_database_provider,
)

_METADATA_BYTES_PER_CHUNK = 500
_BYTES_PER_FLOAT32 = 4


def bytes_to_mb(value: float) -> float:
    return round(value / (1024 * 1024), 2)


def storage_breakdown_mb(
    total_chunks: int, embedding_models: list[str]
) -> tuple[float, float, float]:
    """Estimate (embedding_mb, metadata_mb, total_mb) for a set of chunks."""
    if total_chunks == 0:
        return 0.0, 0.0, 0.0
    dims = [get_dimensions(model) for model in embedding_models if model in EMBEDDING_MODELS]
    if not dims:
        return 0.0, 0.0, 0.0
    avg_dim = sum(dims) / len(dims)
    embedding_bytes = total_chunks * int(avg_dim) * _BYTES_PER_FLOAT32
    metadata_bytes = total_chunks * _METADATA_BYTES_PER_CHUNK
    return (
        bytes_to_mb(embedding_bytes),
        bytes_to_mb(metadata_bytes),
        bytes_to_mb(embedding_bytes + metadata_bytes),
    )


def embedding_dimensions_for(embedding_models: list[str]) -> list[int]:
    return sorted({get_dimensions(m) for m in embedding_models if m in EMBEDDING_MODELS})


def retrieval_methods_for_experiment(experiment: dict | None) -> list[str]:
    """Read retrieval methods from sweep_summary, falling back to raw config."""
    if not experiment:
        return []
    sweep = experiment.get("sweep_summary") or {}
    methods = sweep.get("retrieval_methods")
    if isinstance(methods, list):
        return [str(method) for method in methods]
    config = experiment.get("config") or {}
    retrieval = config.get("retrieval") or {}
    config_methods = retrieval.get("methods")
    if isinstance(config_methods, list):
        return [str(method) for method in config_methods]
    return []


def golden_query_facts(
    experiment: dict | None, results_per_run: list[int]
) -> tuple[int | None, str | None, int]:
    """Return ``(golden_queries, source, partial_runs)``.

    A golden record is one evaluation query. The count is persisted lazily on
    ``sweep_summary.golden_queries`` (source ``config``); older experiments fall
    back to the largest per-run result-row count (source ``max_per_run``, an
    inference). ``partial_runs`` counts runs with fewer rows than the golden count.
    """
    stored = ((experiment or {}).get("sweep_summary") or {}).get("golden_queries")
    # An empty dataset stores 0: source stays 'config' and no run is partial.
    if isinstance(stored, int) and not isinstance(stored, bool) and stored >= 0:
        return stored, "config", sum(1 for rows in results_per_run if rows < stored)
    inferred = max(results_per_run, default=0)
    if inferred > 0:
        return inferred, "max_per_run", sum(1 for rows in results_per_run if rows < inferred)
    return None, None, 0


def assemble_experiment_db_stats(
    experiment: dict | None,
    *,
    database_provider: str,
    collection_name: str,
    cluster_host: str | None,
    index_names: list[str],
    total_chunks: int,
    embedding_models: list[str],
    chunking_breakdown: dict[str, int],
    total_results: int,
    unique_queries: int,
    runs_with_data: int,
    run_breakdown: list[dict],
    results_per_run: list[int] | None = None,
    results_known: bool = True,
) -> dict:
    """Build the per-experiment db-stats dict from already-queried aggregates.

    ``results_per_run`` is the result-row count of every run that has results
    (adapters supply it from their own ``GROUP BY run_id``); it feeds
    ``result_runs`` / ``golden_queries`` / ``partial_runs``. Vector stores that
    hold no results (Redis, ES) omit it.
    """
    per_run = sorted(results_per_run or [])
    golden, golden_source, partial_runs = golden_query_facts(experiment, per_run)
    result_runs: int | None = len(per_run)
    partial: int | None = partial_runs
    if not results_known:
        # The optional per-run fetch failed: report "unknown" (None), never a false 0.
        result_runs, golden, golden_source, partial = None, None, None, None
    avg_chunks_per_run = round(total_chunks / runs_with_data, 1) if runs_with_data else 0.0
    embedding_mb, metadata_mb, total_mb = storage_breakdown_mb(total_chunks, embedding_models)

    return {
        "database_provider": database_provider,
        "collection_name": collection_name,
        "cluster_host": cluster_host,
        "total_chunks": total_chunks,
        "unique_documents": len((experiment or {}).get("data_paths") or []),
        "embedding_models": embedding_models,
        "embedding_dimensions": embedding_dimensions_for(embedding_models),
        "index_names": index_names,
        "retrieval_methods": retrieval_methods_for_experiment(experiment),
        "chunking_methods": sorted(chunking_breakdown.keys()),
        "chunking_breakdown": chunking_breakdown,
        "estimated_storage_mb": total_mb,
        "estimated_embedding_mb": embedding_mb,
        "estimated_metadata_mb": metadata_mb,
        "runs_with_data": runs_with_data,
        "avg_chunks_per_run": avg_chunks_per_run,
        "total_results": total_results,
        # NB: query_id is a uuid4 per query per run, so unique_queries equals
        # total_results. It is not the golden-record count; see golden_queries.
        "unique_queries": unique_queries,
        # Runs with >= 1 result row. A run that died before its first query has no
        # rows, so it is neither counted here nor in partial_runs.
        "result_runs": result_runs,
        "golden_queries": golden,
        "golden_queries_source": golden_source,
        # Runs with fewer rows than golden_queries. A run still in flight counts as
        # partial, so read it as "currently below golden" unless the experiment is
        # terminal. golden_queries is write-once: it goes stale if queries_file
        # changes between pause and resume.
        "partial_runs": partial,
        "run_breakdown": run_breakdown,
    }


def normalize_stats_database_provider(value: str | None, *, fallback: str) -> str:
    """Canonical engine label for stats (never emit ``supabase``).

    Thin re-export (Slice 49A Stream 6): the alias table lives in
    ``server.models.config`` alongside ``normalize_database_provider`` — one
    owner for provider-label normalisation — kept importable from here so
    ``mongo_stats.py`` / ``postgres_stats.py`` don't need an import-path
    change.
    """
    return _normalize_stats_database_provider(value, fallback=fallback)


def resolve_experiment_storage_mode(
    experiment: dict | None,
    *,
    fallback_mode: str,
) -> str:
    """Prefer persisted experiment storage_mode; else live/runtime fallback."""
    if not experiment:
        return fallback_mode
    top = experiment.get("storage_mode")
    if isinstance(top, str) and top.strip():
        return top.strip()
    sweep = experiment.get("sweep_summary") or {}
    nested = sweep.get("storage_mode")
    if isinstance(nested, str) and nested.strip():
        return nested.strip()
    return fallback_mode


def vector_db_group_key(storage_mode: str, cluster_host: str | None) -> str:
    """Group key for vector-db-stats — ``storage_mode:<host>`` (Slice 37).

    Prefer the four-value ``storage_mode`` over ``database_provider`` so product
    labels (``supabase``) never appear in ``vector_db_id``.
    """
    return f"{storage_mode}:{cluster_host or 'unknown'}"


def new_vector_db_group(group_key: str, stats: dict) -> dict:
    """Empty group for the grouped view.

    ``total_result_runs`` / ``golden_queries_min`` / ``golden_queries_max`` (like
    ``total_results``) only populate when the vector store and run state are the
    same backend: the grouped view has no run-state overlay (owner decision). The
    single-experiment detail view does overlay run-state facts for every backend.
    """
    return {
        "vector_db_id": group_key,
        "database_provider": stats["database_provider"],
        "collection_name": stats["collection_name"],
        "cluster_host": stats["cluster_host"],
        "index_names": [],
        "embedding_dimensions": [],
        "totals": {
            "experiment_count": 0,
            "total_chunks": 0,
            "total_results": 0,
            "total_result_runs": 0,
            "golden_queries_min": None,
            "golden_queries_max": None,
            "estimated_storage_mb": 0.0,
            "estimated_embedding_mb": 0.0,
            "estimated_metadata_mb": 0.0,
        },
        "experiments": [],
    }


def merge_group_totals(group: dict, stats: dict) -> None:
    totals = group["totals"]
    totals["experiment_count"] += 1
    totals["total_chunks"] += stats["total_chunks"]
    totals["total_results"] += stats["total_results"]
    totals["total_result_runs"] += stats.get("result_runs") or 0  # None (unknown) is skipped
    golden = stats.get("golden_queries")
    if golden is not None:
        low, high = totals["golden_queries_min"], totals["golden_queries_max"]
        totals["golden_queries_min"] = golden if low is None else min(low, golden)
        totals["golden_queries_max"] = golden if high is None else max(high, golden)
    for key in ("estimated_storage_mb", "estimated_embedding_mb", "estimated_metadata_mb"):
        totals[key] = round(totals[key] + stats[key], 2)
    group["index_names"] = sorted(set(group["index_names"]) | set(stats["index_names"]))
    group["embedding_dimensions"] = sorted(
        set(group["embedding_dimensions"]) | set(stats["embedding_dimensions"])
    )


def experiment_summary_row(experiment: dict, experiment_id: str, stats: dict) -> dict:
    """Flatten an experiment plus its stats into a grouped-response row."""
    created_at = experiment.get("created_at")
    created_at_value: Any = (
        created_at.isoformat()
        if created_at is not None and hasattr(created_at, "isoformat")
        else created_at
    )
    return {
        "experiment_id": experiment_id,
        "experiment_name": experiment.get("experiment_name", ""),
        "status": experiment.get("status", ""),
        "created_at": created_at_value,
        **stats,
    }


def finalize_groups(groups: dict[str, dict], cluster_storage: dict) -> list[dict]:
    """Attach backend capacity fields and apply the response sort order."""
    grouped = list(groups.values())
    for group in grouped:
        group["totals"].update(cluster_storage)
        group["experiments"].sort(key=lambda row: row.get("created_at") or "", reverse=True)
    grouped.sort(key=lambda row: row["totals"]["total_chunks"], reverse=True)
    return grouped
