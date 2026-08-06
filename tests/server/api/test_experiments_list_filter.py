"""
Author: Mani Sarkar
Created: 2026-08-06
Scope: list_all_experiment_docs — internal experiment-type filtering

Verifies that internal bookkeeping records (tier1_sweep) are excluded from
the user-facing experiments list while normal experiments are preserved.
"""

from __future__ import annotations

from unittest.mock import patch

from server.api.experiments_shared import list_all_experiment_docs


class _FakeStorage:
    def __init__(self, docs: list[dict]):
        self._docs = docs

    def find_all_experiments(self) -> list[dict]:
        return self._docs


_NORMAL_EXP = {
    "experiment_id": "exp-001",
    "experiment_name": "rag-test",
    "status": "complete",
}

_TIER1_EXP = {
    "experiment_id": "sweep-001",
    "experiment_name": "sweep:machine learning",
    "experiment_type": "tier1_sweep",
    "status": "complete",
}


class TestListAllExperimentDocsFilter:
    """Scenario: GET /experiments must not expose internal tier1_sweep records."""

    def test_tier1_sweep_excluded_from_list(self):
        """
        Scenario: tier1_sweep experiment is hidden from user-facing list.
        Slice: 22 — SIE Scooter (tier1_sweep history must not pollute experiment list)

        ### Given
        The storage backend holds one normal experiment and one tier1_sweep record.
        ### When
        list_all_experiment_docs() is called.
        ### Then
        Only the normal experiment is returned; the tier1_sweep record is absent.
        """
        ### Given
        storage = _FakeStorage([_NORMAL_EXP, _TIER1_EXP])

        ### When
        with patch("server.api.experiments_shared.get_storage_backend", return_value=storage):
            result = list_all_experiment_docs()

        ### Then
        ids = [doc["experiment_id"] for doc in result]
        assert "exp-001" in ids
        assert "sweep-001" not in ids

    def test_normal_experiments_preserved(self):
        """
        Scenario: normal experiments are not affected by internal-type filtering.
        Slice: 22 — regression guard

        ### Given
        Storage holds two normal experiments (no experiment_type set).
        ### When
        list_all_experiment_docs() is called.
        ### Then
        Both experiments are returned unchanged.
        """
        ### Given
        exp_a = {"experiment_id": "exp-a", "status": "running"}
        exp_b = {"experiment_id": "exp-b", "status": "complete"}
        storage = _FakeStorage([exp_a, exp_b])

        ### When
        with patch("server.api.experiments_shared.get_storage_backend", return_value=storage):
            result = list_all_experiment_docs()

        ### Then
        assert len(result) == 2
        ids = {doc["experiment_id"] for doc in result}
        assert ids == {"exp-a", "exp-b"}

    def test_all_tier1_sweep_excluded_when_no_normal_experiments(self):
        """
        Scenario: empty list when only internal records exist.
        Slice: 22 — edge case

        ### Given
        Storage holds only tier1_sweep records.
        ### When
        list_all_experiment_docs() is called.
        ### Then
        An empty list is returned.
        """
        ### Given
        storage = _FakeStorage([_TIER1_EXP])

        ### When
        with patch("server.api.experiments_shared.get_storage_backend", return_value=storage):
            result = list_all_experiment_docs()

        ### Then
        assert result == []
