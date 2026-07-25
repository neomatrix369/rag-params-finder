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
    #
    # Interface Segregation note: the four methods below form an API-helper
    # cluster serving the explore and db-stats screens rather than core CRUD.
    # They are kept on StorageBackend because every adapter must answer them for
    # the dashboard to render; splitting them into a second port is deferred
    # until a backend needs one without the other.

    def load_explore_source(self, experiment_id: str) -> tuple[dict | None, list[dict], list[dict]]:
        """Load the raw source rows behind the Search Explorer screen.

        Returns a 3-tuple of ``(experiment, query_results, run_statuses)``:

        - ``experiment`` — the experiment document, or ``None`` when the id is
          unknown. When ``None``, both lists are empty.
        - ``query_results`` — every result document for the experiment, each
          shaped like ``QueryResult`` (``query_id``, ``run_id``, ``query_text``,
          ``persona_id``, ``focus``, ``results``, ``top_k``).
        - ``run_statuses`` — every run document for the experiment, each shaped
          like ``RunStatus`` (``run_id``, ``phase``, ``embedding_model``,
          ``chunking_method``, ``chunk_size``, ``overlap``, ``padding``, …).
        """
        ...

    def list_results_for_experiment(self, experiment_id: str) -> list[dict]:
        """Return every result document for an experiment.

        Each entry is a full ``QueryResult`` document. Unlike
        ``find_results_for_experiment``, no field projection is applied — callers
        that rank configurations need the complete document.
        """
        ...

    def get_experiment_db_stats(self, experiment_id: str) -> dict:
        """Compute per-experiment storage and content statistics.

        Returned keys: ``database_provider``, ``collection_name``,
        ``cluster_host``, ``total_chunks``, ``unique_documents``,
        ``embedding_models``, ``embedding_dimensions``, ``index_names``,
        ``retrieval_methods``, ``chunking_methods``, ``chunking_breakdown``,
        ``estimated_storage_mb``, ``estimated_embedding_mb``,
        ``estimated_metadata_mb``, ``runs_with_data``, ``avg_chunks_per_run``,
        ``total_results``, ``unique_queries``, and ``run_breakdown`` (a list of
        ``{run_id, chunks, results}``).
        """
        ...

    def get_vector_db_stats_grouped(self) -> dict:
        """Compute cluster-grouped statistics across all experiments.

        Returns ``{"groups": [...]}``. Each group carries ``vector_db_id``,
        ``database_provider``, ``collection_name``, ``cluster_host``,
        ``index_names``, ``embedding_dimensions``, a ``totals`` dict, and an
        ``experiments`` list.

        ``totals`` accumulates ``experiment_count``, ``total_chunks``,
        ``total_results``, ``estimated_storage_mb``, ``estimated_embedding_mb``,
        and ``estimated_metadata_mb``, plus backend-level capacity fields
        (``database_used_mb``, ``database_data_mb``, ``database_index_mb``,
        ``database_storage_limit_mb``, ``database_free_mb``) which are ``None``
        when the backend cannot report a quota.

        Each ``experiments`` entry is the ``get_experiment_db_stats`` shape plus
        ``experiment_id``, ``experiment_name``, ``status``, and ``created_at``.
        """
        ...
