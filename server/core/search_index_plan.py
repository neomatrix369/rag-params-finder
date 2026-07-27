"""Deprecated import path — use ``server.core.guards.search_index_plan``."""

from server.core.guards.search_index_plan import (
    POSTGRES_HNSW_384_INDEX,
    POSTGRES_HNSW_1024_INDEX,
    POSTGRES_REQUIRED_INDEXES,
    POSTGRES_TEXT_SEARCH_GIN_INDEX,
    POSTGRES_VECTOR_EXTENSION,
    SearchIndexAssessment,
    SearchIndexMismatchError,
    SearchIndexSnapshot,
    assess_search_index_readiness,
    default_cluster_limit,
    format_mismatch_message,
    format_postgres_mismatch_message,
    preflight_not_applicable,
    required_postgres_catalog_indexes,
    required_search_indexes,
    validate_vector_index_feasibility,
)

__all__ = [
    "POSTGRES_HNSW_1024_INDEX",
    "POSTGRES_HNSW_384_INDEX",
    "POSTGRES_REQUIRED_INDEXES",
    "POSTGRES_TEXT_SEARCH_GIN_INDEX",
    "POSTGRES_VECTOR_EXTENSION",
    "SearchIndexAssessment",
    "SearchIndexMismatchError",
    "SearchIndexSnapshot",
    "assess_search_index_readiness",
    "default_cluster_limit",
    "format_mismatch_message",
    "format_postgres_mismatch_message",
    "preflight_not_applicable",
    "required_postgres_catalog_indexes",
    "required_search_indexes",
    "validate_vector_index_feasibility",
]
