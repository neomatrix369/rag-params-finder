"""GWT tests for sweep_plan, the single source of truth for sweep counts.

Author: Claude
Created: 2026-11-05
Scope: Slice 67B - sweep_plan(config) agrees with expand_sweep, Bayesian budget
       unchanged, read path computes sweep_plan for old stored experiments.
"""

from __future__ import annotations

import itertools
import json
import warnings
from unittest.mock import patch

import pytest

from server.api.experiments_lifecycle import attach_sweep_plan
from server.core.orchestrator import _resolve_bayesian_n_trials
from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
    RetrieverConfig,
    expand_sweep,
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


def _config(
    *,
    sizes: list[int],
    overlaps: list[int],
    paddings: list[int],
    retrievers: list[RetrieverConfig],
    strategy: str = "grid",
    n_trials: int | None = None,
) -> ExperimentConfig:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cfg = ExperimentConfig(
            experiment_name="plan",
            data_paths=["./input_data/pdfs/sample.pdf"],
            queries_file="./configs/questions.example.json",
            embedding=EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
            chunking=ChunkingConfig(
                methods=[ChunkingMethod.RECURSIVE],
                params=ChunkParams(chunk_sizes=sizes, overlaps=overlaps, paddings=paddings),
            ),
            retrieval=RetrievalConfig(retrievers=retrievers),
            execution=ExecutionConfig(),
        )
    cfg.execution.search_strategy = strategy  # type: ignore[assignment]
    cfg.execution.bayesian.n_trials = n_trials
    return cfg


_CASES = list(
    itertools.product(
        [[256], [128, 256, 512]],
        [[0], [25, 50]],
        [[0], [], [0, 10]],
        [[_DENSE], [_DENSE, _DENSE], [_DENSE, _CE], [_CE, _CE, _DENSE]],
    )
)


@pytest.mark.parametrize("sizes,overlaps,paddings,retrievers", _CASES)
def test_full_grid_count_equals_expand_sweep(sizes, overlaps, paddings, retrievers) -> None:
    """
    Scenario: sweep_plan total always matches the real sweep expansion.
    Slice: 67B

    Given grid configs with empty paddings, duplicate retrievers and rerankers
    When sweep_plan is computed
    Then full_grid_count equals len(expand_sweep(config)) and the dimension
    counts multiply to it.
    """
    ### Given
    cfg = _config(sizes=sizes, overlaps=overlaps, paddings=paddings, retrievers=retrievers)

    ### When
    plan = sweep_plan(cfg)

    ### Then
    assert plan["full_grid_count"] == len(expand_sweep(cfg))
    product = 1
    for count in plan["dimension_counts"].values():
        product *= count
    assert product == plan["full_grid_count"]
    assert plan["planned_runs"] == plan["full_grid_count"]
    assert plan["search_strategy"] == "grid"
    assert plan["searchable_space"] is None


def test_empty_paddings_count_as_one() -> None:
    """
    Scenario: empty paddings never zero the total.
    Slice: 67B

    Given paddings: []
    When sweep_plan is computed
    Then the padding factor is 1.
    """
    ### Given
    cfg = _config(sizes=[256], overlaps=[50], paddings=[], retrievers=[_DENSE])

    ### When
    plan = sweep_plan(cfg)

    ### Then
    assert plan["dimension_counts"]["paddings"] == 1
    assert plan["full_grid_count"] == 1


@pytest.mark.parametrize(
    "n_trials,expected",
    [(None, 6), (4, 4), (50, 6)],
)
def test_bayesian_plan_and_budget_unchanged(n_trials: int | None, expected: int) -> None:
    """
    Scenario: Bayesian planned runs follow today's trial budget rule.
    Slice: 67B

    Given a Bayesian config with 3 sizes x 2 overlaps and n_trials (maybe larger)
    When sweep_plan and the orchestrator's budget resolver run
    Then planned_runs equals the capped budget, searchable_space is sizes x
    overlaps, and the orchestrator re-export agrees.
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


def test_warnings_for_overlap_and_padding() -> None:
    """
    Scenario: sweep_plan flags suspicious parameter pairs.
    Slice: 67B

    Given overlap >= chunk size and padding > chunk size
    When sweep_plan is computed
    Then warnings mention both.
    """
    ### Given
    cfg = _config(sizes=[100], overlaps=[100], paddings=[500], retrievers=[_DENSE])

    ### When
    plan = sweep_plan(cfg)

    ### Then
    assert any("overlap" in w for w in plan["warnings"])
    assert any("padding" in w for w in plan["warnings"])


def test_sweep_plan_is_quiet_for_bayesian() -> None:
    """
    Scenario: reading a plan must not emit trial-budget log noise.
    Slice: 67B

    Given a Bayesian config whose n_trials exceeds the space
    When sweep_plan is computed
    Then the budget warning logger is not called.
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
    with patch("server.models.config.logger") as mock_logger:
        sweep_plan(cfg)

    ### Then
    mock_logger.warning.assert_not_called()


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


def test_unparseable_config_leaves_doc_untouched() -> None:
    """
    Scenario: experiments without a usable config do not break reads.
    Slice: 67B

    Given a doc with no usable config
    When the read path attaches the plan
    Then no sweep_plan key is added.
    """
    ### Given
    doc = {"experiment_id": "x", "config": {"nonsense": 1}}

    ### When
    attach_sweep_plan(doc)

    ### Then
    assert "sweep_plan" not in doc


def test_sweep_plan_is_deterministic() -> None:
    """
    Scenario: same config in, byte-identical plan out.
    Slice: 67B

    Given a config with bad overlap/padding and a shuffled-equivalent config
    (same values, different list order)
    When sweep_plan is called repeatedly and on both
    Then the serialized outputs are identical, including key and warning order.
    """
    ### Given
    base = _config(
        sizes=[100, 200], overlaps=[100, 50], paddings=[500, 0], retrievers=[_DENSE, _CE]
    )
    shuffled = _config(
        sizes=[200, 100], overlaps=[50, 100], paddings=[0, 500], retrievers=[_CE, _DENSE]
    )

    ### When
    first = json.dumps(sweep_plan(base))
    second = json.dumps(sweep_plan(base))
    from_shuffled = json.dumps(sweep_plan(shuffled))

    ### Then
    assert first == second == from_shuffled
    assert list(sweep_plan(base)["dimension_counts"]) == [
        "models",
        "chunking_methods",
        "chunk_sizes",
        "overlaps",
        "paddings",
        "retrievers",
    ]
