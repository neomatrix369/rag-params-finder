"""Synchronous storage helpers for experiments API (run inside asyncio.to_thread).

Blocking database drivers stall the asyncio event loop if called directly from
async endpoints. Keeping I/O here isolates blocking work into threadpool tasks.

All persistent data access delegates to the StorageBackend port via store_factory.
"""

from server.db.ports import store_factory
from server.db.ports.store_factory import get_storage_backend
from server.utils.logger import get_logger

logger = get_logger(__name__)

# Experiment types used internally (e.g. sweep history bookkeeping) that must not
# appear in the user-facing experiments list.
_INTERNAL_EXPERIMENT_TYPES = {"tier1_sweep"}


def list_all_experiment_docs():
    return [
        doc
        for doc in get_storage_backend().find_all_experiments()
        if doc.get("experiment_type") not in _INTERNAL_EXPERIMENT_TYPES
    ]


def find_experiment_with_runs(experiment_id: str):
    return get_storage_backend().find_experiment_with_runs(experiment_id)


def insert_experiment_doc(experiment_doc: dict):
    get_storage_backend().insert_experiment(experiment_doc)


def list_results_for_experiment(experiment_id: str):
    return get_storage_backend().list_results_for_experiment(experiment_id)


def load_explore_source(experiment_id: str):
    return get_storage_backend().load_explore_source(experiment_id)


def find_experiment_by_id(experiment_id: str):
    return get_storage_backend().find_experiment_by_id(experiment_id)


def mark_experiment_cancelled_now(experiment_id: str):
    get_storage_backend().mark_experiment_cancelled(experiment_id)


def mark_experiment_paused_now(experiment_id: str):
    get_storage_backend().mark_experiment_paused(experiment_id)


def mark_experiment_running(experiment_id: str):
    get_storage_backend().mark_experiment_running(experiment_id)


def delete_experiment_data(experiment_id: str) -> dict[str, int]:
    """Delete an experiment's data from both stores (DECISIONS #246).

    Order: vector store first (chunks), then run state (experiment, runs,
    results) — both steps are idempotent, so a retry after a partial failure
    completes the delete and reports the true counts. Response shape is
    unchanged (same keys as the pre-split-store StorageBackend cascade) —
    only the composition source changed.
    """
    chunks_deleted = store_factory.get_vector_store().delete_chunks_for_experiment(experiment_id)
    run_state_counts = get_storage_backend().delete_experiment_data(experiment_id)
    counts = dict(run_state_counts)
    counts["chunks"] = chunks_deleted
    return counts


def get_experiment_db_stats(experiment_id: str) -> dict:
    """Compose per-experiment db-stats: chunk facts from the vector store,
    result facts from run state (DECISIONS #240). Response shape unchanged."""
    stats = dict(store_factory.get_vector_store().get_experiment_db_stats(experiment_id))
    run_state_stats = get_storage_backend().get_experiment_db_stats(experiment_id)
    stats["total_results"] = run_state_stats.get("total_results", stats.get("total_results", 0))
    stats["unique_queries"] = run_state_stats.get("unique_queries", stats.get("unique_queries", 0))
    return stats


def get_vector_db_stats_grouped() -> dict:
    return store_factory.get_vector_store().get_vector_db_stats_grouped()
