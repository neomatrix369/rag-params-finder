"""Split-store acceptance gaps left by the interrupted 49B verify pass.

Author: swami
Created: 2026-09-27
Scope: SLICE-49B GWT scenarios that /verify-slice marked unmet — partial
       delete retry, delete with zero chunks, vector-write on_error,
       pause/resume without re-embedding, legacy database_provider labels.
       The vector-only label-everywhere scenario is CF-49B-2 (Slice 50).
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

import server.core.pipeline.orchestrator as orchestrator
from server.api.experiments_shared import delete_experiment_data
from server.core.pipeline.experiment_control import request_pause
from server.core.pipeline.orchestrator import resume_sweep
from server.core.results_analyzer import analyze_results
from server.db.ports import registry as vector_store_registry
from server.models.config import expand_sweep
from server.settings import settings
from tests.fixtures.split_store import CHUNK_SIZE
from tests.fixtures.split_store.bow_embedder import build_vocabulary, make_embedder_pair
from tests.helpers.memory_vector_store import MemoryVectorStore
from tests.helpers.pipeline_sweep import FakeRunStateStore, _patch_backends
from tests.server.test_split_store_e2e import (
    _make_app,
    _split_store_config,
    _wait_for_terminal_status,
)

_EXPERIMENT_ID = "exp-split-recovery"
_CHUNK = {
    "chunk_id": "c1",
    "experiment_id": _EXPERIMENT_ID,
    "run_id": "run-1",
    "text": "alpha",
    "index": 0,
    "embedding": [1.0],
    "embedding_model": "all-MiniLM-L6-v2",
    "chunk_method": "recursive",
}


class _FailOnceVectorDelete(MemoryVectorStore):
    """Raises on the first chunk delete, then deletes normally."""

    def __init__(self) -> None:
        super().__init__()
        self.failures_remaining = 1

    def delete_chunks_for_experiment(self, experiment_id: str) -> int:
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise RuntimeError("vector-store delete failed")
        return super().delete_chunks_for_experiment(experiment_id)


class _FailOnceRunStateDelete(FakeRunStateStore):
    """Raises on the first cascade delete, then deletes normally."""

    def __init__(self) -> None:
        super().__init__()
        self.failures_remaining = 1

    def delete_experiment_data(self, experiment_id: str) -> dict[str, int]:
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise RuntimeError("run-state delete failed")
        return super().delete_experiment_data(experiment_id)


class _FailFirstUpsert(MemoryVectorStore):
    """Names the memory store in the first upsert error, then stores normally."""

    def __init__(self) -> None:
        super().__init__()
        self.failures_remaining = 1

    def insert_chunks(self, docs: list[dict]) -> None:
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise RuntimeError("memory vector store upsert failed")
        super().insert_chunks(docs)


class _PauseAfterFirstComplete(FakeRunStateStore):
    """Signals pause once the first run reaches COMPLETE."""

    def update_run_phase(
        self,
        run_id: str,
        *,
        phase: str,
        updated_at: object,
        elapsed_ms: int,
        error_message: str | None,
    ) -> None:
        super().update_run_phase(
            run_id,
            phase=phase,
            updated_at=updated_at,
            elapsed_ms=elapsed_ms,
            error_message=error_message,
        )
        row = self.run_status.get(run_id, {})
        experiment_id = row.get("experiment_id")
        if phase != "complete" or not experiment_id:
            return
        completed = [
            item
            for item in self.run_status.values()
            if item.get("experiment_id") == experiment_id and item.get("phase") == "complete"
        ]
        if len(completed) == 1:
            request_pause(str(experiment_id))


@pytest.fixture
def split_store_backends(monkeypatch: pytest.MonkeyPatch):
    """Register the memory vector store and patch storage plus vector factories."""
    monkeypatch.setattr(settings, "storage_backend", "mongodb")
    monkeypatch.setattr(settings, "vector_store_backend", "memory")
    monkeypatch.setattr(
        settings, "mongodb_atlas_local_uri", "mongodb://localhost:27017/split-store-e2e"
    )
    monkeypatch.setitem(
        vector_store_registry._VECTOR_STORE_REGISTRY,
        "memory",
        "tests.helpers.memory_vector_store:MemoryVectorStore",
    )
    storage = FakeRunStateStore()
    vector_store = MemoryVectorStore()
    with _patch_backends(storage=storage, vector_store=vector_store):
        yield storage, vector_store


@pytest.fixture
def split_store_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip index, SIE, and config-backend guards — this file proves delete and resume."""
    import server.api.experiments as experiments_api
    import server.core.pipeline.orchestrator as orchestrator

    for module in (experiments_api, orchestrator):
        monkeypatch.setattr(module, "validate_experiment_search_indexes", lambda config: None)
        monkeypatch.setattr(module, "validate_sie_readiness", lambda config: None)
    monkeypatch.setattr(experiments_api, "validate_config_backend_match", lambda config: None)
    monkeypatch.setattr(orchestrator.AimLogger, "log_run", lambda *_a, **_k: None)


