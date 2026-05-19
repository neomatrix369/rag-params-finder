"""Synchronous Mongo helpers for experiments API (run inside asyncio.to_thread).

PyMongo blocks the asyncio event loop if called directly from async endpoints.
Keeping I/O here isolates blocking work into threadpool tasks.
"""

from datetime import datetime

from server.db.atlas import (
    EXPERIMENTS_COLLECTION,
    RESULTS_COLLECTION,
    RUN_STATUS_COLLECTION,
    get_collection,
)
from server.models.enums import ExperimentStatus


def mongo_list_all_experiment_docs():
    cursor = get_collection(EXPERIMENTS_COLLECTION).find({}, {"_id": 0}).sort("created_at", -1)
    return list(cursor)


def mongo_find_experiment_with_runs(experiment_id: str):
    experiment = get_collection(EXPERIMENTS_COLLECTION).find_one(
        {"experiment_id": experiment_id}, {"_id": 0}
    )
    if not experiment:
        return None
    runs_cursor = (
        get_collection(RUN_STATUS_COLLECTION)
        .find({"experiment_id": experiment_id}, {"_id": 0})
        .sort("created_at", 1)
    )
    experiment["runs"] = list(runs_cursor)
    return experiment


def mongo_insert_experiment_doc(experiment_doc: dict):
    get_collection(EXPERIMENTS_COLLECTION).insert_one(experiment_doc)


def mongo_list_results_for_experiment(experiment_id: str):
    return list(
        get_collection(RESULTS_COLLECTION).find({"experiment_id": experiment_id}, {"_id": 0})
    )


def mongo_load_explore_source(experiment_id: str):
    experiment = get_collection(EXPERIMENTS_COLLECTION).find_one({"experiment_id": experiment_id})
    if not experiment:
        return None, [], []
    query_results = list(
        get_collection(RESULTS_COLLECTION).find({"experiment_id": experiment_id}, {"_id": 0})
    )
    run_statuses = list(
        get_collection(RUN_STATUS_COLLECTION).find({"experiment_id": experiment_id}, {"_id": 0})
    )
    return experiment, query_results, run_statuses


def mongo_find_experiment_by_id(experiment_id: str):
    return get_collection(EXPERIMENTS_COLLECTION).find_one({"experiment_id": experiment_id})


def mongo_mark_experiment_cancelled_now(experiment_id: str):
    get_collection(EXPERIMENTS_COLLECTION).update_one(
        {"_id": experiment_id},
        {"$set": {"status": ExperimentStatus.CANCELLED, "completed_at": datetime.utcnow()}},
    )


def mongo_delete_experiment_data(experiment_id: str) -> dict[str, int]:
    """Delete all data for an experiment across all collections.

    Returns dict with counts of deleted documents from each collection.
    """
    from server.db.atlas import CHUNKS_COLLECTION

    chunks_deleted = (
        get_collection(CHUNKS_COLLECTION)
        .delete_many({"experiment_id": experiment_id})
        .deleted_count
    )

    results_deleted = (
        get_collection(RESULTS_COLLECTION)
        .delete_many({"experiment_id": experiment_id})
        .deleted_count
    )

    run_status_deleted = (
        get_collection(RUN_STATUS_COLLECTION)
        .delete_many({"experiment_id": experiment_id})
        .deleted_count
    )

    experiment_deleted = (
        get_collection(EXPERIMENTS_COLLECTION)
        .delete_one({"experiment_id": experiment_id})
        .deleted_count
    )

    return {
        "experiments": experiment_deleted,
        "run_status": run_status_deleted,
        "chunks": chunks_deleted,
        "results": results_deleted,
    }


def _retrieval_methods_for_experiment(experiment: dict | None) -> list[str]:
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


def _mongodb_cluster_hint() -> str | None:
    from server.settings import settings

    uri = settings.mongodb_uri.strip()
    if not uri:
        return None
    without_scheme = uri.split("://", 1)[-1]
    host_part = without_scheme.split("@")[-1].split("/")[0].split("?")[0]
    return host_part or None


