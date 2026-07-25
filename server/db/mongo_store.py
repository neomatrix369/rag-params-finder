"""MongoDB adapter implementations for StorageBackend and RetrieverBackend.

All pymongo-specific code lives here; orchestrator, experiments API, and
startup reconciliation import from store_factory, not from this module directly.
"""

from datetime import UTC, datetime
from typing import Any, cast

from server.db.atlas import (
    CHUNKS_COLLECTION,
    EXPERIMENTS_COLLECTION,
    RESULTS_COLLECTION,
    RUN_STATUS_COLLECTION,
    get_collection,
    get_database,
)
from server.models.enums import ExperimentStatus
from server.models.enums import RetrievalMethod as _RetrievalMethod
from server.models.results import SearchResult as _SearchResult
from server.utils.logger import get_logger

logger = get_logger(__name__)


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
    from server.core.atlas_storage import resolve_tier_specs

    db = get_database()
    stats = db.command("dbStats")
    data_bytes = float(stats.get("dataSize") or 0)
    index_bytes = float(stats.get("indexSize") or 0)
    total_bytes = float(stats.get("totalSize") or data_bytes + index_bytes)
    used_mb = _bytes_to_mb(total_bytes)

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


class MongoStorageBackend:
    """StorageBackend backed by MongoDB Atlas / Atlas Local."""

    # ── Experiment CRUD ───────────────────────────────────────────────────────

    def insert_experiment(self, doc: dict) -> None:
        get_collection(EXPERIMENTS_COLLECTION).insert_one(doc)

    def find_all_experiments(self) -> list[dict]:
        return list(
            get_collection(EXPERIMENTS_COLLECTION).find({}, {"_id": 0}).sort("created_at", -1)
        )

    def find_experiment_by_id(self, experiment_id: str) -> dict | None:
        return cast(
            dict[str, Any] | None,
            get_collection(EXPERIMENTS_COLLECTION).find_one({"experiment_id": experiment_id}),
        )

    def find_experiment_with_runs(self, experiment_id: str) -> dict | None:
        experiment = cast(
            dict[str, Any] | None,
            get_collection(EXPERIMENTS_COLLECTION).find_one(
                {"experiment_id": experiment_id}, {"_id": 0}
            ),
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

    def update_experiment(self, experiment_id: str, update: dict) -> None:
        get_collection(EXPERIMENTS_COLLECTION).update_one({"_id": experiment_id}, {"$set": update})

    def mark_experiment_cancelled(self, experiment_id: str) -> None:
        get_collection(EXPERIMENTS_COLLECTION).update_one(
            {"_id": experiment_id},
            {"$set": {"status": ExperimentStatus.CANCELLED, "completed_at": datetime.now(UTC)}},
        )

    def mark_experiment_paused(self, experiment_id: str) -> None:
        get_collection(EXPERIMENTS_COLLECTION).update_one(
            {"_id": experiment_id},
            {"$set": {"status": ExperimentStatus.PAUSED, "completed_at": datetime.now(UTC)}},
        )

    def mark_experiment_running(self, experiment_id: str) -> None:
        get_collection(EXPERIMENTS_COLLECTION).update_one(
            {"_id": experiment_id},
            {"$set": {"status": ExperimentStatus.RUNNING, "completed_at": None}},
        )

    def is_experiment_cancelled(self, experiment_id: str) -> bool:
        doc = get_collection(EXPERIMENTS_COLLECTION).find_one({"_id": experiment_id}, {"status": 1})
        return bool(doc and doc.get("status") == ExperimentStatus.CANCELLED.value)

    # ── Run status ────────────────────────────────────────────────────────────

    def insert_run_status(self, doc: dict) -> None:
        get_collection(RUN_STATUS_COLLECTION).insert_one(doc)

    def update_run_phase(
        self,
        run_id: str,
        *,
        phase: str,
        updated_at: datetime,
        elapsed_ms: int,
        error_message: str | None,
    ) -> None:
        get_collection(RUN_STATUS_COLLECTION).update_one(
            {"run_id": run_id},
            {
                "$set": {
                    "phase": phase,
                    "updated_at": updated_at,
                    "elapsed_ms": elapsed_ms,
                    "error_message": error_message,
                }
            },
        )

    def find_run_status(self, run_id: str) -> dict | None:
        return cast(
            dict[str, Any] | None,
            get_collection(RUN_STATUS_COLLECTION).find_one({"run_id": run_id}, {"_id": 0}),
        )

    def find_run_statuses(self, experiment_id: str) -> list[dict]:
        return list(
            get_collection(RUN_STATUS_COLLECTION).find({"experiment_id": experiment_id}, {"_id": 0})
        )

    def find_completed_run_sigs(self, experiment_id: str) -> list[dict]:
        cursor = get_collection(RUN_STATUS_COLLECTION).find(
            {"experiment_id": experiment_id, "phase": "complete"},
            {
                "database_provider": 1,
                "embedding_provider": 1,
                "embedding_model": 1,
                "chunking_method": 1,
                "chunk_size": 1,
                "overlap": 1,
                "retrieval_method": 1,
                "retrieval_provider": 1,
                "retrieval_model": 1,
            },
        )
        return list(cursor)

    def count_runs_by_phase(self, experiment_id: str, phase: str) -> int:
        return int(
            get_collection(RUN_STATUS_COLLECTION).count_documents(
                {"experiment_id": experiment_id, "phase": phase}
            )
        )

    def find_runs_by_phase(self, experiment_id: str, phase: str, limit: int) -> list[dict]:
        cursor = (
            get_collection(RUN_STATUS_COLLECTION)
            .find(
                {"experiment_id": experiment_id, "phase": phase},
                {
                    "run_id": 1,
                    "embedding_model": 1,
                    "chunking_method": 1,
                    "chunk_size": 1,
                    "error_message": 1,
                },
            )
            .limit(limit)
        )
        return list(cursor)

    def mark_runs_interrupted(
        self,
        run_ids: list[str],
        *,
        updated_at: datetime,
        error_message: str,
    ) -> None:
        if not run_ids:
            return
        get_collection(RUN_STATUS_COLLECTION).update_many(
            {"run_id": {"$in": run_ids}},
            {
                "$set": {
                    "phase": "interrupted",
                    "updated_at": updated_at,
                    "error_message": error_message,
                }
            },
        )

    # ── Chunks ────────────────────────────────────────────────────────────────

    def insert_chunks(self, docs: list[dict]) -> None:
        if docs:
            get_collection(CHUNKS_COLLECTION).insert_many(docs)

    def delete_chunks_for_experiment(self, experiment_id: str) -> int:
        return int(
            get_collection(CHUNKS_COLLECTION)
            .delete_many({"experiment_id": experiment_id})
            .deleted_count
        )

    # ── Results ───────────────────────────────────────────────────────────────

    def insert_result(self, doc: dict) -> None:
        get_collection(RESULTS_COLLECTION).insert_one(doc)

    def find_results_for_experiment(self, experiment_id: str) -> list[dict]:
        return list(
            get_collection(RESULTS_COLLECTION).find(
                {"experiment_id": experiment_id},
                {"run_id": 1, "query_text": 1, "results": 1},
            )
        )

    def find_results_for_run(self, experiment_id: str, run_id: str) -> list[dict]:
        return list(
            get_collection(RESULTS_COLLECTION).find(
                {"run_id": run_id, "experiment_id": experiment_id},
                {"query_text": 1, "results": 1},
            )
        )

    def delete_results_for_experiment(self, experiment_id: str) -> int:
        return int(
            get_collection(RESULTS_COLLECTION)
            .delete_many({"experiment_id": experiment_id})
            .deleted_count
        )

    # ── Cascade delete ────────────────────────────────────────────────────────

    def delete_experiment_data(self, experiment_id: str) -> dict[str, int]:
        logger.info("delete started — experiment %s", experiment_id)
        chunks_deleted = self.delete_chunks_for_experiment(experiment_id)
        results_deleted = self.delete_results_for_experiment(experiment_id)
        run_status_deleted = int(
            get_collection(RUN_STATUS_COLLECTION)
            .delete_many({"experiment_id": experiment_id})
            .deleted_count
        )
        experiment_deleted = int(
            get_collection(EXPERIMENTS_COLLECTION)
            .delete_one({"experiment_id": experiment_id})
            .deleted_count
        )
        counts = {
            "experiments": experiment_deleted,
            "run_status": run_status_deleted,
            "chunks": chunks_deleted,
            "results": results_deleted,
        }
        logger.info("delete complete — experiment %s, counts=%s", experiment_id, counts)
        return counts

    # ── Boot reconciliation ───────────────────────────────────────────────────

    def find_running_experiments(self) -> list[dict]:
        return list(
            get_collection(EXPERIMENTS_COLLECTION).find({"status": ExperimentStatus.RUNNING})
        )

    def update_experiment_reconciled(
        self,
        experiment_id: str,
        *,
        status: object,
        failed_count: int,
        completion_reason: str,
        completed_at: datetime,
    ) -> None:
        get_collection(EXPERIMENTS_COLLECTION).update_one(
            {"_id": experiment_id},
            {
                "$set": {
                    "status": status,
                    "failed_count": failed_count,
                    "completion_reason": completion_reason,
                    "completed_at": completed_at,
                }
            },
        )

    # ── API helpers ───────────────────────────────────────────────────────────

    def load_explore_source(self, experiment_id: str) -> tuple[dict | None, list[dict], list[dict]]:
        experiment = get_collection(EXPERIMENTS_COLLECTION).find_one(
            {"experiment_id": experiment_id}
        )
        if not experiment:
            return None, [], []
        query_results = list(
            get_collection(RESULTS_COLLECTION).find({"experiment_id": experiment_id}, {"_id": 0})
        )
        run_statuses = list(
            get_collection(RUN_STATUS_COLLECTION).find({"experiment_id": experiment_id}, {"_id": 0})
        )
        return experiment, query_results, run_statuses

    def list_results_for_experiment(self, experiment_id: str) -> list[dict]:
        return list(
            get_collection(RESULTS_COLLECTION).find({"experiment_id": experiment_id}, {"_id": 0})
        )

    def get_experiment_db_stats(self, experiment_id: str) -> dict:
        logger.debug("computing db stats — experiment %s", experiment_id)
        try:
            experiment = get_collection(EXPERIMENTS_COLLECTION).find_one(
                {"experiment_id": experiment_id},
                {"data_paths": 1, "sweep_summary": 1, "config": 1},
            )
            chunks_coll = get_collection(CHUNKS_COLLECTION)
            results_coll = get_collection(RESULTS_COLLECTION)

            total_chunks = chunks_coll.count_documents({"experiment_id": experiment_id})
            embedding_models = chunks_coll.distinct(
                "embedding_model", {"experiment_id": experiment_id}
            )
            total_results = results_coll.count_documents({"experiment_id": experiment_id})
            unique_queries = len(
                results_coll.distinct("query_id", {"experiment_id": experiment_id})
            )
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

    def get_vector_db_stats_grouped(self) -> dict:
        logger.debug("computing grouped vector db stats — all experiments")
        try:
            experiments = self.find_all_experiments()
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
                if created_at is not None and hasattr(created_at, "isoformat"):
                    created_at_str: Any = created_at.isoformat()
                else:
                    created_at_str = created_at
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
        except Exception:
            logger.error("grouped vector db stats failed — aggregation error", exc_info=True)
            raise
        logger.debug(
            "grouped vector db stats ready — %s group(s), %s experiment(s)",
            len(grouped),
            len(experiments),
        )
        return {"groups": grouped}


class MongoRetrieverBackend:
    """RetrieverBackend backed by MongoDB Atlas / Atlas Local."""

    def search(
        self,
        method: _RetrievalMethod,
        query_text: str,
        experiment_id: str,
        embedding_model: str,
        run_id: str,
        top_k: int,
        query_embedding: list[float] | None,
    ) -> list[_SearchResult]:
        from server.core.retriever import search as _mongo_search

        return _mongo_search(
            method=method,
            query_text=query_text,
            experiment_id=experiment_id,
            embedding_model=embedding_model,
            run_id=run_id,
            top_k=top_k,
            query_embedding=query_embedding,
        )


# ── Singleton accessors ───────────────────────────────────────────────────────
_storage: MongoStorageBackend | None = None
_retriever: MongoRetrieverBackend | None = None


def get_mongo_storage() -> MongoStorageBackend:
    global _storage
    if _storage is None:
        _storage = MongoStorageBackend()
    return _storage


def get_mongo_retriever() -> MongoRetrieverBackend:
    global _retriever
    if _retriever is None:
        _retriever = MongoRetrieverBackend()
    return _retriever
