"""MongoDB adapter implementations for StorageBackend and RetrieverBackend.

All pymongo-specific code lives here; orchestrator, experiments API, and
startup reconciliation import from store_factory, not from this module directly.

Stats / explore helpers live in ``server.db.mongo_stats``.
"""

from datetime import UTC, datetime
from typing import Any, cast

from server.core.retrieval.retriever_mongo import search as _mongo_search
from server.db import mongo_stats
from server.db.atlas import (
    CHUNKS_COLLECTION,
    EXPERIMENTS_COLLECTION,
    RESULTS_COLLECTION,
    RUN_STATUS_COLLECTION,
    get_collection,
)
from server.models.enums import ExperimentStatus
from server.models.enums import RetrievalMethod as _RetrievalMethod
from server.models.results import SearchResult as _SearchResult
from server.utils.logger import get_logger

logger = get_logger(__name__)


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

    # ── Stats / explore (delegated to mongo_stats) ────────────────────────────

    def load_explore_source(self, experiment_id: str) -> tuple[dict | None, list[dict], list[dict]]:
        return mongo_stats.load_explore_source(experiment_id)

    def list_results_for_experiment(self, experiment_id: str) -> list[dict]:
        return mongo_stats.list_results_for_experiment(experiment_id)

    def get_experiment_db_stats(self, experiment_id: str) -> dict:
        return mongo_stats.get_experiment_db_stats(experiment_id)

    def get_vector_db_stats_grouped(self) -> dict:
        return mongo_stats.get_vector_db_stats_grouped(self.find_all_experiments)


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
