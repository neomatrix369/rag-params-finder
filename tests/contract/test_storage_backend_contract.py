"""
Contract tests for the StorageBackend Protocol — both live adapters.

Author: Mani Sarkar
Created: 2026-07-26
Scope: Behaviour-level scenarios over the port only — experiment CRUD,
       find_experiment_with_runs shape, run phase transitions, cascade delete
       counts, find_running_experiments reconciliation shape, and
       get_experiment_db_stats key contract. Driven by the parametrized
       ``storage`` fixture (mongo + postgres).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from server.db.ports.storage import StorageBackend
from server.models.enums import ExperimentStatus
from tests.helpers.storage_live import CONTRACT_EXP_ID, CONTRACT_RUN_ID

pytestmark = pytest.mark.integration

# Keys documented on StorageBackend.get_experiment_db_stats (server/db/storage.py).
_DB_STATS_KEYS = frozenset(
    {
        "database_provider",
        "collection_name",
        "cluster_host",
        "total_chunks",
        "unique_documents",
        "embedding_models",
        "embedding_dimensions",
        "index_names",
        "retrieval_methods",
        "chunking_methods",
        "chunking_breakdown",
        "estimated_storage_mb",
        "estimated_embedding_mb",
        "estimated_metadata_mb",
        "runs_with_data",
        "avg_chunks_per_run",
        "total_results",
        "unique_queries",
        "run_breakdown",
    }
)


def _experiment_doc(**overrides: object) -> dict:
    doc: dict = {
        "_id": CONTRACT_EXP_ID,
        "experiment_id": CONTRACT_EXP_ID,
        "experiment_name": "storage contract",
        "status": ExperimentStatus.RUNNING,
        "created_at": datetime(2026, 7, 26, 12, 0, tzinfo=UTC),
        "started_at": None,
        "completed_at": None,
        "data_paths": ["./input_data/pdfs/a.pdf"],
        "total_runs": 1,
        "sweep_summary": {"database_provider": "contract"},
    }
    doc.update(overrides)
    return doc


def _run_doc(**overrides: object) -> dict:
    doc: dict = {
        "run_id": CONTRACT_RUN_ID,
        "experiment_id": CONTRACT_EXP_ID,
        "phase": "queued",
        "created_at": datetime(2026, 7, 26, 12, 1, tzinfo=UTC),
        "updated_at": datetime(2026, 7, 26, 12, 1, tzinfo=UTC),
        "embedding_model": "all-MiniLM-L6-v2",
        "chunking_method": "recursive",
        "chunk_size": 512,
        "overlap": 50,
    }
    doc.update(overrides)
    return doc


def _chunk_doc(chunk_id: str, **overrides: object) -> dict:
    doc: dict = {
        "chunk_id": chunk_id,
        "experiment_id": CONTRACT_EXP_ID,
        "run_id": CONTRACT_RUN_ID,
        "text": "Pell Grant eligibility depends on financial need.",
        "index": 0,
        "embedding_model": "all-MiniLM-L6-v2",
        "chunk_method": "recursive",
        "chunk_size": 512,
        "overlap": 50,
        "padding": 0,
        "embedding": [0.1] * 384,
    }
    doc.update(overrides)
    return doc


class TestStorageBackendContractShould:
    """Port-level behaviour that every StorageBackend adapter must satisfy."""

    def test_given_experiment_when_inserted_then_round_trip_preserves_identity(
        self, storage: StorageBackend
    ) -> None:
        """
        Scenario: Insert + find_experiment_by_id returns the same experiment_id.
        Slice: storage-backend-contract

        Given an experiment document,
        When it is inserted and read back by id,
        Then the experiment_id and name match the original.
        """
        ### Given
        doc = _experiment_doc()

        ### When
        storage.insert_experiment(doc)
        actual = storage.find_experiment_by_id(CONTRACT_EXP_ID)

        ### Then
        assert actual is not None, "Expected the inserted experiment to be found"
        assert actual["experiment_id"] == CONTRACT_EXP_ID
        assert actual["experiment_name"] == "storage contract"

    def test_given_experiment_with_run_when_find_with_runs_then_runs_list_present(
        self, storage: StorageBackend
    ) -> None:
        """
        Scenario: find_experiment_with_runs embeds the run documents.
        Slice: storage-backend-contract

        Given an experiment and one run,
        When find_experiment_with_runs is called,
        Then the returned document carries a runs list with that run_id.
        """
        ### Given
        storage.insert_experiment(_experiment_doc())
        storage.insert_run_status(_run_doc())

        ### When
        actual = storage.find_experiment_with_runs(CONTRACT_EXP_ID)

        ### Then
        assert actual is not None
        assert "runs" in actual, "find_experiment_with_runs must embed a runs list"
        assert any(run["run_id"] == CONTRACT_RUN_ID for run in actual["runs"])

    def test_given_queued_run_when_phase_updated_then_new_phase_readable(
        self, storage: StorageBackend
    ) -> None:
        """
        Scenario: update_run_phase persists phase and error fields.
        Slice: storage-backend-contract

        Given a queued run,
        When its phase is advanced to failed with an error message,
        Then find_run_status reports the new phase and error.
        """
        ### Given
        storage.insert_experiment(_experiment_doc())
        storage.insert_run_status(_run_doc())

        ### When
        storage.update_run_phase(
            CONTRACT_RUN_ID,
            phase="failed",
            updated_at=datetime(2026, 7, 26, 12, 5, tzinfo=UTC),
            elapsed_ms=1234,
            error_message="contract probe",
        )
        actual = storage.find_run_status(CONTRACT_RUN_ID)

        ### Then
        assert actual is not None
        assert actual["phase"] == "failed"
        assert actual["error_message"] == "contract probe"

    def test_given_experiment_with_children_when_cascade_deleted_then_counts_match(
        self, storage: StorageBackend
    ) -> None:
        """
        Scenario: delete_experiment_data removes experiment, runs, chunks, results.
        Slice: storage-backend-contract

        Given an experiment with one run, two chunks, and one result,
        When delete_experiment_data is called,
        Then every key reports its deleted count and no rows remain.
        """
        ### Given
        storage.insert_experiment(_experiment_doc())
        storage.insert_run_status(_run_doc())
        storage.insert_chunks([_chunk_doc("c-1"), _chunk_doc("c-2", index=1)])
        storage.insert_result(
            {
                "experiment_id": CONTRACT_EXP_ID,
                "run_id": CONTRACT_RUN_ID,
                "query_id": "q1",
                "query_text": "What is the Pell Grant deadline?",
                "results": [{"chunk_id": "c-1", "score": 0.91}],
            }
        )

        ### When
        actual = storage.delete_experiment_data(CONTRACT_EXP_ID)

        ### Then
        assert actual == {"chunks": 2, "results": 1, "run_status": 1, "experiments": 1}
        assert storage.find_experiment_by_id(CONTRACT_EXP_ID) is None
        assert storage.find_run_statuses(CONTRACT_EXP_ID) == []
        assert storage.find_results_for_experiment(CONTRACT_EXP_ID) == []

    def test_given_running_experiment_when_listed_then_carries_id_for_reconciliation(
        self, storage: StorageBackend
    ) -> None:
        """
        Scenario: find_running_experiments returns docs with _id for boot reconciliation.
        Slice: storage-backend-contract

        Given a running experiment,
        When find_running_experiments is called,
        Then at least one entry carries _id equal to the experiment_id.
        """
        ### Given
        storage.insert_experiment(_experiment_doc(status=ExperimentStatus.RUNNING))

        ### When
        running = storage.find_running_experiments()

        ### Then
        assert any(
            str(row.get("_id") or row.get("experiment_id")) == CONTRACT_EXP_ID for row in running
        ), "Running experiments must carry _id (or experiment_id) for startup reconciliation"

    def test_given_populated_experiment_when_db_stats_then_required_keys_present(
        self, storage: StorageBackend
    ) -> None:
        """
        Scenario: get_experiment_db_stats returns the documented key set.
        Slice: storage-backend-contract

        Given an experiment with a run, chunks, and a result,
        When get_experiment_db_stats is called,
        Then every key from the StorageBackend docstring is present and totals match.
        """
        ### Given
        storage.insert_experiment(_experiment_doc())
        storage.insert_run_status(_run_doc())
        storage.insert_chunks([_chunk_doc("c-1"), _chunk_doc("c-2", index=1)])
        storage.insert_result(
            {
                "experiment_id": CONTRACT_EXP_ID,
                "run_id": CONTRACT_RUN_ID,
                "query_id": "q1",
                "query_text": "q",
                "results": [],
            }
        )

        ### When
        actual = storage.get_experiment_db_stats(CONTRACT_EXP_ID)

        ### Then
        missing = _DB_STATS_KEYS - set(actual)
        assert not missing, f"get_experiment_db_stats missing keys: {sorted(missing)}"
        assert actual["total_chunks"] == 2
        assert actual["total_results"] == 1
        assert actual["collection_name"] == "chunks"
