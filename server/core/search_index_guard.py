"""Deprecated import path — use ``server.core.guards.search_index_guard``."""

from server.core.guards.search_index_guard import (
    collect_postgres_index_snapshot,
    collect_search_index_snapshot,
    postgres_vector_extension_present,
    validate_experiment_search_indexes,
    validate_postgres_experiment_indexes,
)

__all__ = [
    "collect_postgres_index_snapshot",
    "collect_search_index_snapshot",
    "postgres_vector_extension_present",
    "validate_experiment_search_indexes",
    "validate_postgres_experiment_indexes",
]
