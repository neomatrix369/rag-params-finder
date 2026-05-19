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
