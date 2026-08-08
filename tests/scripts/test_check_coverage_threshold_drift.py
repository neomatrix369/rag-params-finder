"""Verifies frontend and backend coverage threshold alignment validator.

Author: Slice 45
Created: 2026-07-28
Scope: scripts/ci/check_coverage_threshold_drift.py — threshold drift validators, unit
"""

from __future__ import annotations

from scripts.check_coverage_threshold_drift import drift_failures


def test_drift_validator_passes_when_thresholds_are_aligned() -> None:
    """Frontend and backend coverage thresholds match — no drift violations.

    Scenario: Drift validator reports no violations when frontend (vite) and backend
    (pyproject) thresholds are identical.
    Slice: 45 — Frontend↔Backend coverage threshold alignment

    Given frontend (vite) thresholds of statements=95%, branches=90%, lines=95%,
    functions=95% and matching backend (pyproject) thresholds
    When the drift validator evaluates both threshold sets
    Then no drift failures are reported
    """
    ### Given
    pyproject = {"statements": 95.0, "branches": 90.0, "lines": 95.0, "functions": 95.0}
    vite = {"statements": 95.0, "branches": 90.0, "lines": 95.0, "functions": 95.0}

    ### When
    failures = drift_failures(pyproject, vite)

    ### Then
    assert failures == []


def test_drift_validator_detects_threshold_mismatch_on_shared_metrics() -> None:
    """Threshold mismatches between frontend and backend are reported.

    Scenario: Drift validator identifies when a shared metric (branches) has
    different thresholds in frontend and backend.
    Slice: 45 — Frontend↔Backend coverage threshold alignment

    Given backend (pyproject) threshold of branches=90% and frontend (vite) threshold
    of branches=85%
    When the drift validator evaluates both threshold sets
    Then a drift failure is reported naming the branches metric
    """
    ### Given
    pyproject = {"statements": 95.0, "branches": 90.0, "lines": 95.0, "functions": 95.0}
    vite = {"statements": 95.0, "branches": 85.0, "lines": 95.0, "functions": 95.0}

    ### When
    failures = drift_failures(pyproject, vite)

    ### Then
    assert any(f.startswith("branches:") for f in failures)


def test_drift_validator_fails_when_backend_missing_metric_declared_in_frontend() -> None:
    """Backend must declare all metrics declared by frontend for full coverage lockdown.

    Scenario: Drift validator requires that backend (pyproject) declares all metrics
    present in frontend (vite) thresholds.
    Slice: 45 — Frontend↔Backend coverage threshold alignment

    Given frontend (vite) threshold includes functions=95% but backend (pyproject)
    does not declare functions
    When the drift validator evaluates both threshold sets
    Then a drift failure is reported naming the functions metric
    """
    ### Given
    pyproject = {"statements": 95.0, "branches": 90.0, "lines": 95.0}
    vite = {"statements": 95.0, "branches": 90.0, "lines": 95.0, "functions": 95.0}

    ### When
    failures = drift_failures(pyproject, vite)

    ### Then
    assert any("functions" in f for f in failures)
