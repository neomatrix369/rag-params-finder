"""GWT tests for sweep_plan, the single source of truth for sweep counts.

Author: Claude
Created: 2026-11-05
Scope: Slice 67B - sweep_plan(config) agrees with expand_sweep, Bayesian budget
       unchanged, deterministic output, read path (attach_sweep_plan and
       GET /experiments/{id}) decorates old stored experiments and never fails.
"""

from __future__ import annotations

import itertools
import json
import logging
import warnings
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import server.api.experiments_lifecycle as lifecycle
from server.api.experiments_lifecycle import attach_sweep_plan
from server.core.orchestrator import _resolve_bayesian_n_trials
from server.core.pipeline import orchestrator as orchestrator_impl
from server.models import config as config_module
from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
    RetrieverConfig,
    expand_sweep,
    grid_equivalent_count,
    resolve_bayesian_n_trials,
    sweep_plan,
)
from server.models.enums import ChunkingMethod, RetrieverType

_CE = RetrieverConfig(
    type=RetrieverType.CROSS_ENCODER,
    provider="local",
    model="cross-encoder/ms-marco-MiniLM-L-6-v2",
)
_DENSE = RetrieverConfig(type=RetrieverType.DENSE)
_ONE_MODEL = ["all-MiniLM-L6-v2"]
_TWO_MODELS = ["all-MiniLM-L6-v2", "voyage-4"]
_ONE_METHOD = [ChunkingMethod.RECURSIVE]
_TWO_METHODS = [ChunkingMethod.RECURSIVE, ChunkingMethod.FIXED]
_THREE_METHODS = [ChunkingMethod.RECURSIVE, ChunkingMethod.FIXED, ChunkingMethod.SENTENCE]


@pytest.fixture(autouse=True)
def _reset_plan_failure_log() -> None:
    """Each test starts with an empty once-per-experiment failure log."""
    lifecycle._plan_failures_logged.clear()


def _config(
    *,
    sizes: list[int],
    overlaps: list[int],
    paddings: list[int],
    retrievers: list[RetrieverConfig],
    models: list[str] | None = None,
    methods: list[ChunkingMethod] | None = None,
    strategy: str = "grid",
    n_trials: int | None = None,
) -> ExperimentConfig:
    execution = {"search_strategy": strategy, "bayesian": {"n_trials": n_trials}}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ExperimentConfig(
            experiment_name="plan",
            data_paths=["./input_data/pdfs/sample.pdf"],
            queries_file="./configs/questions.example.json",
            embedding=EmbeddingConfig(models=models or _ONE_MODEL),
            chunking=ChunkingConfig(
                methods=methods or _ONE_METHOD,
                params=ChunkParams(chunk_sizes=sizes, overlaps=overlaps, paddings=paddings),
            ),
            retrieval=RetrievalConfig(retrievers=retrievers),
            execution=ExecutionConfig.model_validate(execution),
        )


_CASES = list(
    itertools.product(
        [_ONE_MODEL, _TWO_MODELS],
        [_ONE_METHOD, _TWO_METHODS, _THREE_METHODS],
        [[256], [128, 256, 512]],
        [[0], [25, 50]],
        [[0], [], [0, 10]],
        [[_DENSE], [_DENSE, _DENSE], [_DENSE, _CE], [_CE, _CE, _DENSE]],
    )
)


@pytest.mark.parametrize("models,methods,sizes,overlaps,paddings,retrievers", _CASES)
def test_full_grid_count_equals_expand_sweep(
    models, methods, sizes, overlaps, paddings, retrievers
) -> None:
    """
    Scenario: sweep_plan total always matches the real sweep expansion.
    Slice: 67B

    Given grid configs crossing 1-2 models, 1-3 chunking methods, sizes, overlaps,
    empty paddings, duplicate retrievers and rerankers
    When sweep_plan is computed
    Then full_grid_count equals len(expand_sweep(config)) and planned_runs equals it.
    """
    ### Given
    cfg = _config(
        models=models,
        methods=methods,
        sizes=sizes,
        overlaps=overlaps,
        paddings=paddings,
        retrievers=retrievers,
    )

    ### When
    plan = sweep_plan(cfg)
    expected_runs = len(expand_sweep(cfg))

    ### Then
    assert plan["full_grid_count"] == expected_runs
    assert plan["planned_runs"] == expected_runs
    assert plan["search_strategy"] == "grid"
    assert plan["searchable_space"] is None


