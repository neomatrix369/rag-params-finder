"""StorageBackend Protocol — backend-agnostic interface for all persistent data I/O.

Call sites (orchestrator, experiments API, startup reconciliation) depend on this
port, never on pymongo or psycopg directly.
"""

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Port for experiment/run/chunk/result CRUD, cascade delete, and boot reconciliation."""

    # ── Experiment CRUD ───────────────────────────────────────────────────────

    def insert_experiment(self, doc: dict) -> None: ...

    def find_all_experiments(self) -> list[dict]: ...

    def find_experiment_by_id(self, experiment_id: str) -> dict | None: ...

    def find_experiment_with_runs(self, experiment_id: str) -> dict | None: ...

    def update_experiment(self, experiment_id: str, update: dict) -> None: ...

    def mark_experiment_cancelled(self, experiment_id: str) -> None: ...

    def mark_experiment_paused(self, experiment_id: str) -> None: ...

    def mark_experiment_running(self, experiment_id: str) -> None: ...

    def is_experiment_cancelled(self, experiment_id: str) -> bool: ...

    # ── Run status ────────────────────────────────────────────────────────────

    def insert_run_status(self, doc: dict) -> None: ...

    def update_run_phase(
        self,
        run_id: str,
        *,
        phase: str,
        updated_at: datetime,
        elapsed_ms: int,
        error_message: str | None,
    ) -> None: ...

    def find_run_status(self, run_id: str) -> dict | None: ...

    def find_run_statuses(self, experiment_id: str) -> list[dict]: ...

    def find_completed_run_sigs(self, experiment_id: str) -> list[dict]: ...

    def count_runs_by_phase(self, experiment_id: str, phase: str) -> int: ...

    def find_runs_by_phase(self, experiment_id: str, phase: str, limit: int) -> list[dict]: ...

    def mark_runs_interrupted(
        self,
        run_ids: list[str],
        *,
        updated_at: datetime,
        error_message: str,
    ) -> None: ...

    # ── Chunks ────────────────────────────────────────────────────────────────

    def insert_chunks(self, docs: list[dict]) -> None: ...

    def delete_chunks_for_experiment(self, experiment_id: str) -> int: ...

    # ── Results ───────────────────────────────────────────────────────────────

    def insert_result(self, doc: dict) -> None: ...

    def find_results_for_experiment(self, experiment_id: str) -> list[dict]: ...

    def find_results_for_run(self, experiment_id: str, run_id: str) -> list[dict]: ...

    def delete_results_for_experiment(self, experiment_id: str) -> int: ...

    # ── Cascade delete ────────────────────────────────────────────────────────

    def delete_experiment_data(self, experiment_id: str) -> dict[str, int]: ...

    # ── Boot reconciliation ───────────────────────────────────────────────────

    def find_running_experiments(self) -> list[dict]: ...

    def update_experiment_reconciled(
        self,
        experiment_id: str,
        *,
        status: object,
        failed_count: int,
        completion_reason: str,
        completed_at: datetime,
    ) -> None: ...

    # ── API helpers ───────────────────────────────────────────────────────────

    def load_explore_source(
        self, experiment_id: str
    ) -> tuple[dict | None, list[dict], list[dict]]: ...

    def list_results_for_experiment(self, experiment_id: str) -> list[dict]: ...

    def get_experiment_db_stats(self, experiment_id: str) -> dict: ...

    def get_vector_db_stats_grouped(self) -> dict: ...
