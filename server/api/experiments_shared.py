"""Synchronous Mongo helpers for experiments API (run inside asyncio.to_thread).

PyMongo blocks the asyncio event loop if called directly from async endpoints.
Keeping I/O here isolates blocking work into threadpool tasks.
"""

from datetime import UTC, datetime

from server.db.atlas import (
    CHUNKS_COLLECTION,
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
        {"$set": {"status": ExperimentStatus.CANCELLED, "completed_at": datetime.now(UTC)}},
    )


def mongo_mark_experiment_paused_now(experiment_id: str):
    get_collection(EXPERIMENTS_COLLECTION).update_one(
        {"_id": experiment_id},
        {"$set": {"status": ExperimentStatus.PAUSED, "completed_at": datetime.now(UTC)}},
    )


def mongo_mark_experiment_running(experiment_id: str):
    get_collection(EXPERIMENTS_COLLECTION).update_one(
        {"_id": experiment_id},
        {"$set": {"status": ExperimentStatus.RUNNING, "completed_at": None}},
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


def _mongodb_cluster_storage_mb() -> dict[str, float | str | None]:
    """Actual database footprint from MongoDB dbStats (data + indexes) + tier specs."""
    from server.core.atlas_storage import resolve_tier_specs
    from server.db.atlas import get_database

    db = get_database()
    stats = db.command("dbStats")
    data_bytes = float(stats.get("dataSize") or 0)
    index_bytes = float(stats.get("indexSize") or 0)
    total_bytes = float(stats.get("totalSize") or data_bytes + index_bytes)
    used_mb = _bytes_to_mb(total_bytes)

    # Get tier specs (includes storage_mb, instance_size, tier_type, provider, region)
    tier_specs = resolve_tier_specs()
    quota_mb: float | None = None
    if tier_specs:
        storage = tier_specs.get("storage_mb")
        if isinstance(storage, int | float):
            quota_mb = float(storage)
    has_quota = quota_mb is not None and quota_mb > 0

    result: dict[str, float | str | None] = {
        "database_used_mb": used_mb,
        "database_data_mb": _bytes_to_mb(data_bytes),
        "database_index_mb": _bytes_to_mb(index_bytes),
        "database_storage_limit_mb": quota_mb if has_quota else None,
        "database_free_mb": round(max(0.0, quota_mb - used_mb), 2)
        if has_quota and quota_mb is not None
        else None,
    }

    # Add tier information if available
    if tier_specs:
        for result_key, spec_key in (
            ("cluster_tier", "instance_size"),
            ("cluster_tier_type", "tier_type"),
            ("cluster_provider", "provider"),
            ("cluster_region", "region"),
        ):
            value = tier_specs.get(spec_key)
            if isinstance(value, str):
                result[result_key] = value

    return result


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


def _assemble_experiment_db_stats(
    experiment: dict | None,
    *,
    total_chunks: int,
    embedding_models: list[str],
    chunking_breakdown: dict[str, int],
    total_results: int,
    unique_queries: int,
    runs_with_data: int,
    run_breakdown: list[dict],
) -> dict:
    from server.core.model_registry import EMBEDDING_MODELS, get_dimensions, get_index_name
    from server.db.indexes import TEXT_SEARCH_INDEX_NAME

    embedding_dimensions = sorted(
        {get_dimensions(model) for model in embedding_models if model in EMBEDDING_MODELS}
    )
    unique_documents = len((experiment or {}).get("data_paths") or [])
    index_names = sorted(
        {get_index_name(model) for model in embedding_models if model in EMBEDDING_MODELS}
    )
    retrieval_methods = _retrieval_methods_for_experiment(experiment)
    if any(method in {"sparse", "hybrid"} for method in retrieval_methods):
        index_names.append(TEXT_SEARCH_INDEX_NAME)
        index_names = sorted(set(index_names))

    avg_chunks_per_run = round(total_chunks / runs_with_data, 1) if runs_with_data else 0.0
    embedding_mb, metadata_mb, total_mb = _storage_breakdown_mb(total_chunks, embedding_models)
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


def _bulk_chunk_aggregates() -> dict[str, dict]:
    """Per-experiment chunk counts and models in one aggregation (dashboard list)."""
    chunks_coll = get_collection(CHUNKS_COLLECTION)
    pipeline = [
        {
            "$group": {
                "_id": "$experiment_id",
                "total_chunks": {"$sum": 1},
                "embedding_models": {"$addToSet": "$embedding_model"},
                "run_ids": {"$addToSet": "$run_id"},
            }
        }
    ]
    out: dict[str, dict] = {}
    for row in chunks_coll.aggregate(pipeline, allowDiskUse=True):
        exp_id = row.get("_id")
        if not exp_id:
            continue
        models = [str(m) for m in row.get("embedding_models") or [] if m]
        run_ids = [r for r in row.get("run_ids") or [] if r]
        out[str(exp_id)] = {
            "total_chunks": int(row["total_chunks"]),
            "embedding_models": models,
            "runs_with_data": len(run_ids),
        }
    return out


def _bulk_result_aggregates() -> dict[str, dict]:
    """Per-experiment result counts in one aggregation."""
    results_coll = get_collection(RESULTS_COLLECTION)
    pipeline = [
        {
            "$group": {
                "_id": "$experiment_id",
                "total_results": {"$sum": 1},
                "query_ids": {"$addToSet": "$query_id"},
            }
        }
    ]
    out: dict[str, dict] = {}
    for row in results_coll.aggregate(pipeline, allowDiskUse=True):
        exp_id = row.get("_id")
        if not exp_id:
            continue
        query_ids = [q for q in row.get("query_ids") or [] if q]
        out[str(exp_id)] = {
            "total_results": int(row["total_results"]),
            "unique_queries": len(query_ids),
        }
    return out


def _bulk_chunking_breakdown() -> dict[str, dict[str, int]]:
    """Per-experiment chunking method counts in one aggregation."""
    chunks_coll = get_collection(CHUNKS_COLLECTION)
    pipeline = [
        {
            "$group": {
                "_id": {
                    "experiment_id": "$experiment_id",
                    "chunk_method": "$chunk_method",
                },
                "count": {"$sum": 1},
            }
        }
    ]
    out: dict[str, dict[str, int]] = {}
    for row in chunks_coll.aggregate(pipeline, allowDiskUse=True):
        key = row.get("_id") or {}
        exp_id = key.get("experiment_id")
        method = key.get("chunk_method")
        if not exp_id or not method:
            continue
        bucket = out.setdefault(str(exp_id), {})
        bucket[str(method)] = int(row["count"])
    return out


def _summary_db_stats_for_experiment(
    experiment: dict,
    chunk_row: dict | None,
    result_row: dict | None,
    chunking_breakdown: dict[str, int],
) -> dict:
    """Lightweight stats for grouped dashboard (no per-run breakdown queries)."""
    total_chunks = int((chunk_row or {}).get("total_chunks") or 0)
    embedding_models = list((chunk_row or {}).get("embedding_models") or [])
    runs_with_data = int((chunk_row or {}).get("runs_with_data") or 0)
    total_results = int((result_row or {}).get("total_results") or 0)
    unique_queries = int((result_row or {}).get("unique_queries") or 0)
    return _assemble_experiment_db_stats(
        experiment,
        total_chunks=total_chunks,
        embedding_models=embedding_models,
        chunking_breakdown=chunking_breakdown,
        total_results=total_results,
        unique_queries=unique_queries,
        runs_with_data=runs_with_data,
        run_breakdown=[],
    )


def mongo_get_experiment_db_stats(experiment_id: str) -> dict:
    """Vector DB stats for one experiment (full detail, including per-run breakdown)."""
    experiment = get_collection(EXPERIMENTS_COLLECTION).find_one(
        {"experiment_id": experiment_id},
        {"data_paths": 1, "sweep_summary": 1, "config": 1},
    )
    chunks_coll = get_collection(CHUNKS_COLLECTION)
    results_coll = get_collection(RESULTS_COLLECTION)

    total_chunks = chunks_coll.count_documents({"experiment_id": experiment_id})
    embedding_models = chunks_coll.distinct("embedding_model", {"experiment_id": experiment_id})
    total_results = results_coll.count_documents({"experiment_id": experiment_id})
    unique_queries = len(results_coll.distinct("query_id", {"experiment_id": experiment_id}))
    run_breakdown = _run_breakdown_for_experiment(chunks_coll, results_coll, experiment_id)
    chunking_breakdown = _chunking_breakdown(chunks_coll, experiment_id)

    return _assemble_experiment_db_stats(
        experiment,
        total_chunks=total_chunks,
        embedding_models=embedding_models,
        chunking_breakdown=chunking_breakdown,
        total_results=total_results,
        unique_queries=unique_queries,
        runs_with_data=len(run_breakdown),
        run_breakdown=run_breakdown,
    )


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
    chunk_by_exp = _bulk_chunk_aggregates()
    result_by_exp = _bulk_result_aggregates()
    chunking_by_exp = _bulk_chunking_breakdown()
    cluster_storage = _mongodb_cluster_storage_mb()
    groups: dict[str, dict] = {}

    for experiment in experiments:
        experiment_id = str(experiment["experiment_id"])
        stats = _summary_db_stats_for_experiment(
            experiment,
            chunk_by_exp.get(experiment_id),
            result_by_exp.get(experiment_id),
            chunking_by_exp.get(experiment_id, {}),
        )
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
    for group in grouped:
        group["totals"].update(cluster_storage)
        group["experiments"].sort(
            key=lambda row: row.get("created_at") or "",
            reverse=True,
        )
    grouped.sort(key=lambda row: row["totals"]["total_chunks"], reverse=True)
    return {"groups": grouped}
