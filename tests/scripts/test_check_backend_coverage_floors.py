"""Verifies backend test coverage floor validation for DECISIONS #142.

Author: Cursor agent
Created: 2026-07-27
Scope: scripts/ci/check_backend_coverage_floors.py — coverage validators, unit, pure functions

Coverage baseline for full backend (server/ + cli/) as of 2026-08-07:
statements=61%, branches=47%, lines=61%.
"""

from __future__ import annotations

from scripts.check_backend_coverage_floors import evaluate, metrics_from_totals


def test_coverage_floors_pass_when_all_metrics_at_or_above_baseline() -> None:
    """Backend coverage metrics pass when statements, branches, and lines meet floor thresholds.

    Scenario: Coverage validator reports no violations when measured metrics exceed or
    equal the 61/47/61 floor baseline.
    Slice: 44 — Backend coverage floor validation

    Given measured backend coverage totals with statements=96%, branches=90%, lines=96%
    (all above the 61/47/61 floor thresholds)
    When the coverage floor validator evaluates the metrics
    Then the evaluation produces zero failures
    """
    ### Given
    # statements=96%, branches=90%, lines=96% — all above 61/47/61 floors
    totals = {
        "num_statements": 100,
        "missing_lines": 4,
        "covered_lines": 96,
        "num_branches": 50,
        "covered_branches": 45,
    }

    ### When
    measured = metrics_from_totals(totals)
    failures = evaluate(totals)

    ### Then
    assert measured["statements"] == 96.0
    assert measured["branches"] == 90.0
    assert measured["lines"] == 96.0
    assert failures == []


def test_coverage_floors_fail_when_branch_coverage_below_threshold() -> None:
    """Branch coverage shortfall is reported independently.

    Scenario: Coverage validator reports branch violation even when statement and line
    coverage are above their floors.
    Slice: 44 — Backend coverage floor validation

    Given measured backend coverage with statements=98%, branches=40%, lines=98%
    (branches below the 47% floor, statements and lines above theirs)
    When the coverage floor validator evaluates the metrics
    Then the evaluation reports a failure for branches and no failure for statements
    """
    ### Given
    # statements=98% (above 61% floor), branches=40% (below 47% floor)
    totals = {
        "num_statements": 100,
        "missing_lines": 2,
        "covered_lines": 98,
        "num_branches": 100,
        "covered_branches": 40,
    }

    ### When
    failures = evaluate(totals)

    ### Then
    assert any(f.startswith("branches:") for f in failures)
    assert not any(f.startswith("statements:") for f in failures)
