"""
Author: rag-params-finder contributors
Created: 2026-07-23
Scope: Unit tests for cli/main.py _print_summary — Bayesian summary and trial log output.

Process note: tests written post-implementation (GREEN-first deviation from RED→GREEN).
Coverage is equivalent but the ATDD RED phase was skipped for this closure pass.
"""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from rich.console import Console


def _capture_print_summary(data: dict) -> str:
    """Run _print_summary and return the rendered text output.

    markup=False on the Console causes Rich markup tags to appear literally in
    the output (e.g. '[green]completed[/green]' not ANSI codes), enabling
    assertions on both text content and styling.  The patch() context manager
    restores cli.main.console on exit, so tests are serially isolated.
    """
    from cli.main import _print_summary

    buf = StringIO()
    with patch("cli.main.console", Console(file=buf, highlight=False, markup=False)):
        _print_summary(data)
    return buf.getvalue()


_BASE_DATA: dict = {
    "status": "complete",
    "experiment_name": "test-exp",
    "runs": [],
    "config": {"execution": {"search_strategy": "grid"}},
}

_BAYESIAN_DATA: dict = {
    "status": "complete",
    "experiment_name": "test-bayesian",
    "runs": [],
    "config": {"execution": {"search_strategy": "bayesian"}},
    "grid_equivalent_count": 6,
    "bayesian_summary": {
        "planned_trials": 4,
        "attempted_trials": 4,
        "discarded_trials": 2,
        "not_started": 0,
        "grid_equivalent_count": 6,
        "best_query_avg_score": 0.847,
        "best_chunk_size": 512,
        "best_overlap": 50,
        "trial_log": [
            {"chunk_size": 256, "overlap": 0, "state": "completed", "score": 0.72},
            {"chunk_size": 512, "overlap": 50, "state": "completed", "score": 0.847},
            {"chunk_size": 256, "overlap": 0, "state": "pruned", "score": None},
            {"chunk_size": 768, "overlap": 100, "state": "failed", "score": None},
        ],
    },
}


class TestPrintSummaryBayesianSection:
    """_print_summary renders Bayesian section only for bayesian strategy.

    Five tests cover five distinct rendered scenarios of the Bayesian output:
    (1) grid strategy — no Bayesian section at all,
    (2) Bayesian strategy+counts line,
    (3) best-config line with formatted score,
    (4) Trial History table with per-state Rich markup applied,
    (5) Trial History section absent when trial_log is missing.
    Each scenario has a different conditional branch in _print_summary.
    """

    def test_grid_experiment_has_no_bayesian_section(self) -> None:
        """
        Scenario: non-Bayesian experiment output contains no Bayesian header.

        Given a completed grid experiment
        When _print_summary is called
        Then the output does not mention "Bayesian Search" or "Trial History".
        """
        ### Given
        data = {**_BASE_DATA}

        ### When
        output = _capture_print_summary(data)

        ### Then
        assert "Bayesian Search" not in output
        assert "Trial History" not in output

    def test_bayesian_experiment_shows_strategy_and_counts(self) -> None:
        """
        Scenario: Bayesian experiment output shows strategy header with trial counts.

        Given a completed Bayesian experiment with bayesian_summary
        When _print_summary is called
        Then the output includes the Bayesian strategy section with trial and grid counts.
        """
        ### Given
        data = {**_BAYESIAN_DATA}

        ### When
        output = _capture_print_summary(data)

        ### Then
        assert "Bayesian Search" in output
        assert "4/4" in output  # attempted/planned
        assert "6" in output  # grid_equivalent_count

    def test_bayesian_experiment_shows_best_config(self) -> None:
        """
        Scenario: Bayesian summary includes best config and score.

        Given a completed Bayesian experiment with best_query_avg_score and best_chunk_size
        When _print_summary is called
        Then the output displays chunk_size, overlap, and score for the best trial.
        """
        ### Given
        data = {**_BAYESIAN_DATA}

        ### When
        output = _capture_print_summary(data)

        ### Then
        assert "chunk_size=512" in output
        assert "overlap=50" in output
        assert "0.8470" in output

    def test_bayesian_experiment_shows_trial_history(self) -> None:
        """
        Scenario: trial_log entries are rendered in Trial History table with state markup.

        Given a Bayesian experiment with a trial_log containing completed, pruned,
        and failed entries
        When _print_summary is called
        Then the output includes Trial History with all states wrapped in their
        expected Rich markup tags (markup=False console preserves tags literally).
        """
        ### Given
        data = {**_BAYESIAN_DATA}

        ### When
        output = _capture_print_summary(data)

        ### Then
        assert "Trial History" in output
        # Verify Rich markup is applied, not just that the state text is present.
        # markup=False console emits tags literally: removing the style mapping
        # in production code would drop the tag and fail these assertions.
        assert "[green]completed" in output
        assert "[dim]pruned" in output
        assert "[red]failed" in output

    def test_bayesian_experiment_no_trial_log_skips_history_section(self) -> None:
        """
        Scenario: missing trial_log omits Trial History section entirely.

        Given a Bayesian experiment whose bayesian_summary has no trial_log key
        When _print_summary is called
        Then the output includes the Bayesian section but not Trial History.
        """
        ### Given
        import copy

        data = copy.deepcopy(_BAYESIAN_DATA)
        del data["bayesian_summary"]["trial_log"]

        ### When
        output = _capture_print_summary(data)

        ### Then
        assert "Bayesian Search" in output
        assert "Trial History" not in output
