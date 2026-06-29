"""Pure logic for Atlas Search index requirements and capacity assessment."""

from __future__ import annotations

from dataclasses import dataclass

from server.core.model_registry import get_index_name
from server.db.indexes import (
    ATLAS_MAX_VECTOR_DIMENSIONS,
    M0_SEARCH_INDEX_LIMIT,
    TEXT_SEARCH_INDEX_NAME,
    vector_index_dimensions,
)
from server.models.config import ExperimentConfig


class SearchIndexMismatchError(Exception):
    """Raised when an experiment cannot run due to missing or unavailable search indexes."""


@dataclass(frozen=True)
class SearchIndexSnapshot:
    """Cluster search-index state used for preflight checks."""

    chunks_ready: frozenset[str]
    chunks_building: frozenset[str]
    cluster_total: int
    cluster_limit: int
    unknown_count: int


@dataclass(frozen=True)
class SearchIndexAssessment:
    """Outcome of comparing experiment requirements to cluster capacity."""

    required: frozenset[str]
    present_ready: frozenset[str]
    present_building: frozenset[str]
    missing: frozenset[str]
    cluster_total: int
    cluster_limit: int
    available_slots: int
    unknown_count: int
    is_satisfied: bool
    failure_reason: str | None


def validate_vector_index_feasibility(required: frozenset[str]) -> str | None:
    """Return an error message when required vector indexes exceed Atlas limits."""
    oversized: list[str] = []
    for name in sorted(required):
        if name == TEXT_SEARCH_INDEX_NAME:
            continue
        dims = vector_index_dimensions(name)
        if dims is not None and dims > ATLAS_MAX_VECTOR_DIMENSIONS:
            oversized.append(f"{name} ({dims}-dim)")
    if not oversized:
        return None
    joined = ", ".join(oversized)
    return (
        f"Atlas Vector Search cannot index {joined}; "
        f"maximum is {ATLAS_MAX_VECTOR_DIMENSIONS} dimensions. "
        "Remove unsupported embedding models from the config."
    )


def required_search_indexes(config: ExperimentConfig) -> frozenset[str]:
    """Return Atlas Search index names this experiment config needs on chunks."""
    names = {get_index_name(model) for model in config.embedding.models}
    # Check if any retriever needs text search (sparse or hybrid)
    needs_text = any(r.type in ("sparse", "hybrid") for r in config.retrieval.retrievers)
    if needs_text:
        names.add(TEXT_SEARCH_INDEX_NAME)
    return frozenset(names)


def assess_search_index_readiness(
    *,
    required: frozenset[str],
    snapshot: SearchIndexSnapshot,
) -> SearchIndexAssessment:
    """Compare required indexes to cluster state and decide if the experiment can run."""
    present_ready = required & snapshot.chunks_ready
    present_building = required & snapshot.chunks_building
    missing = required - snapshot.chunks_ready - snapshot.chunks_building
    available_slots = max(snapshot.cluster_limit - snapshot.cluster_total, 0)

    failure_reason = _failure_reason(
        required=required,
        missing=missing,
        present_building=present_building,
        available_slots=available_slots,
        snapshot=snapshot,
    )
    is_satisfied = failure_reason is None

    return SearchIndexAssessment(
        required=required,
        present_ready=present_ready,
        present_building=present_building,
        missing=missing,
        cluster_total=snapshot.cluster_total,
        cluster_limit=snapshot.cluster_limit,
        available_slots=available_slots,
        unknown_count=snapshot.unknown_count,
        is_satisfied=is_satisfied,
        failure_reason=failure_reason,
    )


def format_mismatch_message(assessment: SearchIndexAssessment) -> str:
    """Human-readable explanation for logs, API errors, and CLI output."""
    if assessment.is_satisfied:
        return "Search indexes satisfy experiment requirements."

    lines = [assessment.failure_reason or "Search index preflight failed."]
    lines.append(
        f"Required: {sorted(assessment.required)}; "
        f"ready on chunks: {sorted(assessment.present_ready)}; "
        f"missing: {sorted(assessment.missing)}."
    )
    lines.append(
        f"Cluster search indexes: {assessment.cluster_total}/{assessment.cluster_limit} "
        f"({assessment.available_slots} slot(s) available)."
    )
    if assessment.unknown_count:
        lines.append(
            f"{assessment.unknown_count} unknown index(es) consume quota — "
            "run `rag-params-finder indexes reset --unknown-only`."
        )
    return " ".join(lines)


def _failure_reason(
    *,
    required: frozenset[str],
    missing: frozenset[str],
    present_building: frozenset[str],
    available_slots: int,
    snapshot: SearchIndexSnapshot,
) -> str | None:
    if len(required) > snapshot.cluster_limit:
        return (
            f"Experiment requires {len(required)} search indexes "
            f"but this cluster tier allows {snapshot.cluster_limit}."
        )

    if present_building:
        building = ", ".join(sorted(present_building))
        return f"Required search indexes still building on chunks: {building}."

    if not missing:
        return None

    if len(missing) > available_slots:
        missing_list = ", ".join(sorted(missing))
        return (
            f"Cannot create required search index(es): {missing_list}. "
            f"Need {len(missing)} free slot(s) but only {available_slots} available "
            f"({snapshot.cluster_total}/{snapshot.cluster_limit} in use)."
        )

    missing_list = ", ".join(sorted(missing))
    return f"Required search index(es) missing on chunks: {missing_list}."


def default_cluster_limit() -> int:
    """Return the configured Atlas M0 search-index limit."""
    return M0_SEARCH_INDEX_LIMIT
