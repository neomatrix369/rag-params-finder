"""MongoDB stats and explore helpers extracted from mongo_store.

Mongo-specific aggregation queries plus four public query functions that
compose collection reads and statistics assembly.  MongoStorageBackend
delegates to these; they have no dependency on the class itself.

The backend-agnostic assembly maths lives in ``server.db.stats_common`` and is
shared with the Postgres adapter.
"""

from collections.abc import Callable
from typing import Any

from server.core.atlas_storage import resolve_tier_specs
from server.core.model_registry import EMBEDDING_MODELS, get_index_name
from server.db.atlas import (
    CHUNKS_COLLECTION,
    EXPERIMENTS_COLLECTION,
    RESULTS_COLLECTION,
    RUN_STATUS_COLLECTION,
    get_collection,
    get_database,
)
from server.db.indexes import TEXT_SEARCH_INDEX_NAME
from server.db.stats_common import (
    assemble_experiment_db_stats,
    bytes_to_mb,
    experiment_summary_row,
    finalize_groups,
    merge_group_totals,
    new_vector_db_group,
    retrieval_methods_for_experiment,
    vector_db_group_key,
)
from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)


# ── Mongo-specific helpers ────────────────────────────────────────────────────


def _mongodb_cluster_hint() -> str | None:
    uri = settings.mongodb_uri.strip()
    if not uri:
        return None
    without_scheme = uri.split("://", 1)[-1]
    host_part = without_scheme.split("@")[-1].split("/")[0].split("?")[0]
    return host_part or None


def _mongodb_cluster_storage_mb() -> dict[str, float | str | None]:
    db = get_database()
    stats = db.command("dbStats")
    data_bytes = float(stats.get("dataSize") or 0)
    index_bytes = float(stats.get("indexSize") or 0)
    total_bytes = float(stats.get("totalSize") or data_bytes + index_bytes)
    used_mb = bytes_to_mb(total_bytes)

    tier_specs = resolve_tier_specs()
    quota_mb: float | None = None
    if tier_specs:
        storage = tier_specs.get("storage_mb")
        if isinstance(storage, int | float):
            quota_mb = float(storage)
    has_quota = quota_mb is not None and quota_mb > 0

    result: dict[str, float | str | None] = {
        "database_used_mb": used_mb,
        "database_data_mb": bytes_to_mb(data_bytes),
        "database_index_mb": bytes_to_mb(index_bytes),
        "database_storage_limit_mb": quota_mb if has_quota else None,
        "database_free_mb": round(max(0.0, quota_mb - used_mb), 2)
        if has_quota and quota_mb is not None
        else None,
    }

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


def _chunking_breakdown(chunks_coll: Any, experiment_id: str) -> dict[str, int]:
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


def _document_counts_by_run_id(collection: Any, experiment_id: str) -> dict[str, int]:
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


def _run_breakdown_for_experiment(
    chunks_coll: Any, results_coll: Any, experiment_id: str
) -> list[dict]:
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


def _atlas_index_names(experiment: dict | None, embedding_models: list[str]) -> list[str]:
    """Atlas search indexes an experiment touches — vector plus text when sparse."""
    index_names = {get_index_name(model) for model in embedding_models if model in EMBEDDING_MODELS}
    methods = retrieval_methods_for_experiment(experiment)
    if any(method in {"sparse", "hybrid"} for method in methods):
        index_names.add(TEXT_SEARCH_INDEX_NAME)
    return sorted(index_names)


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
    sweep = (experiment or {}).get("sweep_summary") or {}
    return assemble_experiment_db_stats(
        experiment,
        database_provider=str(sweep.get("database_provider") or "mongodb"),
        collection_name=CHUNKS_COLLECTION,
        cluster_host=_mongodb_cluster_hint(),
        index_names=_atlas_index_names(experiment, embedding_models),
        total_chunks=total_chunks,
        embedding_models=embedding_models,
        chunking_breakdown=chunking_breakdown,
        total_results=total_results,
        unique_queries=unique_queries,
        runs_with_data=runs_with_data,
        run_breakdown=run_breakdown,
    )


def _bulk_chunk_aggregates() -> dict[str, dict]:
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


# ── Public query functions ────────────────────────────────────────────────────


def load_explore_source(
    experiment_id: str,
) -> tuple[dict | None, list[dict], list[dict]]:
    """Load experiment, query results, and run statuses for the explore screen."""
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


def list_results_for_experiment(experiment_id: str) -> list[dict]:
    """Return all result documents for an experiment (no ``_id`` field)."""
    return list(
        get_collection(RESULTS_COLLECTION).find({"experiment_id": experiment_id}, {"_id": 0})
    )


def get_experiment_db_stats(experiment_id: str) -> dict:
    """Compute per-experiment chunk/result/storage statistics."""
    logger.debug("computing db stats — experiment %s", experiment_id)
    try:
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
        chunking_bkdn = _chunking_breakdown(chunks_coll, experiment_id)

        stats = _assemble_experiment_db_stats(
            experiment,
            total_chunks=total_chunks,
            embedding_models=embedding_models,
            chunking_breakdown=chunking_bkdn,
            total_results=total_results,
            unique_queries=unique_queries,
            runs_with_data=len(run_breakdown),
            run_breakdown=run_breakdown,
        )
    except Exception:
        logger.error("db stats compute failed — experiment %s", experiment_id, exc_info=True)
        raise
    logger.debug(
        "db stats ready — experiment %s chunks=%s est_mb=%s",
        experiment_id,
        stats["total_chunks"],
        stats["estimated_storage_mb"],
    )
    return stats


def get_vector_db_stats_grouped(
    find_all_experiments: Callable[[], list[dict]],
) -> dict:
    """Compute grouped vector-db statistics across all experiments.

    ``find_all_experiments`` is a callable that returns the full experiment
    list — this avoids a circular dependency on MongoStorageBackend.
    """
    logger.debug("computing grouped vector db stats — all experiments")
    try:
        experiments = find_all_experiments()
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
            group_key = vector_db_group_key(stats["database_provider"], stats["cluster_host"])

            if group_key not in groups:
                groups[group_key] = new_vector_db_group(group_key, stats)

            group = groups[group_key]
            merge_group_totals(group, stats)
            group["experiments"].append(experiment_summary_row(experiment, experiment_id, stats))

        grouped = finalize_groups(groups, cluster_storage)
    except Exception:
        logger.error("grouped vector db stats failed — aggregation error", exc_info=True)
        raise
    logger.debug(
        "grouped vector db stats ready — %s group(s), %s experiment(s)",
        len(grouped),
        len(experiments),
    )
    return {"groups": grouped}
