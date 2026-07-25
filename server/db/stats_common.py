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
) -> dict:
    """Build the per-experiment db-stats dict from already-queried aggregates."""
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
        "unique_queries": unique_queries,
        "run_breakdown": run_breakdown,
    }


def vector_db_group_key(database_provider: str, cluster_host: str | None) -> str:
    return f"{database_provider}:{cluster_host or 'unknown'}"


def new_vector_db_group(group_key: str, stats: dict) -> dict:
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
