"""GET /api/v1/compare — live cross-store compare (Slice 66).

Reads run state only (no vector store needed), so it works whichever store is active.
Called on demand by the dashboard's "Compare sweeps" button, never on page load.
"""

from __future__ import annotations

import asyncio
import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from server.api.experiments_shared import list_all_experiment_docs
from server.core.compare import ExperimentBundle, build_compare
from server.db.ports.store_factory import get_storage_backend

router = APIRouter()


def _questions_sha(path: str) -> str:
    """SHA-256 of the questions file; '' when it is a URL or not readable (still a stable key)."""
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return ""


def _load_bundles() -> list[ExperimentBundle]:
    storage = get_storage_backend()
    bundles: list[ExperimentBundle] = []
    for experiment in list_all_experiment_docs():
        if experiment.get("status") not in ("complete", "partial"):
            continue
        exp_id = str(experiment["experiment_id"])
        bundles.append(
            (
                experiment,
                storage.find_run_statuses(exp_id),
                storage.find_results_for_experiment(exp_id),
            )
        )
    return bundles


@router.get("/compare")
async def compare() -> dict[str, Any]:
    sha_of = lru_cache(maxsize=None)(_questions_sha)  # per request: files may change between calls
    return await asyncio.to_thread(lambda: build_compare(_load_bundles(), sha_of))
