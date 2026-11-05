"""Seam test: the real run path persists the golden count and writes one row per query.

Author: Mani Sarkar
Created: 2026-11-05
Scope: Slice 67E — drives ``_run_single`` (not the helper) against a real SQLite
       run-state store and a 3-record queries file, with embedding, chunking and
       retrieval stubbed. Witnesses that ``sweep_summary.golden_queries`` equals the
       dataset record count and that exactly that many result rows are written.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from server.core.pipeline import orchestrator
from server.core.pipeline.orchestrator import _run_single
from server.models.enums import ExperimentStatus
from server.models.results import Chunk, SearchResult
from tests.helpers.pipeline_sweep import _patch_backends, _run_param


@pytest.fixture()
def sqlite_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import server.db.sqlite.sqlite_store as store_module

    monkeypatch.setattr("server.settings.settings.sqlite_db_path", str(tmp_path / "rs.db"))
    store_module._local.__dict__.clear()
    store_module._storage = None
    orchestrator._golden_persisted.clear()
    yield store_module.SQLiteStorageBackend()
    orchestrator._golden_persisted.clear()


def _queries_file(tmp_path: Path) -> str:
    """Three records over two personas, two of them with identical text."""
    path = tmp_path / "golden.json"
    path.write_text(
        json.dumps(
            {
                "personas": [
                    {"id": "a", "questions": [{"text": "same"}, {"text": "same"}]},
                    {"id": "b", "questions": [{"text": "other"}]},
                ]
            }
        )
    )
    return str(path)


def test_run_single_persists_golden_count_and_writes_one_row_per_query(
    sqlite_store, tmp_path: Path
) -> None:
    """
    Scenario: the real run path persists the dataset record count and one row per query.
    Slice: 67E

    Given a 3-record queries file and an experiment without golden_queries
    When _run_single executes one run with stubbed embedding and retrieval
    Then sweep_summary.golden_queries is 3 and exactly 3 result rows exist for the run,
    each embedding both retrieved hits (rows are per query, not per hit).
    """
    ### Given
    sqlite_store.insert_experiment(
        {
            "_id": "exp-seam",
            "experiment_id": "exp-seam",
            "experiment_name": "seam",
            "status": ExperimentStatus.RUNNING,
            "created_at": datetime(2026, 11, 5, tzinfo=UTC),
            "sweep_summary": {"database_provider": "sqlite", "models": ["m"]},
        }
    )
    params = _run_param()
    params.queries_file = _queries_file(tmp_path)
    hits = [
        SearchResult(
            chunk=Chunk(
                id=f"c{rank}",
                text="t",
                index=rank,
                embedding_model="all-MiniLM-L6-v2",
                chunk_method="recursive",
            ),
            dense_score=0.9,
            rerank_score=None,
            retrieval_method="dense",
            rank=rank,
        )
        for rank in (1, 2)
    ]

    with (
        patch("server.core.pipeline.orchestrator.AimLogger"),
        patch(
            "server.core.pipeline.orchestrator._search_traditional_retriever",
            return_value=(hits, [0.1]),
        ),
        patch(
            "server.core.pipeline.orchestrator.get_embedder",
            return_value=(
                lambda chunks, _model, cancel_check=None, **_kw: [[0.1] for _ in chunks],
                lambda text, model: [0.1],
            ),
        ),
        patch("server.core.pipeline.orchestrator.chunk_text", return_value=["c"]),
        patch("server.core.pipeline.orchestrator.load_all_files", return_value="text"),
        patch("server.core.pipeline.orchestrator.check_control", return_value=None),
        _patch_backends(storage=sqlite_store, vector_store=MagicMock(name="VectorStore")),
    ):
        ### When
        _run_single("exp-seam", "run-1", params)

    ### Then
    experiment = sqlite_store.find_experiment_by_id("exp-seam")
    assert experiment["sweep_summary"]["golden_queries"] == 3
    assert experiment["sweep_summary"]["models"] == ["m"]
    rows = [
        r for r in sqlite_store.list_results_for_experiment("exp-seam") if r["run_id"] == "run-1"
    ]
    assert len(rows) == 3
    assert len(rows[0]["results"]) == 2
