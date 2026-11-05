"""Verifies the SLICE-56 Part A demo-data exporter against tiny temp SQLite run-state files.

Author: Mani Sarkar
Created: 2026-11-05
Scope: scripts/demo/export_demo_results.py — manifest, selection rule, ranking reuse,
       improvement story, size cap, determinism and read-only access; no live data.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts.demo.export_demo_results import apply_run_id_tiebreak, main
from tests.helpers.repo_paths import repo_root_from

_REPO = repo_root_from(Path(__file__))
_SCHEMA = (_REPO / "server" / "db" / "sqlite" / "schema.sql").read_text()

PELL = "./input_data/pdfs/The_Federal_Pell_Grant_Program.pdf"
OTHER_PDF = "./input_data/pdfs/sample.pdf"
QUESTIONS_REF = "./configs/questions.example.json"
Q1 = "How much can I borrow for my degree program?"
Q2 = "When do I need to start repaying my loans?"
LONG_TEXT = "Pell\tGrant " * 40  # 400 characters, tabs included


@dataclass
class RunSpec:
    """One run to seed: chunk size distinguishes the config, scores the retrieval quality."""

    run_id: str
    chunk_size: int
    scores: dict[str, list[float]]
    phase: str = "complete"
    chunking_method: str = "fixed"
    provider_recorded: bool = True


@dataclass
class ExperimentSpec:
    """One experiment to seed into a temp run-state database."""

    experiment_id: str
    store: str
    runs: Sequence[RunSpec]
    status: str = "complete"
    created_at: str = "2026-10-01T10:00:00+00:00"
    data_paths: list[str] = field(default_factory=lambda: [PELL])
    queries_file: str = QUESTIONS_REF


def _result_doc(spec: ExperimentSpec, run: RunSpec, question: str, scores: list[float]) -> dict:
    return {
        "persona_id": "p",
        "focus": "General",
        "results": [
            {
                "chunk": {
                    "id": f"{run.run_id}_{i}",
                    "text": f"{LONG_TEXT} #{i}",
                    "index": i,
                    "embedding_model": "all-MiniLM-L6-v2",
                    "chunk_method": run.chunking_method,
                },
                "dense_score": score,
                "rerank_score": None,
                "retrieval_method": "dense",
                "rank": i + 1,
            }
            for i, score in enumerate(scores)
        ],
    }


def make_db(path: Path, experiments: Sequence[ExperimentSpec]) -> Path:
    """Create a run-state SQLite file (real schema) holding the given experiments."""
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA)
    for exp in experiments:
        config = {
            "experiment_name": exp.experiment_id,
            "data_paths": exp.data_paths,
            "queries_file": exp.queries_file,
            "database_provider": exp.store,
        }
        conn.execute(
            "INSERT INTO experiments (experiment_id, experiment_name, status, created_at,"
            " completed_at, doc) VALUES (?, ?, ?, ?, ?, ?)",
            (
                exp.experiment_id,
                exp.experiment_id,
                exp.status,
                exp.created_at,
                exp.created_at,
                json.dumps({"config": config}),
            ),
        )
        for run in exp.runs:
            run_doc: dict[str, Any] = {
                "embedding_provider": "local",
                "embedding_model": "all-MiniLM-L6-v2",
                "chunking_method": run.chunking_method,
                "chunk_size": run.chunk_size,
                "overlap": 50,
                "padding": 0,
                "retrievers": [{"type": "dense", "provider": None, "model": None}],
                "retrieval_method": "dense",
                "retrieval_provider": "local",
                "retrieval_model": None,
                "elapsed_ms": 1000 + run.chunk_size,
            }
            if run.provider_recorded:
                run_doc["database_provider"] = exp.store
            conn.execute(
                "INSERT INTO run_status (run_id, experiment_id, phase, created_at, updated_at,"
                " doc) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    run.run_id,
                    exp.experiment_id,
                    run.phase,
                    exp.created_at,
                    exp.created_at,
                    json.dumps(run_doc),
                ),
            )
            for n, (question, scores) in enumerate(sorted(run.scores.items())):
                conn.execute(
                    "INSERT INTO results (experiment_id, run_id, query_id, query_text, doc)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (
                        exp.experiment_id,
                        run.run_id,
                        f"{run.run_id}-q{n}",
                        question,
                        json.dumps(_result_doc(exp, run, question, scores)),
                    ),
                )
    conn.commit()
    conn.close()
    return path


def make_questions(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "personas": [
                    {
                        "id": "p",
                        "questions": [
                            {"text": Q1, "focus": "Borrowing"},
                            {"text": Q2, "focus": "Repayment"},
                        ],
                    }
                ]
            }
        )
    )
    return path


def three_runs(prefix: str, *, delta: float = 0.0) -> list[RunSpec]:
    """Three configs (256 best, 512 middle, 1024 worst); Q1 shows the widest top-1 gap."""
    return [
        RunSpec(f"{prefix}-a", 256, {Q1: [0.9 - delta, 0.8], Q2: [0.7, 0.6]}),
        RunSpec(f"{prefix}-b", 512, {Q1: [0.6, 0.5], Q2: [0.6, 0.5]}),
        RunSpec(f"{prefix}-c", 1024, {Q1: [0.3, 0.2], Q2: [0.4, 0.1]}),
    ]


@pytest.fixture
def questions(tmp_path: Path) -> Path:
    return make_questions(tmp_path / "questions.example.json")


@pytest.fixture
def cross_store_db(tmp_path: Path) -> Path:
    """Redis (3 runs) plus mongodb (3 runs, same configs) and postgres (2 of the 3 configs)."""
    return make_db(
        tmp_path / "state.db",
        [
            ExperimentSpec("e-redis", "redis", three_runs("r")),
            ExperimentSpec("e-mongo", "mongodb", three_runs("m", delta=0.1)),
            ExperimentSpec("e-pg", "postgres", three_runs("p")[:2]),
        ],
    )


def export(
    tmp_path: Path, dbs: Sequence[Path], questions: Path, *extra: str, name: str = "out.json"
) -> tuple[int, Path]:
    out = tmp_path / name
    argv: list[str] = []
    for db in dbs:
        argv += ["--db", str(db)]
    argv += ["--questions", str(questions), "--out", str(out), *extra]
    return main(argv), out


def load(out: Path) -> dict[str, Any]:
    return json.loads(out.read_text())


def runs_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {r["run_id"]: r for r in payload["runs"]}


def test_given_inputs_when_exported_then_manifest_records_inputs_ranking_and_rules(
    tmp_path: Path, cross_store_db: Path, questions: Path
) -> None:
    """
    Scenario: The manifest explains where the numbers came from.
    Slice: 56 (Part A)

    Given a run-state database and a questions file,
    When the exporter runs,
    Then the manifest lists each input with its sha256, the ranking, the selection rule,
    the exclusions and a schema_version.
    """
    ### Given
    db = cross_store_db

    ### When
    code, out = export(tmp_path, [db], questions)

    ### Then
    assert code == 0
    payload = load(out)
    manifest = payload["manifest"]
    assert payload["schema_version"] == manifest["schema_version"] == 1
    assert manifest["inputs"]["databases"] == [
        {"path": str(db), "sha256": hashlib.sha256(db.read_bytes()).hexdigest()}
    ]
    assert manifest["inputs"]["questions"] == {
        "path": str(questions),
        "sha256": hashlib.sha256(questions.read_bytes()).hexdigest(),
    }
    assert manifest["ranking"]["fields"] == [
        "max_score DESC",
        "query_avg_score DESC",
        "chunk_size ASC",
        "overlap ASC",
        "padding ASC",
        "run_id ASC",
    ]
    assert "similarity" in manifest["ranking"]["score"]
    assert "median" in manifest["selection_rule"] and "floor((n-1)/2)" in manifest["selection_rule"]
    assert isinstance(manifest["exclusions"], list)


def test_given_redis_and_other_stores_when_exported_then_each_config_carries_every_store(
    tmp_path: Path, cross_store_db: Path, questions: Path
) -> None:
    """
    Scenario: Same-config runs on other stores travel with the Redis runs.
    Slice: 56 (Part A)

    Given Redis runs and mongodb/postgres runs of the same configs,
    When exported,
    Then every Redis run is present and each Redis config group lists the runs of the other
    stores that share it (postgres only has two of the three).
    """
    ### Given
    db = cross_store_db

    ### When
    code, out = export(tmp_path, [db], questions)

    ### Then
    assert code == 0
    runs = runs_by_id(load(out))
    assert set(runs) == {"r-a", "r-b", "r-c", "m-a", "m-b", "m-c", "p-a", "p-b"}
    groups: dict[str, set[str]] = {}
    for run in runs.values():
        groups.setdefault(run["group_id"], set()).add(run["store"])
    assert sorted(len(stores) for stores in groups.values()) == [2, 3, 3]


def test_given_runs_on_other_dataset_or_questions_when_exported_then_never_paired(
    tmp_path: Path, questions: Path
) -> None:
    """
    Scenario: Runs of a different dataset or questions file are not exported next to Redis.
    Slice: 56 (Part A)

    Given Redis runs on the Pell PDF and mongodb runs on sample.pdf plus postgres runs that
    used a different questions file,
    When exported,
    Then neither of those runs appears, and the manifest says why.
    """
    ### Given
    db = make_db(
        tmp_path / "state.db",
        [
            ExperimentSpec("e-redis", "redis", three_runs("r")),
            ExperimentSpec("e-mongo", "mongodb", three_runs("m"), data_paths=[OTHER_PDF]),
            ExperimentSpec(
                "e-pg", "postgres", three_runs("p"), queries_file="./configs/other-questions.json"
            ),
        ],
    )

    ### When
    code, out = export(tmp_path, [db], questions)

    ### Then
    assert code == 0
    payload = load(out)
    assert set(runs_by_id(payload)) == {"r-a", "r-b", "r-c"}
    reasons = {e["reason"] for e in payload["manifest"]["exclusions"]}
    assert any("questions file" in r for r in reasons)
    assert any("not run on the primary store" in r for r in reasons)


def test_given_several_runs_per_store_when_exported_then_best_median_worst_are_marked(
    tmp_path: Path, cross_store_db: Path, questions: Path
) -> None:
    """
    Scenario: Each store contributes best, median (floor((n-1)/2)) and worst.
    Slice: 56 (Part A)

    Given mongodb with three ranked runs and postgres with two,
    When exported,
    Then mongodb best/median/worst are its 1st/2nd/3rd run and postgres median is its 1st
    (floor((2-1)/2) = 0).
    """
    ### Given
    db = cross_store_db

    ### When
    _, out = export(tmp_path, [db], questions)

    ### Then
    stores = load(out)["stores"]
    assert (stores["mongodb"]["best_run_id"], stores["mongodb"]["median_run_id"]) == ("m-a", "m-b")
    assert stores["mongodb"]["worst_run_id"] == "m-c"
    assert stores["postgres"]["median_run_id"] == stores["postgres"]["best_run_id"] == "p-a"
    assert stores["postgres"]["worst_run_id"] == "p-b"
    assert stores["redis"]["run_count"] == 3


def test_given_union_when_exported_then_ranking_comes_from_analyze_results_once(
    tmp_path: Path, cross_store_db: Path, questions: Path
) -> None:
    """
    Scenario: Scores are normalised across the whole export, not per store.
    Slice: 56 (Part A)

    Given redis best run scoring 0.9 and mongodb best run scoring 0.8 (the min is 0.1),
    When exported,
    Then both are scored on one scale: redis max 100, mongodb best below it, and the overall
    ranking is highest max_score first.
    """
    ### Given
    db = cross_store_db

    ### When
    _, out = export(tmp_path, [db], questions)

    ### Then
    runs = runs_by_id(load(out))
    assert runs["r-a"]["max_score"] == 100
    assert runs["m-a"]["max_score"] == round((0.8 - 0.1) / 0.8 * 100)
    ordered = sorted(runs.values(), key=lambda r: r["rank"])
    assert [r["max_score"] for r in ordered] == sorted(
        (r["max_score"] for r in ordered), reverse=True
    )
    assert [r["rank"] for r in ordered] == list(range(1, len(ordered) + 1))


def test_given_tied_scores_when_exported_then_run_id_is_the_final_tiebreak(
    tmp_path: Path, questions: Path
) -> None:
    """
    Scenario: Equal scores never leave the order to chance.
    Slice: 56 (Part A)

    Given two Redis runs that differ only in chunking method (identical scores and sizes)
    seeded with the higher run id first,
    When exported,
    Then the lower run id ranks first.
    """
    ### Given
    same = {Q1: [0.5, 0.4], Q2: [0.5, 0.4]}
    db = make_db(
        tmp_path / "state.db",
        [
            ExperimentSpec(
                "e-redis",
                "redis",
                [
                    RunSpec("z-run", 256, same, chunking_method="token"),
                    RunSpec("a-run", 256, same, chunking_method="fixed"),
                ],
            )
        ],
    )

    ### When
    _, out = export(tmp_path, [db], questions)

    ### Then
    runs = runs_by_id(load(out))
    assert runs["a-run"]["rank"] == 1
    assert runs["z-run"]["rank"] == 2


def test_given_fully_tied_configs_in_reverse_order_when_tiebroken_then_run_id_ascends() -> None:
    """
    Scenario: The exporter's own tie-break does not depend on input order.
    Slice: 56 (Part A)

    Given three ranked entries with identical scores and sizes, handed over in descending
    run-id order, and one lower-scored entry after them,
    When the run-id tie-break is applied,
    Then the tied entries come back in ascending run-id order and the lower one stays last.
    """
    ### Given
    tied = {
        "max_score": 80,
        "query_avg_score": 50,
        "avg_score": 50,
        "chunk_size": 256,
        "overlap": 50,
        "padding": 0,
    }
    lower = {**tied, "max_score": 10}
    ranked = [
        (dict(tied), SimpleNamespace(run_id="c")),
        (dict(tied), SimpleNamespace(run_id="a")),
        (dict(tied), SimpleNamespace(run_id="b")),
        (dict(lower), SimpleNamespace(run_id="0")),
    ]

    ### When
    ordered = apply_run_id_tiebreak(ranked)  # type: ignore[arg-type]

    ### Then
    assert [cand.run_id for _, cand in ordered] == ["a", "b", "c", "0"]


def test_given_no_redis_run_when_exported_then_it_fails_clearly(
    tmp_path: Path, questions: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    Scenario: Nothing is exported without a Redis run.
    Slice: 56 (Part A)

    Given a database that only holds mongodb runs,
    When the exporter runs,
    Then it exits non-zero with a message naming Redis and writes no file.
    """
    ### Given
    db = make_db(tmp_path / "state.db", [ExperimentSpec("e-mongo", "mongodb", three_runs("m"))])

    ### When
    code, out = export(tmp_path, [db], questions)

    ### Then
    assert code == 1
    assert "no exportable redis run" in capsys.readouterr().err.lower()
    assert not out.exists()