def test_dimension_counts_report_each_axis() -> None:
    """
    Scenario: each axis count is reported separately (not only the product).
    Slice: 67B

    Given 2 models, 3 methods, 3 sizes, 2 overlaps, no paddings, 2 retrievers
    When sweep_plan is computed
    Then every axis count is reported and empty paddings count as 1.
    """
    ### Given
    cfg = _config(
        models=_TWO_MODELS,
        methods=_THREE_METHODS,
        sizes=[128, 256, 512],
        overlaps=[25, 50],
        paddings=[],
        retrievers=[_DENSE, _CE],
    )

    ### When
    counts = sweep_plan(cfg)["dimension_counts"]

    ### Then
    assert counts == {
        "models": 2,
        "chunking_methods": 3,
        "chunk_sizes": 3,
        "overlaps": 2,
        "paddings": 1,
        "retrievers": 2,
    }


@pytest.mark.parametrize("n_trials,expected", [(None, 6), (4, 4), (50, 6)])
def test_bayesian_plan_and_budget_unchanged(n_trials: int | None, expected: int) -> None:
    """
    Scenario: Bayesian planned runs follow today's trial budget rule.
    Slice: 67B

    Given a Bayesian config with 3 sizes x 2 overlaps and n_trials (maybe larger)
    When sweep_plan and the budget resolvers run
    Then planned_runs equals the capped budget and searchable_space is sizes x overlaps.
    """
    ### Given
    cfg = _config(
        sizes=[128, 256, 512],
        overlaps=[0, 50],
        paddings=[0],
        retrievers=[_DENSE],
        strategy="bayesian",
        n_trials=n_trials,
    )

    ### When
    plan = sweep_plan(cfg)

    ### Then
    assert plan["searchable_space"] == 6
    assert plan["planned_runs"] == expected
    assert resolve_bayesian_n_trials(cfg) == expected
    assert _resolve_bayesian_n_trials(cfg) == expected
    assert plan["full_grid_count"] == len(expand_sweep(cfg))


def test_orchestrator_uses_the_config_owned_budget_and_search_space() -> None:
    """
    Scenario: the surface that drives the sweep loop uses the config-owned helpers.
    Slice: 67B

    Given the orchestrator module and the config module
    When the helpers the sweep loop calls are compared
    Then they are the same function objects (budget AT-12..14 live in test_bayesian_finalise).
    """
    ### Given / When / Then
    assert orchestrator_impl.resolve_bayesian_n_trials is resolve_bayesian_n_trials
    assert orchestrator_impl._resolve_bayesian_n_trials is resolve_bayesian_n_trials
    assert orchestrator_impl.grid_equivalent_count is grid_equivalent_count


@pytest.mark.parametrize("sizes,overlaps", [([128, 256, 512], [0, 50]), ([64], [0, 8, 16, 32])])
def test_grid_equivalent_count_is_sizes_times_overlaps(sizes, overlaps) -> None:
    """
    Scenario: the Bayesian control variable keeps its meaning after the move.
    Slice: 67B

    Given configs of different shapes (other axes widened to prove they are ignored)
    When grid_equivalent_count is computed
    Then it equals len(sizes) * len(overlaps).
    """
    ### Given
    cfg = _config(
        models=_TWO_MODELS,
        methods=_TWO_METHODS,
        sizes=sizes,
        overlaps=overlaps,
        paddings=[0, 10],
        retrievers=[_DENSE, _CE],
    )

    ### When
    value = grid_equivalent_count(cfg)

    ### Then
    assert value == len(sizes) * len(overlaps)


def test_warnings_use_fixed_templates_with_sorted_numbers() -> None:
    """
    Scenario: sweep_plan flags suspicious pairs with deterministic sentences.
    Slice: 67B

    Given overlaps and paddings listed in non-sorted order with values > 9
    When sweep_plan is computed
    Then warnings are the full fixed-template sentences with sorted numbers.
    """
    ### Given
    cfg = _config(
        sizes=[300, 100],
        overlaps=[400, 150, 50],
        paddings=[900, 0, 700],
        retrievers=[_DENSE],
    )

    ### When
    plan = sweep_plan(cfg)

    ### Then
    assert plan["warnings"] == [
        "overlap [150, 400] is >= a chunk size in [100, 300]",
        "padding [700, 900] is larger than the smallest chunk size 100",
    ]


def test_clean_config_has_no_warnings() -> None:
    """
    Scenario: a sane config produces no warnings.
    Slice: 67B

    Given overlap < size and padding <= size
    When sweep_plan is computed
    Then warnings is empty.
    """
    ### Given
    cfg = _config(sizes=[256], overlaps=[50], paddings=[0], retrievers=[_DENSE])

    ### When / Then
    assert sweep_plan(cfg)["warnings"] == []


