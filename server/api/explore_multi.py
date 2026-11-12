"""GET /api/v1/explore/multi?ids=e1&ids=e2 — merged explore across selected experiments (Slice 66).

Loads each experiment's runs and results from run-state, validates that all share
the same dataset and question file, then passes the merged data to analyze_results
for a single global ranking. Returns the same shape as GET /experiments/{id}/explore.
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from server.api.experiments_shared import load_explore_source
from server.core.results_analyzer import analyze_results

router = APIRouter()


def _questions_sha(path: str) -> str:
    """SHA-256 of the questions file; '' when unreadable or a URL."""
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return ""


def _normalized_paths(config: dict[str, Any]) -> tuple[str, ...]:
    paths = config.get("data_paths") or []
    return tuple(sorted(str(p) for p in paths))


def _load_and_merge(ids: list[str]) -> dict[str, Any]:
    """Blocking: load, validate, merge, rank."""
    all_runs: list[dict[str, Any]] = []
    all_results: list[dict[str, Any]] = []
    experiment_ids: list[str] = []
    experiment_names: list[str] = []
    first_paths: tuple[str, ...] | None = None
    first_sha: str | None = None

    for exp_id in ids:
        exp_doc, query_results, run_statuses = load_explore_source(exp_id)
        if exp_doc is None:
            raise HTTPException(status_code=404, detail=f"Experiment not found: {exp_id}")

        config = exp_doc.get("config") or {}
        paths = _normalized_paths(config)
        qfile = str(config.get("queries_file") or "")
        sha = _questions_sha(qfile)

        if first_paths is None:
            first_paths = paths
            first_sha = sha
        elif paths != first_paths or sha != first_sha:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Selected experiments use different datasets or question files "
                    "and cannot be compared directly. "
                    "Select experiments that all use the same data_paths and queries_file."
                ),
            )

        experiment_ids.append(exp_id)
        experiment_names.append(str(exp_doc.get("experiment_name") or exp_id))
        all_runs.extend(run_statuses)
        all_results.extend(query_results)

    explored = analyze_results(all_results, all_runs)
    explored["experiment_id"] = ids[0]
    explored["experiment_name"] = " vs ".join(experiment_names)
    explored["experiment_ids"] = experiment_ids
    explored["experiment_names"] = experiment_names
    return explored


@router.get("/explore/multi")
async def explore_multi(ids: list[str] = Query(default=[])) -> dict[str, Any]:
    """Merge results from selected experiments into one ranked leaderboard.

    Returns the same shape as GET /experiments/{id}/explore, plus experiment_ids
    and experiment_names fields listing all selected experiments.
    HTTP 422 when fewer than 2 IDs are provided or when experiments use different
    datasets or question files.
    """
    if len(ids) < 2:
        raise HTTPException(status_code=422, detail="At least 2 experiment IDs are required.")
    return await asyncio.to_thread(_load_and_merge, ids)