def _wait_for_status(storage: FakeRunStateStore, experiment_id: str, statuses: set[str]) -> str:
    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline:
        doc = storage.find_experiment_by_id(experiment_id)
        status = doc.get("status") if doc else None
        if status in statuses:
            return str(status)
        time.sleep(0.1)
    last = storage.find_experiment_by_id(experiment_id)
    raise AssertionError(f"experiment {experiment_id} stayed at {last}, wanted {statuses}")


def _seed_experiment(storage: FakeRunStateStore, vector_store: MemoryVectorStore) -> None:
    storage.insert_experiment(
        {"experiment_id": _EXPERIMENT_ID, "status": "complete", "experiment_name": "recovery"}
    )
    vector_store.insert_chunks([dict(_CHUNK)])


def _two_run_config(on_error: str):
    """Two grid runs via chunk size — both models stay in the registry."""
    config = _split_store_config()
    config.chunking.params.chunk_sizes = [CHUNK_SIZE, CHUNK_SIZE + 40]
    config.execution.on_error = on_error  # type: ignore[assignment]
    return config


def _recording_embedder(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from tests.fixtures.split_store import DOCS_DIR, EXPECTED_KEYWORDS

    doc_texts = [path.read_text(encoding="utf-8") for path in sorted(DOCS_DIR.glob("*.txt"))]
    vocabulary = build_vocabulary(doc_texts + list(EXPECTED_KEYWORDS.keys()))
    embed_docs_fn, embed_query_fn = make_embedder_pair(vocabulary)
    recorded: list[str] = []

    def embed_docs(chunks: list[str], model: str, **kwargs: object) -> list[list[float]]:
        recorded.append(model)
        return embed_docs_fn(chunks, model, **kwargs)

    import server.core.pipeline.orchestrator as orchestrator

    monkeypatch.setattr(
        orchestrator, "get_embedder", lambda _provider: (embed_docs, embed_query_fn)
    )
    return recorded


class TestSplitStoreDeleteShould:
    def test_given_vector_delete_fails_when_delete_retried_then_both_stores_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Scenario: A partial delete is completed by a retry after the vector delete fails.
        Slice: 49B — delete across two stores

        Given the first DELETE raises while deleting vectors and leaves run state untouched,
        When DELETE is retried,
        Then both stores are empty and the reported chunk count matches what was removed.
        """
        ### Given
        monkeypatch.setattr(settings, "storage_backend", "mongodb")
        monkeypatch.setattr(settings, "vector_store_backend", "memory")
        monkeypatch.setitem(
            vector_store_registry._VECTOR_STORE_REGISTRY,
            "memory",
            "tests.helpers.memory_vector_store:MemoryVectorStore",
        )
        storage = FakeRunStateStore()
        vector_store = _FailOnceVectorDelete()
        _seed_experiment(storage, vector_store)

        ### When
        with _patch_backends(storage=storage, vector_store=vector_store):
            with pytest.raises(RuntimeError, match="vector-store delete failed"):
                delete_experiment_data(_EXPERIMENT_ID)
            actual_counts = delete_experiment_data(_EXPERIMENT_ID)

        ### Then
        assert storage.find_experiment_by_id(_EXPERIMENT_ID) is None, (
            "retry should remove the run-state experiment"
        )
        assert vector_store.chunks == [], "retry should remove vector-store chunks"
        assert actual_counts["chunks"] == 1, "retry should report the chunk that was still present"

    def test_given_run_state_delete_fails_when_delete_retried_then_chunk_count_is_zero(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Scenario: A partial delete is completed by a retry after run state fails.
        Slice: 49B — delete across two stores

        Given vectors were removed and the run-state delete then failed,
        When DELETE is retried,
        Then it succeeds and reports 0 chunks because the vector step is idempotent.
        """
        ### Given
        monkeypatch.setattr(settings, "storage_backend", "mongodb")
        monkeypatch.setattr(settings, "vector_store_backend", "memory")
        monkeypatch.setitem(
            vector_store_registry._VECTOR_STORE_REGISTRY,
            "memory",
            "tests.helpers.memory_vector_store:MemoryVectorStore",
        )
        storage = _FailOnceRunStateDelete()
        vector_store = MemoryVectorStore()
        _seed_experiment(storage, vector_store)

        ### When
        with _patch_backends(storage=storage, vector_store=vector_store):
            with pytest.raises(RuntimeError, match="run-state delete failed"):
                delete_experiment_data(_EXPERIMENT_ID)
            actual_counts = delete_experiment_data(_EXPERIMENT_ID)

        ### Then
        assert vector_store.chunks == [], "vector chunks stay gone after the failed run-state step"
        assert actual_counts["chunks"] == 0, "retry should report 0 chunks"
        assert storage.find_experiment_by_id(_EXPERIMENT_ID) is None, (
            "retry should finish the run-state delete"
        )

    def test_given_crash_between_delete_steps_when_delete_retried_then_run_state_is_removed(
        self, split_store_backends: tuple[FakeRunStateStore, MemoryVectorStore]
    ) -> None:
        """
        Scenario: A process crash between delete steps is completed by a retry.
        Slice: 49B — delete across two stores

        Given vector chunks are already gone and the run-state row remains,
        When DELETE runs again,
        Then the experiment is removed and the reported chunk count is 0.
        """
        storage, vector_store = split_store_backends

        ### Given
        _seed_experiment(storage, vector_store)
        vector_store.delete_chunks_for_experiment(_EXPERIMENT_ID)

        ### When
        actual_counts = delete_experiment_data(_EXPERIMENT_ID)

        ### Then
        assert actual_counts["chunks"] == 0, "crash recovery should report 0 chunks"
        assert storage.find_experiment_by_id(_EXPERIMENT_ID) is None, (
            "retry should remove the leftover run-state experiment"
        )

    def test_given_experiment_with_no_chunks_when_deleted_then_chunk_count_is_zero(
        self,
        split_store_backends: tuple[FakeRunStateStore, MemoryVectorStore],
        split_store_guards: None,
    ) -> None:
        """
        Scenario: Deleting an experiment with no chunks succeeds and reports 0.
        Slice: 49B — delete across two stores

        Given an experiment whose runs wrote no chunks,
        When DELETE /experiments/{id} runs,
        Then it succeeds and reports 0 chunks.
        """
        storage, _vector_store = split_store_backends

        ### Given
        storage.insert_experiment(
            {"experiment_id": _EXPERIMENT_ID, "status": "complete", "experiment_name": "empty"}
        )
        client = TestClient(_make_app())

        ### When
        response = client.delete(f"/experiments/{_EXPERIMENT_ID}")

        ### Then
        assert response.status_code == 200, response.text
        assert response.json()["deleted_counts"]["chunks"] == 0, (
            "an experiment that never wrote chunks should report 0"
        )


class TestSplitStoreOnErrorShould:
    @pytest.mark.parametrize(
        ("on_error", "expected_run_count"),
        [("continue", 2), ("stop", 1)],
    )
    def test_given_vector_write_fails_when_sweep_runs_then_on_error_is_honoured(
        self,
        on_error: str,
        expected_run_count: int,
        monkeypatch: pytest.MonkeyPatch,
        split_store_guards: None,
    ) -> None:
        """
        Scenario: A vector-store write failure fails the run and honours on_error.
        Slice: 49B — split-store sweep errors

        Given the memory vector store raises on the first upsert,
        When the sweep runs with on_error continue or stop,
        Then the failed run names the memory store, and stop does not start another run.
        """
        ### Given
        monkeypatch.setattr(settings, "storage_backend", "mongodb")
        monkeypatch.setattr(settings, "vector_store_backend", "memory")
        monkeypatch.setattr(
            settings, "mongodb_atlas_local_uri", "mongodb://localhost:27017/split-store-e2e"
        )
        monkeypatch.setitem(
            vector_store_registry._VECTOR_STORE_REGISTRY,
            "memory",
            "tests.helpers.memory_vector_store:MemoryVectorStore",
        )
        storage = FakeRunStateStore()
        vector_store = _FailFirstUpsert()
        _recording_embedder(monkeypatch)
        config = _two_run_config(on_error)
        client = TestClient(_make_app())

        ### When
        with _patch_backends(storage=storage, vector_store=vector_store):
            response = client.post("/experiments", json=config.model_dump(mode="json"))
            assert response.status_code == 200, response.text
            experiment_id = response.json()["experiment_id"]
            _wait_for_terminal_status(storage, experiment_id)
            runs = storage.find_run_statuses(experiment_id)

        ### Then
        failed = [run for run in runs if run.get("phase") == "failed"]
        assert failed, "the run whose vector write failed should be FAILED"
        assert "memory" in str(failed[0].get("error_message")), (
            "the failed run should name the memory vector store"
        )
        assert len(runs) == expected_run_count, (
            f"on_error={on_error} should leave {expected_run_count} run(s), found {len(runs)}"
        )


class TestSplitStoreResumeShould:
    def test_given_paused_split_store_sweep_when_resumed_then_completed_run_is_not_reembedded(
        self,
        monkeypatch: pytest.MonkeyPatch,
        split_store_guards: None,
    ) -> None:
        """
        Scenario: A paused and resumed split-store sweep does not re-embed completed runs.
        Slice: 49B — split-store resume

        Given a two-run sweep paused after the first run completed,
        When it is resumed,
        Then the embedder is not called again for the completed run's model
        and that run's chunk count is unchanged.
        """
        ### Given
        monkeypatch.setattr(settings, "storage_backend", "mongodb")
        monkeypatch.setattr(settings, "vector_store_backend", "memory")
        monkeypatch.setattr(
            settings, "mongodb_atlas_local_uri", "mongodb://localhost:27017/split-store-e2e"
        )
        monkeypatch.setitem(
            vector_store_registry._VECTOR_STORE_REGISTRY,
            "memory",
            "tests.helpers.memory_vector_store:MemoryVectorStore",
        )
        storage = _PauseAfterFirstComplete()
        vector_store = MemoryVectorStore()
        recorded = _recording_embedder(monkeypatch)
        config = _two_run_config("stop")
        client = TestClient(_make_app())

        ### When
        with _patch_backends(storage=storage, vector_store=vector_store):
            response = client.post("/experiments", json=config.model_dump(mode="json"))
            assert response.status_code == 200, response.text
            experiment_id = response.json()["experiment_id"]
            paused_status = _wait_for_status(storage, experiment_id, {"paused"})
            embeds_at_pause = len(recorded)
            chunks_before = [
                doc for doc in vector_store.chunks if doc.get("chunk_size") == CHUNK_SIZE
            ]
            resume_response = client.post(f"/experiments/{experiment_id}/resume")
            final_status = _wait_for_terminal_status(storage, experiment_id)
            chunks_after = [
                doc for doc in vector_store.chunks if doc.get("chunk_size") == CHUNK_SIZE
            ]

        ### Then
        assert paused_status == "paused", f"expected pause, got {paused_status}"
        assert resume_response.status_code == 200, resume_response.text
        assert embeds_at_pause == 1, "only the first run should embed before pause"
        assert len(recorded) == 2, "resume should embed only the run that had not completed"
        assert len(chunks_after) == len(chunks_before), (
            "chunk count for the completed run should be unchanged across resume"
        )
        assert final_status == "complete", storage.find_experiment_by_id(experiment_id)


class TestLegacyRunLabelShould:
    @pytest.mark.parametrize("run_state", ["mongodb", "postgres"])
    def test_given_run_without_database_provider_when_resumed_then_label_stays_run_state(
        self,
        run_state: str,
        monkeypatch: pytest.MonkeyPatch,
        split_store_backends: tuple[FakeRunStateStore, MemoryVectorStore],
    ) -> None:
        """
        Scenario: Runs persisted without database_provider keep their run-state label.
        Slice: 49B — legacy run labels

        Given a completed run row with no database_provider,
        When the experiment is resumed and its results are analysed,
        Then that run is not executed again and explore labels it with the run-state store.
        """
        storage, _vector_store = split_store_backends
        monkeypatch.setattr(settings, "storage_backend", run_state)
        if run_state == "postgres":
            monkeypatch.setattr(
                settings, "postgres_local_url", "postgresql://rag:rag@localhost/rag"
            )

        ### Given
        config = _split_store_config()
        config.database_provider = run_state  # type: ignore[assignment]
        params = expand_sweep(config)[0]
        experiment_id = _EXPERIMENT_ID
        run_doc = params.model_dump(mode="json")
        run_doc.pop("database_provider")
        run_doc.update(
            {
                "run_id": "run-legacy",
                "experiment_id": experiment_id,
                "phase": "complete",
            }
        )
        storage.insert_experiment(
            {
                "experiment_id": experiment_id,
                "status": "paused",
                "config": config.model_dump(mode="json"),
            }
        )
        storage.insert_run_status(run_doc)
        storage.insert_result(
            {
                "experiment_id": experiment_id,
                "run_id": "run-legacy",
                "query_text": "q",
                "results": [
                    {
                        "dense_score": 0.5,
                        "retrieval_method": "dense",
                        "chunk": {"text": "alpha", "embedding_model": params.embedding_model},
                    }
                ],
            }
        )
        calls: list[str] = []

        def embed_docs(chunks: list[str], model: str, **_kwargs: object) -> list[list[float]]:
            calls.append(model)
            return [[0.0] for _ in chunks]

        monkeypatch.setattr(
            orchestrator,
            "get_embedder",
            lambda _provider: (embed_docs, lambda *_a, **_k: [0.0]),
        )

        ### When
        resume_sweep(experiment_id, config)
        explored = analyze_results(
            storage.find_results_for_experiment(experiment_id),
            storage.find_run_statuses(experiment_id),
        )

        ### Then
        assert calls == [], "a completed legacy run must not be executed again on resume"
        assert explored["ranked_configs"][0]["database_provider"] == run_state, (
            "explore should label the legacy run with the run-state store"
        )
        assert explored["best_params"]["database_provider"] == run_state
        assert explored["detailed_results"][0]["database_provider"] == run_state