@pytest.mark.parametrize(
    ("flag", "value"),
    [("--max-runs", "2"), ("--max-bytes", "500")],
    ids=["run-count-cap", "byte-cap"],
)
def test_given_export_over_cap_when_exported_then_it_stops_and_asks_without_dropping(
    tmp_path: Path,
    cross_store_db: Path,
    questions: Path,
    capsys: pytest.CaptureFixture[str],
    flag: str,
    value: str,
) -> None:
    """
    Scenario: A too-large export stops instead of silently dropping runs.
    Slice: 56 (Part A)

    Given a cap lower than the selected export,
    When the exporter runs,
    Then it exits with code 2, asks for a selection rule and writes no output file.
    """
    ### Given
    db = cross_store_db

    ### When
    code, out = export(tmp_path, [db], questions, flag, value)

    ### Then
    assert code == 2
    err = capsys.readouterr().err
    assert "selection rule" in err and "no run was dropped" in err
    assert not out.exists()


def test_given_export_when_story_built_then_it_reports_spread_and_the_widest_gap_question(
    tmp_path: Path,
    cross_store_db: Path,
    questions: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    Scenario: The improvement story compares the best and worst Redis run.
    Slice: 56 (Part A)

    Given Redis runs a (best), b (median) and c (worst) where Q1 has the widest top-1 gap,
    When exported,
    Then the story gives best/median/worst scores and the spread, names Q1 with both runs' top
    chunks (text at most 200 characters) and the question is printed.
    """
    ### Given
    db = cross_store_db

    ### When
    _, out = export(tmp_path, [db], questions)

    ### Then
    story = load(out)["story"]
    assert [story[k]["run_id"] for k in ("best", "median", "worst")] == ["r-a", "r-b", "r-c"]
    assert story["spread"]["max_score"] == story["best"]["max_score"] - story["worst"]["max_score"]
    assert story["question"]["text"] == Q1
    assert story["question"]["focus"] == "Borrowing"
    assert (
        story["question"]["gap"] == story["question"]["best_top1"] - story["question"]["worst_top1"]
    )
    assert story["question"]["gap"] == 75
    for side in ("best_top_chunks", "worst_top_chunks"):
        assert story[side], side
        assert all(len(c["chunk_text"]) <= 200 for c in story[side])
    assert {c["run_id"] for c in story["best_top_chunks"]} == {"r-a"}
    assert {c["run_id"] for c in story["worst_top_chunks"]} == {"r-c"}
    assert Q1 in capsys.readouterr().out


def test_given_same_inputs_when_exported_twice_then_bytes_are_identical(
    tmp_path: Path, cross_store_db: Path, questions: Path
) -> None:
    """
    Scenario: The export is reproducible.
    Slice: 56 (Part A)

    Given one database and questions file,
    When the exporter runs twice to different output paths,
    Then both outputs are byte-identical.
    """
    ### Given
    db = cross_store_db

    ### When
    _, first = export(tmp_path, [db], questions, name="one.json")
    _, second = export(tmp_path, [db], questions, name="two.json")

    ### Then
    assert first.read_bytes() == second.read_bytes()


def test_given_older_and_incomplete_experiments_when_exported_then_latest_complete_wins(
    tmp_path: Path, questions: Path
) -> None:
    """
    Scenario: Only the latest completed experiment per store and config is used.
    Slice: 56 (Part A)

    Given a store with an older complete experiment, a newer complete one, a partial one and a
    run that did not finish,
    When exported,
    Then only the newer complete experiment's runs appear, and every other run is listed in the
    manifest exclusions with a reason.
    """
    ### Given
    old = [RunSpec("old-a", 256, {Q1: [0.2, 0.1], Q2: [0.2, 0.1]})]
    new = [
        RunSpec("new-a", 256, {Q1: [0.9, 0.8], Q2: [0.7, 0.6]}),
        RunSpec("new-failed", 512, {Q1: [0.9]}, phase="failed"),
    ]
    db = make_db(
        tmp_path / "state.db",
        [
            ExperimentSpec("e-old", "redis", old, created_at="2026-09-01T10:00:00+00:00"),
            ExperimentSpec("e-new", "redis", new, created_at="2026-10-01T10:00:00+00:00"),
            ExperimentSpec(
                "e-part",
                "redis",
                three_runs("pt"),
                status="partial",
                created_at="2026-10-02T10:00:00+00:00",
            ),
        ],
    )

    ### When
    _, out = export(tmp_path, [db], questions)

    ### Then
    payload = load(out)
    assert set(runs_by_id(payload)) == {"new-a"}
    excluded = {i for e in payload["manifest"]["exclusions"] for i in e["ids"]}
    assert {"old-a", "new-failed", "e-part"} <= excluded
    assert all(
        e["reason"] and e["count"] == len(e["ids"]) for e in payload["manifest"]["exclusions"]
    )


def test_given_two_databases_when_exported_then_union_is_used_and_both_are_listed(
    tmp_path: Path, questions: Path
) -> None:
    """
    Scenario: A volume-copied DB and the host DB combine.
    Slice: 56 (Part A)

    Given redis runs in one database file and mongodb runs in another,
    When both are passed with repeated --db,
    Then the export holds both stores and the manifest lists both files with their sha256.
    """
    ### Given
    host = make_db(tmp_path / "host.db", [ExperimentSpec("e-mongo", "mongodb", three_runs("m"))])
    volume = make_db(tmp_path / "volume.db", [ExperimentSpec("e-redis", "redis", three_runs("r"))])

    ### When
    _, out = export(tmp_path, [host, volume], questions)

    ### Then
    payload = load(out)
    assert {r["store"] for r in payload["runs"]} == {"redis", "mongodb"}
    listed = payload["manifest"]["inputs"]["databases"]
    assert [d["path"] for d in listed] == [str(host), str(volume)]


def test_given_a_database_when_exported_then_it_is_left_untouched(
    tmp_path: Path, cross_store_db: Path, questions: Path
) -> None:
    """
    Scenario: The exporter only reads run state.
    Slice: 56 (Part A)

    Given a database file,
    When the exporter runs,
    Then the file bytes are unchanged and no -wal/-shm sidecar is left beside it.
    """
    ### Given
    before = hashlib.sha256(cross_store_db.read_bytes()).hexdigest()

    ### When
    export(tmp_path, [cross_store_db], questions)

    ### Then
    assert hashlib.sha256(cross_store_db.read_bytes()).hexdigest() == before
    assert sorted(p.name for p in tmp_path.glob("state.db*")) == ["state.db"]


def test_given_exporter_imported_when_modules_inspected_then_no_vector_store_code_loads() -> None:
    """
    Scenario: The exporter never touches a vector store.
    Slice: 56 (Part A)

    Given a fresh interpreter importing the exporter,
    When loaded modules are inspected,
    Then no vector-store adapter, retriever or store factory module is among them.
    """
    ### Given
    code = (
        "import sys;"
        "import scripts.demo.export_demo_results;"
        "bad=[m for m in sys.modules if m.startswith(("
        "'server.db.mongo','server.db.postgres','server.core.retrieval',"
        "'server.db.ports.store_factory','pymongo','psycopg','elasticsearch','redis'))];"
        "print(bad)"
    )

    ### When
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=_REPO, capture_output=True, text=True, check=True
    )

    ### Then
    assert result.stdout.strip().splitlines()[-1] == "[]"
