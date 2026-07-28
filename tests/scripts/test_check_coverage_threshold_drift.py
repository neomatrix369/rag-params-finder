"""Unit tests for FE↔pyproject coverage threshold drift guard (Slice 45 Could).

Author: Slice 45
Created: 2026-07-28
Scope: scripts/ci/check_coverage_threshold_drift.py pure helpers
"""

from __future__ import annotations

from scripts.check_coverage_threshold_drift import drift_failures


def test_given_aligned_floors_when_evaluate_then_no_failures() -> None:
    """
    Scenario: Matching pyproject and vite thresholds pass.
    Slice: 45 — FE↔pyproject drift guard
    """
    ### Given
    pyproject = {"statements": 95.0, "branches": 90.0, "lines": 95.0, "functions": 95.0}
    vite = {"statements": 95.0, "branches": 90.0, "lines": 95.0, "functions": 95.0}

    ### When
    failures = drift_failures(pyproject, vite)

    ### Then
    assert failures == []


def test_given_branch_mismatch_when_evaluate_then_failure_lists_branch() -> None:
    """
    Scenario: Shared metric drift is reported.
    Slice: 45 — FE↔pyproject drift guard
    """
    ### Given
    pyproject = {"statements": 95.0, "branches": 90.0, "lines": 95.0, "functions": 95.0}
    vite = {"statements": 95.0, "branches": 85.0, "lines": 95.0, "functions": 95.0}

    ### When
    failures = drift_failures(pyproject, vite)

    ### Then
    assert any(f.startswith("branches:") for f in failures)


def test_given_missing_functions_in_pyproject_when_evaluate_then_failure() -> None:
    """
    Scenario: FE functions floor must be declared in pyproject for drift lock.
    Slice: 45 — FE↔pyproject drift guard
    """
    ### Given
    pyproject = {"statements": 95.0, "branches": 90.0, "lines": 95.0}
    vite = {"statements": 95.0, "branches": 90.0, "lines": 95.0, "functions": 95.0}

    ### When
    failures = drift_failures(pyproject, vite)

    ### Then
    assert any("functions" in f for f in failures)
