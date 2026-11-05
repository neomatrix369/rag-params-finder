"""
Contract: the dashboard's db-stats TypeScript shapes declare the backend's payload keys.

Author: RAG Params Finder contributors
Created: 2026-11-05
Scope: Slice 67E - frontend/src/types/index.ts hand-mirrors the dicts built by
       server/db/ports/stats_common.py (assemble_experiment_db_stats, new_vector_db_group).
       Both key sets come from the real functions, so a rename on either side fails here.
"""

from __future__ import annotations

import re
from pathlib import Path

from server.db.ports import stats_common

TYPES = Path(__file__).resolve().parents[4] / "frontend/src/types/index.ts"
FIELD = re.compile(r"^  (\w+)(\??):", re.MULTILINE)


def _interface_fields(name: str) -> dict[str, bool]:
    """Field name -> is optional, for a top-level `export interface <name> { ... }`."""
    match = re.search(rf"export interface {name} \{{\n(.*?)\n\}}", TYPES.read_text(), re.DOTALL)
    assert match, f"interface {name} not found in types/index.ts"
    return {field: bool(optional) for field, optional in FIELD.findall(match.group(1))}


def _backend_experiment_stats() -> dict:
    return stats_common.assemble_experiment_db_stats(
        {"data_paths": []},
        database_provider="mongodb",
        collection_name="chunks",
        cluster_host=None,
        index_names=[],
        total_chunks=0,
        embedding_models=[],
        chunking_breakdown={},
        total_results=0,
        unique_queries=0,
        runs_with_data=0,
        run_breakdown=[],
        results_per_run=[3, 3],
    )


def _backend_group_totals() -> dict:
    stats = _backend_experiment_stats()
    return stats_common.new_vector_db_group("mongodb::chunks", stats)["totals"]


class TestResultsBreakdownTypesContractShould:
    def test_experiment_db_stats_declares_exactly_the_backend_keys(self) -> None:
        """
        Scenario: every per-experiment key the server emits is typed, and nothing else is.
        Slice: 67E - ExperimentDbStats mirror.
        """
        ### Given
        backend_keys = set(_backend_experiment_stats())

        ### When
        frontend_keys = set(_interface_fields("ExperimentDbStats"))

        ### Then
        assert frontend_keys == backend_keys, (
            f"only in TS: {sorted(frontend_keys - backend_keys)}; "
            f"only in backend: {sorted(backend_keys - frontend_keys)}"
        )

    def test_group_totals_declare_every_backend_totals_key(self) -> None:
        """
        Scenario: the grouped totals the server starts with are all typed (TS may add
        adapter-filled extras such as database_used_mb).
        Slice: 67E - VectorDbGroupTotals mirror.
        """
        ### Given
        backend_keys = set(_backend_group_totals())

        ### When
        frontend_keys = set(_interface_fields("VectorDbGroupTotals"))

        ### Then
        assert backend_keys <= frontend_keys, f"untyped: {sorted(backend_keys - frontend_keys)}"

    def test_golden_fields_are_optional_in_the_frontend(self) -> None:
        """
        Scenario: old payloads and Redis/ES omit the golden facts, so TS must mark them optional.
        Slice: 67E - hide, do not invent.
        """
        ### Given
        experiment = _interface_fields("ExperimentDbStats")
        totals = _interface_fields("VectorDbGroupTotals")
        new_experiment_keys = {
            "result_runs",
            "golden_queries",
            "golden_queries_source",
            "partial_runs",
        }
        new_totals_keys = {"total_result_runs", "golden_queries_min", "golden_queries_max"}

        ### When
        backend_new = new_experiment_keys & set(_backend_experiment_stats())
        backend_new_totals = new_totals_keys & set(_backend_group_totals())

        ### Then
        assert backend_new == new_experiment_keys, "backend renamed a 67E per-experiment field"
        assert backend_new_totals == new_totals_keys, "backend renamed a 67E group-totals field"
        assert all(experiment[key] for key in new_experiment_keys)
        assert all(totals[key] for key in new_totals_keys)
