"""Split-store E2E acceptance test — Slice 49B (RED against 49A wiring).

Author: Claude (Stream 1)
Created: 2026-09-27
Scope: SLICE-49B-VECTOR-STORE-DATA-PATH-REWIRE.md, "Spec (GWT)" — the first
       two scenarios:

  Scenario: A split-store sweep writes, finds, reports and deletes through
            the vector store
  Scenario: The same test fails on the 49A wiring (detects the defect)

This test is the defect detector for DECISIONS #240: with 49A code
(chunks still written via ``get_storage_backend().insert_chunks(...)`` at
``server/core/pipeline/orchestrator.py``), a split-store setup
(``VECTOR_STORE_BACKEND=memory`` while ``STORAGE_BACKEND=mongodb``) writes
every chunk to the run-state double instead of the vector-store double.
The test fails on the very first assertion — chunks land in the vector
store — for that reason, not an import/fixture/timeout error. Stream 2
rewires the chunk data path onto ``get_vector_store()`` to turn this GREEN
without editing this file.

Test infrastructure this exercises (all authored in this same commit
sequence — see the module docstrings for detail):
  - ``tests/helpers/memory_vector_store.py`` — in-memory ``VectorStore``
    double (``MemoryVectorStore`` / ``MemoryRetrieverBackend``).
  - ``tests/fixtures/split_store/`` — known-answer corpus + queries +
    deterministic bag-of-words test embedder.
  - ``tests/helpers/pipeline_sweep.py::_patch_backends`` /
    ``FakeRunStateStore`` — patches ``get_storage_backend`` /
    ``get_vector_store`` / ``get_retriever_backend`` together so the sweep
    runs fully in-process, with no live Mongo/Postgres/Elasticsearch.

Settings note: the 49A equality lock
(``Settings.vector_store_backend_must_be_known_and_locked``) only runs at
``Settings(**kwargs)`` construction time (a pydantic ``model_validator``).
This test never reconstructs the module-level ``server.settings.settings``
singleton — it monkeypatches its already-validated attributes directly
(the same pattern ``tests/server/test_vector_store_characterization.py``
uses for exceptional settings), which never re-invokes the validator. That
is how the 49A lock is lifted for this test only, without touching
``server/settings.py`` (Stream 2's job, via pairing rule (ii)).
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.db.ports import registry as vector_store_registry
from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
    RetrieverConfig,
)
from server.models.enums import ChunkingMethod, RetrieverType
from server.settings import settings
from tests.fixtures.split_store import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DOCS_DIR,
    EXPECTED_KEYWORDS,
    QUERIES_FILE,
)
from tests.fixtures.split_store.bow_embedder import build_vocabulary, make_embedder_pair
from tests.helpers.memory_vector_store import MemoryVectorStore
from tests.helpers.pipeline_sweep import FakeRunStateStore, _patch_backends

_POLL_TIMEOUT_S = 20.0
_POLL_INTERVAL_S = 0.1
_TERMINAL_STATUSES = {"complete", "partial", "failed", "cancelled"}


def _split_store_config() -> ExperimentConfig:
    """One grid run — a single (model, chunking, retriever) combination.

    chunk_size=220/overlap=0 is the exact value the fixture corpus was
    designed against (see tests/fixtures/split_store/__init__.py) — each of
    the 5 short documents becomes exactly one chunk under
    RecursiveCharacterTextSplitter.
    """
    return ExperimentConfig(
        experiment_name="split-store-e2e",
        data_paths=[str(DOCS_DIR)],
        queries_file=str(QUERIES_FILE),
        database_provider="mongodb",  # config <-> backend guard is patched out below
        embedding=EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
        chunking=ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[CHUNK_SIZE], overlaps=[CHUNK_OVERLAP], paddings=[0]),
        ),
        retrieval=RetrievalConfig(
            retrievers=[RetrieverConfig(type=RetrieverType.DENSE)],
            top_k_initial=5,
            top_k_final=3,
        ),
        execution=ExecutionConfig(parallelism=1, on_error="stop"),
    )


def _bow_embedder_pair() -> tuple[Any, Any]:
    doc_texts = [path.read_text(encoding="utf-8") for path in sorted(DOCS_DIR.glob("*.txt"))]
    query_texts = list(EXPECTED_KEYWORDS.keys())
    vocabulary = build_vocabulary(doc_texts + query_texts)
    return make_embedder_pair(vocabulary)


def _make_app() -> FastAPI:
    """Minimal app — only the experiments router, no lifespan/mongo/voyageai imports.

    Mirrors server/main.py's ``app.include_router(experiments.router,
    prefix="/experiments", ...)`` without importing server.main itself (same
    rationale as tests/server/api/test_sweep_endpoint.py: avoid pulling in
    mongo/voyageai/torch at collection time).
    """
    app = FastAPI()
    from server.api import experiments

    app.include_router(experiments.router, prefix="/experiments")
    return app


def _wait_for_terminal_status(storage: FakeRunStateStore, experiment_id: str) -> str:
    """Poll the fake run-state store until the sweep (running on the real
    background sweep executor — schedule_sweep -> SWEEP_EXECUTOR) finishes."""
    deadline = time.monotonic() + _POLL_TIMEOUT_S
    while time.monotonic() < deadline:
        doc = storage.find_experiment_by_id(experiment_id)
        status = doc.get("status") if doc else None
        if status in _TERMINAL_STATUSES:
            return str(status)
        time.sleep(_POLL_INTERVAL_S)
    raise AssertionError(
        f"experiment {experiment_id} did not reach a terminal status within "
        f"{_POLL_TIMEOUT_S}s (last status={storage.find_experiment_by_id(experiment_id)})"
    )


@pytest.fixture
def split_store_backends(monkeypatch: pytest.MonkeyPatch):
    """Lift the 49A lock + register 'memory' + patch every factory call site.

    Returns (storage, vector_store) so the test can inspect both fakes'
    final state directly, in addition to what the HTTP responses report.
    """
    # Lift the 49A equality lock for this test's settings only — mutating the
    # already-validated singleton never re-runs
    # Settings.vector_store_backend_must_be_known_and_locked (that validator
    # only fires at Settings(**kwargs) construction time).
    monkeypatch.setattr(settings, "storage_backend", "mongodb")
    monkeypatch.setattr(settings, "vector_store_backend", "memory")
    monkeypatch.setattr(settings, "mongodb_uri", "mongodb://localhost:27017/split-store-e2e")

    # Register the in-memory adapter under "memory" for this test only —
    # production code (server/db/ports/registry.py) is never edited.
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
def split_store_guards(monkeypatch: pytest.MonkeyPatch):
    """No-op the preflight/backend-match guards — this test proves the chunk
    data-path defect, not Atlas/Postgres/SIE preflight behaviour (those have
    their own characterization suites)."""
    import server.api.experiments as experiments_api
    import server.core.pipeline.orchestrator as orchestrator

    for module in (experiments_api, orchestrator):
        monkeypatch.setattr(module, "validate_experiment_search_indexes", lambda config: None)
        monkeypatch.setattr(module, "validate_sie_readiness", lambda config: None)
    monkeypatch.setattr(experiments_api, "validate_config_backend_match", lambda config: None)
    monkeypatch.setattr(orchestrator.AimLogger, "log_run", lambda *_a, **_k: None)


@pytest.fixture
def split_store_embedder(monkeypatch: pytest.MonkeyPatch):
    """Deterministic bag-of-words embedder — no model download, no network."""
    import server.core.pipeline.orchestrator as orchestrator

    embed_docs_fn, embed_query_fn = _bow_embedder_pair()
    monkeypatch.setattr(
        orchestrator, "get_embedder", lambda _provider: (embed_docs_fn, embed_query_fn)
    )


class TestSplitStoreSweepShould:
    """Scenario: a split-store sweep writes, finds, reports and deletes
    through the vector store (SLICE-49B GWT, first scenario) — and its RED
    counterpart, "the same test fails on the 49A wiring"."""

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Slice 49B RED (DECISIONS #240/#242) — chunks are still written via "
            "get_storage_backend().insert_chunks(...) at "
            "server/core/pipeline/orchestrator.py's _run_single, not through "
            "get_vector_store(). Stream 2 rewires that call site onto the vector "
            "store; remove this marker once GREEN (gate-evidence/slice-49b.json "
            "red_run captures this exact failure)."
        ),
    )
    def test_given_split_store_config_when_sweep_runs_then_chunks_land_only_in_vector_store(
        self,
        split_store_backends: tuple[FakeRunStateStore, MemoryVectorStore],
        split_store_guards: None,
        split_store_embedder: None,
    ) -> None:
        """
        Scenario: A split-store sweep writes, finds, reports and deletes
        through the vector store.

        Given run state on the configured run-state store (a fake standing
              in for mongodb/postgres), VECTOR_STORE_BACKEND=memory, and the
              known-answer fixture corpus with 5 queries,
        When the experiment is submitted with POST /experiments (FastAPI
             TestClient) and the sweep runs through run_sweep
             (orchestrator.py:84), not adapter calls directly,
        Then chunks are written only to the vector store (the run-state
             store holds none) and every query returns hits and for at
             least 4 of the 5 queries the known relevant passage ranks in
             the top 3.

        RED counterpart ("the same test fails on the 49A wiring", SLICE-49B
        GWT second scenario): against unmodified 49A code (chunks still
        routed through ``get_storage_backend().insert_chunks(...)`` at
        ``orchestrator.py`` — see that module's ``_run_single``), this
        assertion fails first, and specifically on "chunks are written to
        the vector store" — the run-state fake holds every chunk instead.
        """
        storage, vector_store = split_store_backends

        ### Given
        config = _split_store_config()
        app = _make_app()
        client = TestClient(app)

        ### When
        response = client.post("/experiments", json=config.model_dump(mode="json"))
        assert response.status_code == 200, response.text
        experiment_id = response.json()["experiment_id"]

        final_status = _wait_for_terminal_status(storage, experiment_id)

        ### Then
        # 1) Chunks are written only to the vector store — the run-state
        #    store holds none. This is the defect-detector assertion: it
        #    fails on 49A wiring, where insert_chunks still goes to `storage`.
        assert len(vector_store.chunks) > 0, (
            "expected chunks written to the vector store, found none — "
            f"run-state store holds {len(storage.chunks)} chunk(s) instead "
            f"(final experiment status={final_status})"
        )
        assert len(storage.chunks) == 0, (
            "chunks were written to the vector store, but the run-state "
            f"store also holds {len(storage.chunks)} chunk(s) — expected "
            "the run-state store to hold none"
        )

        # 2) Every query returns hits, and >= 4/5 rank the known passage top-3.
        assert final_status == "complete", storage.find_experiment_by_id(experiment_id)
        results = storage.find_results_for_experiment(experiment_id)
        assert len(results) == len(EXPECTED_KEYWORDS), (
            f"expected {len(EXPECTED_KEYWORDS)} query results, got {len(results)}"
        )

        hits_in_top_3 = 0
        for row in results:
            query_text = row["query_text"]
            hits = row["results"]
            assert hits, f"query {query_text!r} returned no hits"
            expected_keyword = EXPECTED_KEYWORDS[query_text]
            top_3_texts = [hit["chunk"]["text"].lower() for hit in hits[:3]]
            if any(expected_keyword in text for text in top_3_texts):
                hits_in_top_3 += 1

        assert hits_in_top_3 >= 4, (
            f"expected >= 4/5 queries to rank their known passage in the "
            f"top 3, got {hits_in_top_3}/5"
        )

        # 3) DELETE reports the written chunk count and empties both stores.
        written_chunk_count = len(vector_store.chunks)
        delete_response = client.delete(f"/experiments/{experiment_id}")
        assert delete_response.status_code == 200, delete_response.text
        assert delete_response.json()["deleted_counts"]["chunks"] == written_chunk_count
        assert len(vector_store.chunks) == 0
        assert len(storage.chunks) == 0

        # 4) A second DELETE reports 0 chunks and does not error.
        second_delete = client.delete(f"/experiments/{experiment_id}")
        assert second_delete.status_code == 404  # already deleted — no double-delete 500
