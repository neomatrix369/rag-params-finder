"""Preflight guard: load cluster state, ensure indexes, validate experiment requirements."""

from __future__ import annotations

from server.core.search_index_plan import (
    SearchIndexAssessment,
    SearchIndexMismatchError,
    SearchIndexSnapshot,
    assess_search_index_readiness,
    format_mismatch_message,
    required_search_indexes,
)
from server.db.atlas import CHUNKS_COLLECTION, get_database
from server.db.indexes import (
    M0_SEARCH_INDEX_LIMIT,
    SearchIndexInfo,
    ensure_required_search_indexes,
    list_cluster_search_indexes,
)
from server.models.config import ExperimentConfig
from server.utils.logger import get_logger

logger = get_logger(__name__)

_READY_STATUSES = frozenset({"READY", True})


def collect_search_index_snapshot(
    *,
    cluster_limit: int = M0_SEARCH_INDEX_LIMIT,
) -> SearchIndexSnapshot:
    """Build a snapshot of search-index readiness from the live cluster."""
    db_name = get_database().name
    rows = list_cluster_search_indexes()

    chunks_ready: set[str] = set()
    chunks_building: set[str] = set()
    unknown_count = 0

    for row in rows:
        if not row["known"]:
            unknown_count += 1
        if row["database"] != db_name or row["collection"] != CHUNKS_COLLECTION:
            continue
        if _is_ready(row):
            chunks_ready.add(row["name"])
        else:
            chunks_building.add(row["name"])

    return SearchIndexSnapshot(
        chunks_ready=frozenset(chunks_ready),
        chunks_building=frozenset(chunks_building),
        cluster_total=len(rows),
        cluster_limit=cluster_limit,
        unknown_count=unknown_count,
    )


def validate_experiment_search_indexes(
    config: ExperimentConfig,
    *,
    attempt_ensure: bool = True,
    cluster_limit: int = M0_SEARCH_INDEX_LIMIT,
) -> SearchIndexAssessment:
    """Ensure required indexes exist or raise SearchIndexMismatchError."""
    required = required_search_indexes(config)
    snapshot = collect_search_index_snapshot(cluster_limit=cluster_limit)
    assessment = assess_search_index_readiness(required=required, snapshot=snapshot)

    if assessment.is_satisfied:
        return assessment

    can_create = (
        attempt_ensure
        and assessment.missing
        and len(assessment.missing) <= assessment.available_slots
    )
    if can_create:
        logger.info(
            "search index preflight — creating missing indexes on chunks: %s",
            sorted(assessment.missing),
        )
        ensure_required_search_indexes(required)
        snapshot = collect_search_index_snapshot(cluster_limit=cluster_limit)
        assessment = assess_search_index_readiness(required=required, snapshot=snapshot)

    if not assessment.is_satisfied:
        message = format_mismatch_message(assessment)
        logger.error("search index preflight failed — %s", message)
        raise SearchIndexMismatchError(message)

    return assessment


def _is_ready(row: SearchIndexInfo) -> bool:
    status = row["status"]
    if status in _READY_STATUSES:
        return True
    if isinstance(status, str) and status.upper() == "READY":
        return True
    return False