def _mongodb_cluster_storage_mb() -> dict[str, float | None]:
    """Actual database footprint from MongoDB dbStats (data + indexes)."""
    from server.core.atlas_storage import resolve_storage_limit_mb
    from server.db.atlas import get_database

    db = get_database()
    stats = db.command("dbStats")
    data_bytes = float(stats.get("dataSize") or 0)
    index_bytes = float(stats.get("indexSize") or 0)
    total_bytes = float(stats.get("totalSize") or data_bytes + index_bytes)
    used_mb = _bytes_to_mb(total_bytes)

    limit_mb = resolve_storage_limit_mb()
    has_quota = limit_mb is not None and limit_mb > 0
    quota_mb = limit_mb if has_quota else None
    return {
        "database_used_mb": used_mb,
        "database_data_mb": _bytes_to_mb(data_bytes),
        "database_index_mb": _bytes_to_mb(index_bytes),
        "database_storage_limit_mb": quota_mb,
        "database_free_mb": round(max(0.0, quota_mb - used_mb), 2)
        if quota_mb is not None
        else None,
    }


def _bytes_to_mb(value: float) -> float:
    return round(value / (1024 * 1024), 2)


def _storage_breakdown_mb(
    total_chunks: int, embedding_models: list[str]
) -> tuple[float, float, float]:
    if total_chunks == 0:
        return 0.0, 0.0, 0.0
    from server.core.model_registry import EMBEDDING_MODELS, get_dimensions

    dims = [get_dimensions(model) for model in embedding_models if model in EMBEDDING_MODELS]
    if not dims:
        return 0.0, 0.0, 0.0
    avg_dim = sum(dims) / len(dims)
    embedding_bytes = total_chunks * int(avg_dim) * 4
    metadata_bytes = total_chunks * 500
    total_bytes = embedding_bytes + metadata_bytes
    return (
        _bytes_to_mb(embedding_bytes),
        _bytes_to_mb(metadata_bytes),
        _bytes_to_mb(total_bytes),
    )


def _estimate_storage_mb(total_chunks: int, embedding_models: list[str]) -> float:
    _, _, total_mb = _storage_breakdown_mb(total_chunks, embedding_models)
    return total_mb


def _chunking_breakdown(chunks_coll, experiment_id: str) -> dict[str, int]:
    pipeline = [
        {"$match": {"experiment_id": experiment_id}},
        {"$group": {"_id": "$chunk_method", "count": {"$sum": 1}}},
    ]
    breakdown: dict[str, int] = {}
    for row in chunks_coll.aggregate(pipeline):
        method = row.get("_id")
        if method:
            breakdown[str(method)] = int(row["count"])
    return breakdown


def _document_counts_by_run_id(collection, experiment_id: str) -> dict[str, int]:
    pipeline = [
        {"$match": {"experiment_id": experiment_id}},
        {"$group": {"_id": "$run_id", "count": {"$sum": 1}}},
    ]
    counts: dict[str, int] = {}
    for row in collection.aggregate(pipeline):
        run_id = row.get("_id")
        if run_id:
            counts[str(run_id)] = int(row["count"])
    return counts


def _run_breakdown_for_experiment(chunks_coll, results_coll, experiment_id: str) -> list[dict]:
    chunk_counts = _document_counts_by_run_id(chunks_coll, experiment_id)
    result_counts = _document_counts_by_run_id(results_coll, experiment_id)
    run_ids = chunks_coll.distinct("run_id", {"experiment_id": experiment_id})
    breakdown: list[dict] = []
    for run_id in run_ids:
        key = str(run_id)
        run_chunks = chunk_counts.get(key, 0)
        run_results = result_counts.get(key, 0)
        if run_chunks > 0 or run_results > 0:
            breakdown.append({"run_id": run_id, "chunks": run_chunks, "results": run_results})
    return breakdown


