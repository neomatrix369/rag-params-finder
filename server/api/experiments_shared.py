"""Synchronous storage helpers for experiments API (run inside asyncio.to_thread).

PyMongo blocks the asyncio event loop if called directly from async endpoints.
Keeping I/O here isolates blocking work into threadpool tasks.

All persistent data access delegates to the StorageBackend port via store_factory.
The mongo-specific aggregation code now lives in server.db.mongo_store.
"""

from server.db.store_factory import get_storage_backend
from server.utils.logger import get_logger

logger = get_logger(__name__)


def mongo_list_all_experiment_docs():
    return get_storage_backend().find_all_experiments()


def mongo_find_experiment_with_runs(experiment_id: str):
    return get_storage_backend().find_experiment_with_runs(experiment_id)


def mongo_insert_experiment_doc(experiment_doc: dict):
    get_storage_backend().insert_experiment(experiment_doc)


def mongo_list_results_for_experiment(experiment_id: str):
    return get_storage_backend().list_results_for_experiment(experiment_id)


def mongo_load_explore_source(experiment_id: str):
    return get_storage_backend().load_explore_source(experiment_id)


def mongo_find_experiment_by_id(experiment_id: str):
    return get_storage_backend().find_experiment_by_id(experiment_id)


def mongo_mark_experiment_cancelled_now(experiment_id: str):
    get_storage_backend().mark_experiment_cancelled(experiment_id)


def mongo_mark_experiment_paused_now(experiment_id: str):
    get_storage_backend().mark_experiment_paused(experiment_id)


def mongo_mark_experiment_running(experiment_id: str):
    get_storage_backend().mark_experiment_running(experiment_id)


def mongo_delete_experiment_data(experiment_id: str) -> dict[str, int]:
    return get_storage_backend().delete_experiment_data(experiment_id)


def mongo_get_experiment_db_stats(experiment_id: str) -> dict:
    return get_storage_backend().get_experiment_db_stats(experiment_id)


def mongo_get_vector_db_stats_grouped() -> dict:
    return get_storage_backend().get_vector_db_stats_grouped()
