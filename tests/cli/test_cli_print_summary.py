"""Verifies CLI experiment summary output — Bayesian trial history, best config, styling.

Author: rag-params-finder contributors
Created: 2026-07-23
Scope: cli/display.py — _print_summary function, unit, mocked Rich console output
"""

from __future__ import annotations

import copy
from io import StringIO
from unittest.mock import patch

import pytest
from rich.console import Console


def _capture_print_summary(data: dict) -> str:
    """Run _print_summary and return the rendered text output.

    markup=False on the Console causes Rich markup tags to appear literally in
    the output (e.g. '[green]completed[/green]' not ANSI codes), enabling
    assertions on both text content and styling.  The patch() context manager
    restores cli.display.console on exit, so tests are serially isolated.
    """
    from cli.display import _print_summary

    buf = StringIO()
    with patch("cli.display.console", Console(file=buf, highlight=False, markup=False)):
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
    """Verifies conditional rendering of Bayesian trial-search summary metadata.

    Covers: strategy-conditional section (Bayesian vs grid), trial-count formatting,
    best-config line (parameters + score), trial-history table (including per-state styling),
    and graceful fallback when optional fields are missing or unknown values present.
    """

    def test_summary_output_omits_bayesian_section_for_grid_strategy(self) -> None:
        """Grid-strategy experiments do not render Bayesian summary or trial history.

        Scenario: CLI summary hides Bayesian section when grid search is used.
        Slice: 45 — CLI output formatting

        Given a completed grid-search experiment
        When the summary is rendered to the terminal
        Then the output contains no "Bayesian Search" header or "Trial History" table
        """
        ### Given
        data = {**_BASE_DATA}

        ### When
        output = _capture_print_summary(data)

        ### Then
        assert "Bayesian Search" not in output
        assert "Trial History" not in output

    def test_summary_output_renders_bayesian_experiment_with_trial_history(
        self,
    ) -> None:
        """Bayesian experiments show trial history, best config, formatted trial stats.

        Scenario: CLI summary displays full Bayesian sweep with state markup and config.
        Slice: 45 — CLI output formatting

        Given a completed Bayesian-search experiment with trial log and best-config
        When the summary is rendered to the terminal
        Then output includes strategy header, trial counts (attempted/planned),
        grid-equivalent count, best-config line with chunk_size/overlap, score formatted
        to 4 decimals, and Trial History table
        """
        ### Given
        data = {**_BAYESIAN_DATA}

        ### When
        output = _capture_print_summary(data)

        ### Then — Bayesian strategy header and trial counts
        assert "Bayesian Search" in output
        assert "4/4" in output  # attempted/planned
        assert "6" in output  # grid_equivalent_count (equivalent single-parameter sweep size)
        ### Then — best config line with parameters and score
        assert "chunk_size=512" in output
        assert "overlap=50" in output
        assert "0.8470" in output  # best_query_avg_score formatted to .4f
        ### Then — Trial History section present
        assert "Trial History" in output

    @pytest.mark.parametrize(
        "state,expected_tag",
        [
            ("completed", "[green]"),
            ("pruned", "[dim]"),
            ("failed", "[red]"),
            ("interrupted", "[yellow]"),
        ],
    )
    def test_summary_output_applies_state_specific_styling_to_trial_entries(
        self, state: str, expected_tag: str
    ) -> None:
        """Each trial log entry receives Rich markup styling for its termination state.

        Scenario: Trial history marks outcomes (completed, pruned, failed, interrupted)
        with distinct styling.
        Slice: 45 — CLI output formatting

        Given a Bayesian experiment with a single trial in <state>
        When the summary renders the trial log
        Then the trial state text is wrapped in the Rich markup tag (<expected_tag>)
        — completed=[green], pruned=[dim], failed=[red], interrupted=[yellow]
        """
        ### Given
        data = copy.deepcopy(_BAYESIAN_DATA)
        score = 0.72 if state == "completed" else None
        data["bayesian_summary"]["trial_log"] = [
            {"chunk_size": 256, "overlap": 0, "state": state, "score": score}
        ]

        ### When
        output = _capture_print_summary(data)

        ### Then
        assert f"{expected_tag}{state}" in output

    def test_summary_output_omits_trial_history_when_trial_log_missing(self) -> None:
        """Bayesian summary shown even when trial-by-trial history unavailable.

        Scenario: Trial History table is conditional on trial_log data.
        Slice: 45 — CLI output formatting

        Given a Bayesian experiment with bayesian_summary but no trial_log array
        When the summary is rendered
        Then output shows Bayesian section (header, counts, best config) but not the
        Trial History table
        """
        ### Given
        data = copy.deepcopy(_BAYESIAN_DATA)
        del data["bayesian_summary"]["trial_log"]

        ### When
        output = _capture_print_summary(data)

        ### Then
        assert "Bayesian Search" in output
        assert "Trial History" not in output

    def test_summary_output_omits_discarded_trials_count_when_zero(self) -> None:
        """Discarded-trials line shown only if count > 0.

        Scenario: Trial-discard metrics omitted when no trials were pruned.
        Slice: 45 — CLI output formatting

        Given a Bayesian experiment where discarded_trials is 0
        When the summary is rendered
        Then output includes Bayesian section header and counts but not a "Discarded"
        line
        """
        ### Given
        data = copy.deepcopy(_BAYESIAN_DATA)
        data["bayesian_summary"]["discarded_trials"] = 0

        ### When
        output = _capture_print_summary(data)

        ### Then
        assert "Bayesian Search" in output
        assert "Discarded" not in output

    def test_summary_output_omits_best_config_when_best_score_missing(self) -> None:
        """Best-config line in summary is omitted when best_query_avg_score is not available.

        Scenario: Best-performing configuration is only highlighted when trial scoring completed.
        Slice: 45 — CLI output formatting

        Given a Bayesian experiment where bayesian_summary lacks best_query_avg_score
        When the summary is rendered
        Then the output shows the Bayesian section but no "Best:" line
        """
        ### Given
        data = copy.deepcopy(_BAYESIAN_DATA)
        data["bayesian_summary"].pop("best_query_avg_score", None)

        ### When
        output = _capture_print_summary(data)

        ### Then
        assert "Bayesian Search" in output
        assert "Best:" not in output

    def test_summary_output_renders_unknown_trial_state_without_styling(self) -> None:
        """Unknown trial states rendered as plain text without Rich markup.

        Scenario: Unrecognized trial outcome state falls back to unstyled text
        (defensive against new states).
        Slice: 45 — CLI output formatting

        Given a Bayesian experiment with a trial in unrecognized state (e.g., "waiting")
        When the summary is rendered
        Then trial state text appears in output but not wrapped in Rich markup tag
        ([green], [red], [dim], [yellow])
        """
        ### Given
        data = copy.deepcopy(_BAYESIAN_DATA)
        data["bayesian_summary"]["trial_log"] = [
            {"chunk_size": 256, "overlap": 0, "state": "waiting", "score": None}
        ]

        ### When
        output = _capture_print_summary(data)

        ### Then
        assert "waiting" in output
        for tag in ("[green]", "[red]", "[dim]", "[yellow]"):
            assert f"{tag}waiting" not in output