def test_sweep_plan_is_quiet_for_bayesian(caplog: pytest.LogCaptureFixture) -> None:
    """
    Scenario: reading a plan must not emit trial-budget log noise.
    Slice: 67B

    Given a Bayesian config whose n_trials exceeds the space
    When sweep_plan is computed
    Then nothing is logged by the config module.
    """
    ### Given
    cfg = _config(
        sizes=[128],
        overlaps=[0],
        paddings=[0],
        retrievers=[_DENSE],
        strategy="bayesian",
        n_trials=9,
    )

    ### When
    with caplog.at_level(logging.DEBUG, logger=config_module.logger.name):
        sweep_plan(cfg)

    ### Then
    assert caplog.records == []
    # positive control: the logging resolver under the same caplog does emit a record
    with caplog.at_level(logging.DEBUG, logger=config_module.logger.name):
        resolve_bayesian_n_trials(cfg)
    assert caplog.records != []


def test_sweep_plan_is_deterministic() -> None:
    """
    Scenario: same config in, byte-identical plan out (grid and Bayesian).
    Slice: 67B

    Given a config with bad overlap/padding, a shuffled-equivalent config and a
    Bayesian config
    When sweep_plan is called repeatedly and on each
    Then the serialized outputs are identical, including key and warning order.
    """
    ### Given
    base = _config(
        sizes=[300, 100], overlaps=[400, 150, 50], paddings=[900, 0, 700], retrievers=[_DENSE, _CE]
    )
    shuffled = _config(
        sizes=[100, 300], overlaps=[50, 150, 400], paddings=[700, 900, 0], retrievers=[_CE, _DENSE]
    )
    bayes = _config(
        sizes=[512, 128],
        overlaps=[50, 0],
        paddings=[0],
        retrievers=[_DENSE],
        strategy="bayesian",
        n_trials=3,
    )

    ### When
    first = json.dumps(sweep_plan(base))
    second = json.dumps(sweep_plan(base))
    from_shuffled = json.dumps(sweep_plan(shuffled))

    ### Then
    assert first == second == from_shuffled
    assert json.dumps(sweep_plan(bayes)) == json.dumps(sweep_plan(bayes))
    assert list(sweep_plan(base)) == [
        "dimension_counts",
        "full_grid_count",
        "searchable_space",
        "planned_runs",
        "search_strategy",
        "warnings",
    ]
    assert list(sweep_plan(base)["dimension_counts"]) == [
        "models",
        "chunking_methods",
        "chunk_sizes",
        "overlaps",
        "paddings",
        "retrievers",
    ]


# ---------------------------------------------------------------------------
# Read path
# ---------------------------------------------------------------------------


def test_old_stored_experiment_gets_sweep_plan_on_read() -> None:
    """
    Scenario: an experiment stored before 67B still returns a sweep_plan.
    Slice: 67B

    Given a stored experiment doc with only config and no new fields
    When the read path attaches the plan
    Then sweep_plan is correct and sweep_summary gains retrievers labels.
    """
    ### Given
    cfg = _config(sizes=[256, 512], overlaps=[50], paddings=[], retrievers=[_DENSE, _CE])
    doc = {
        "experiment_id": "old",
        "config": cfg.model_dump(mode="json"),
        "sweep_summary": {"retrieval_methods": ["dense", "cross_encoder"]},
    }

    ### When
    attach_sweep_plan(doc)

    ### Then
    assert doc["sweep_plan"]["full_grid_count"] == 4
    assert doc["sweep_summary"]["retrievers"] == [
        "dense",
        "cross_encoder: cross-encoder/ms-marco-MiniLM-L-6-v2",
    ]


def test_legacy_shaped_stored_config_still_gets_a_plan() -> None:
    """
    Scenario: a config stored with the deprecated retrieval form and absent keys.
    Slice: 67B

    Given retrieval.methods (deprecated) and no paddings / retrievers keys
    When the read path attaches the plan
    Then the migrated retrievers are counted and labelled and padding defaults apply.
    """
    ### Given
    doc = {
        "experiment_id": "legacy",
        "config": {
            "experiment_name": "legacy",
            "data_paths": ["./input_data/pdfs/sample.pdf"],
            "queries_file": "./configs/questions.example.json",
            "embedding": {"provider": "local", "models": ["all-MiniLM-L6-v2"]},
            "chunking": {"methods": ["recursive"], "params": {"chunk_sizes": [256, 512]}},
            "retrieval": {"methods": ["dense", "sparse"]},
        },
        "sweep_summary": {},
    }

    ### When
    attach_sweep_plan(doc)

    ### Then
    assert doc["sweep_plan"]["full_grid_count"] == 2 * 1 * 1 * 2
    assert doc["sweep_summary"]["retrievers"] == ["dense", "sparse"]


