"""Unit tests for backend coverage floor checker (DECISIONS #142).

Author: Cursor agent
Created: 2026-07-27
Scope: scripts/check_backend_coverage_floors.py pure helpers
"""

from __future__ import annotations

from scripts.check_backend_coverage_floors import evaluate, metrics_from_totals


def test_given_totals_above_floors_when_evaluate_then_no_failures() -> None:
    """
    Scenario: Measured metrics at or above 95/90/95 pass.
    Slice: 44 — BE coverage floor parity
    """
    # -- Given --
    totals = {
        "num_statements": 100,
        "missing_lines": 4,
        "covered_lines": 96,
        "num_branches": 50,
        "covered_branches": 45,
    }

    # -- When --
    measured = metrics_from_totals(totals)
    failures = evaluate(totals)

    # -- Then --
    assert measured["statements"] == 96.0
    assert measured["branches"] == 90.0
    assert measured["lines"] == 96.0
    assert failures == []


def test_given_branch_below_floor_when_evaluate_then_failure_lists_branch() -> None:
    """
    Scenario: Branch shortfall is reported even when statements pass.
    Slice: 44 — BE coverage floor parity
    """
    # -- Given --
    totals = {
        "num_statements": 100,
        "missing_lines": 2,
        "covered_lines": 98,
        "num_branches": 100,
        "covered_branches": 89,
    }

    # -- When --
    failures = evaluate(totals)

    # -- Then --
    assert any(f.startswith("branches:") for f in failures)
    assert not any(f.startswith("statements:") for f in failures)