def mongo_get_experiment_db_stats(experiment_id: str) -> dict:
    """Get vector database statistics for an experiment."""
    from server.core.model_registry import EMBEDDING_MODELS, get_dimensions, get_index_name
    from server.db.atlas import CHUNKS_COLLECTION
    from server.db.indexes import TEXT_SEARCH_INDEX_NAME

    experiment = get_collection(EXPERIMENTS_COLLECTION).find_one(
        {"experiment_id": experiment_id},
        {"data_paths": 1, "sweep_summary": 1, "config": 1},
    )
    chunks_coll = get_collection(CHUNKS_COLLECTION)
    results_coll = get_collection(RESULTS_COLLECTION)

    total_chunks = chunks_coll.count_documents({"experiment_id": experiment_id})
    embedding_models = chunks_coll.distinct("embedding_model", {"experiment_id": experiment_id})

    embedding_dimensions = sorted(
        {get_dimensions(model) for model in embedding_models if model in EMBEDDING_MODELS}
    )

    unique_documents = len((experiment or {}).get("data_paths") or [])
    total_results = results_coll.count_documents({"experiment_id": experiment_id})
    unique_queries = len(results_coll.distinct("query_id", {"experiment_id": experiment_id}))

    run_breakdown = _run_breakdown_for_experiment(chunks_coll, results_coll, experiment_id)

    index_names = sorted(
        {get_index_name(model) for model in embedding_models if model in EMBEDDING_MODELS}
    )
    retrieval_methods = _retrieval_methods_for_experiment(experiment)
    if any(method in {"sparse", "hybrid"} for method in retrieval_methods):
        index_names.append(TEXT_SEARCH_INDEX_NAME)
        index_names = sorted(set(index_names))

    runs_with_data = len(run_breakdown)
    avg_chunks_per_run = round(total_chunks / runs_with_data, 1) if runs_with_data else 0.0
    embedding_mb, metadata_mb, total_mb = _storage_breakdown_mb(total_chunks, embedding_models)
    chunking_breakdown = _chunking_breakdown(chunks_coll, experiment_id)
    sweep = (experiment or {}).get("sweep_summary") or {}

    return {
        "database_provider": str(sweep.get("database_provider") or "mongodb"),
        "collection_name": CHUNKS_COLLECTION,
        "cluster_host": _mongodb_cluster_hint(),
        "total_chunks": total_chunks,
        "unique_documents": unique_documents,
        "embedding_models": embedding_models,
        "embedding_dimensions": embedding_dimensions,
        "index_names": index_names,
        "retrieval_methods": retrieval_methods,
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


def _vector_db_group_key(database_provider: str, cluster_host: str | None) -> str:
    return f"{database_provider}:{cluster_host or 'unknown'}"


def _merge_group_totals(group: dict, stats: dict) -> None:
    totals = group["totals"]
    totals["experiment_count"] += 1
    totals["total_chunks"] += stats["total_chunks"]
    totals["total_results"] += stats["total_results"]
    totals["estimated_storage_mb"] = round(
        totals["estimated_storage_mb"] + stats["estimated_storage_mb"], 2
    )
    totals["estimated_embedding_mb"] = round(
        totals["estimated_embedding_mb"] + stats["estimated_embedding_mb"], 2
    )
    totals["estimated_metadata_mb"] = round(
        totals["estimated_metadata_mb"] + stats["estimated_metadata_mb"], 2
    )
    group["index_names"] = sorted(set(group["index_names"]) | set(stats["index_names"]))
    group["embedding_dimensions"] = sorted(
        set(group["embedding_dimensions"]) | set(stats["embedding_dimensions"])
    )


def mongo_get_vector_db_stats_grouped() -> dict:
    """Aggregate DB stats for all experiments, grouped by vector database cluster."""
    experiments = mongo_list_all_experiment_docs()
    groups: dict[str, dict] = {}

    for experiment in experiments:
        experiment_id = str(experiment["experiment_id"])
        stats = mongo_get_experiment_db_stats(experiment_id)
        group_key = _vector_db_group_key(stats["database_provider"], stats["cluster_host"])

        if group_key not in groups:
            groups[group_key] = {
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

        group = groups[group_key]
        _merge_group_totals(group, stats)

        created_at = experiment.get("created_at")
        created_at_str = created_at.isoformat() if hasattr(created_at, "isoformat") else created_at

        group["experiments"].append(
            {
                "experiment_id": experiment_id,
                "experiment_name": experiment.get("experiment_name", ""),
                "status": experiment.get("status", ""),
                "created_at": created_at_str,
                **stats,
            }
        )

    grouped = list(groups.values())
    cluster_storage = _mongodb_cluster_storage_mb()
    for group in grouped:
        group["totals"].update(cluster_storage)
        group["experiments"].sort(
            key=lambda row: row.get("created_at") or "",
            reverse=True,
        )
    grouped.sort(key=lambda row: row["totals"]["total_chunks"], reverse=True)
    return {"groups": grouped}