def test_unparseable_config_leaves_doc_untouched_and_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Scenario: experiments without a usable config do not break reads, and say why.
    Slice: 67B

    Given a doc whose config fails validation
    When the read path attaches the plan twice
    Then no sweep_plan key is added and exactly one warning is logged.
    """
    ### Given
    doc = {"experiment_id": "bad-config", "config": {"nonsense": 1}}

    ### When
    with caplog.at_level(logging.WARNING, logger=lifecycle.logger.name):
        attach_sweep_plan(doc)
        attach_sweep_plan(doc)

    ### Then
    assert "sweep_plan" not in doc
    warnings_logged = [r for r in caplog.records if "bad-config" in r.getMessage()]
    assert len(warnings_logged) == 1


def test_unexpected_failure_never_escapes_and_leaves_doc_untouched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Scenario: the decoration is additive and must never fail the detail read.
    Slice: 67B

    Given sweep_plan raising a non-ValueError
    When the read path attaches the plan
    Then nothing escapes and the doc has neither sweep_plan nor new retrievers labels.
    """
    ### Given
    cfg = _config(sizes=[256], overlaps=[50], paddings=[0], retrievers=[_DENSE])

    def boom(_: ExperimentConfig) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(lifecycle, "sweep_plan", boom)
    doc = {"experiment_id": "boom", "config": cfg.model_dump(mode="json"), "sweep_summary": {}}

    ### When
    attach_sweep_plan(doc)

    ### Then
    assert "sweep_plan" not in doc
    assert doc["sweep_summary"] == {}


def _client() -> TestClient:
    from server.api.experiments import router

    app = FastAPI()
    app.include_router(router, prefix="/experiments")
    return TestClient(app)


def _stored_doc(summary: dict) -> dict:
    cfg = _config(sizes=[256, 512], overlaps=[50], paddings=[0], retrievers=[_DENSE, _CE])
    return {
        "experiment_id": "exp-1",
        "status": "complete",
        "runs": [],
        "config": cfg.model_dump(mode="json"),
        "sweep_summary": summary,
    }


def test_get_experiment_endpoint_decorates_stored_doc_lacking_new_fields() -> None:
    """
    Scenario: GET /experiments/{id} carries sweep_plan for an old stored experiment.
    Slice: 67B

    Given a stored doc without sweep_plan or sweep_summary.retrievers
    When the detail endpoint is called
    Then the payload carries sweep_plan and the retriever labels.
    """
    ### Given
    doc = _stored_doc({"retrieval_methods": ["dense", "cross_encoder"]})

    ### When
    with patch("server.api.experiments.find_experiment_with_runs", return_value=doc):
        response = _client().get("/experiments/exp-1")

    ### Then
    body = response.json()
    assert response.status_code == 200
    assert body["sweep_plan"]["full_grid_count"] == 4
    assert body["sweep_summary"]["retrievers"] == [
        "dense",
        "cross_encoder: cross-encoder/ms-marco-MiniLM-L-6-v2",
    ]


def test_get_experiment_endpoint_keeps_stored_retrievers() -> None:
    """
    Scenario: a stored retrievers list is not clobbered by the read path.
    Slice: 67B

    Given a stored sweep_summary.retrievers
    When the detail endpoint is called
    Then the stored list is returned unchanged.
    """
    ### Given
    doc = _stored_doc({"retrievers": ["stored-label"]})

    ### When
    with patch("server.api.experiments.find_experiment_with_runs", return_value=doc):
        body = _client().get("/experiments/exp-1").json()

    ### Then
    assert body["sweep_summary"]["retrievers"] == ["stored-label"]


def test_get_experiment_endpoint_survives_plan_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Scenario: a failing sweep_plan cannot break the polled detail endpoint.
    Slice: 67B

    Given sweep_plan raising RuntimeError
    When the detail endpoint is called
    Then it still returns 200 without sweep_plan.
    """
    ### Given

    def boom(_: ExperimentConfig) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(lifecycle, "sweep_plan", boom)
    doc = _stored_doc({})

    ### When
    with patch("server.api.experiments.find_experiment_with_runs", return_value=doc):
        response = _client().get("/experiments/exp-1")

    ### Then
    assert response.status_code == 200
    assert "sweep_plan" not in response.json()


def test_list_endpoint_does_not_attach_sweep_plan() -> None:
    """
    Scenario: sweep_plan is a detail-only decoration.
    Slice: 67B

    Given a stored doc with a parseable config
    When the list endpoint is called
    Then the listed experiment has no sweep_plan.
    """
    ### Given
    doc = _stored_doc({})

    ### When
    with patch("server.api.experiments.list_all_experiment_docs", return_value=[doc]):
        body = _client().get("/experiments").json()

    ### Then
    assert [e["experiment_id"] for e in body["experiments"]] == ["exp-1"]
    assert "sweep_plan" not in body["experiments"][0]
