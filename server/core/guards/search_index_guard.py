"""Search-index preflight guard — Atlas (Mongo) and Postgres catalog paths.

Mongo: load Atlas cluster state, ensure indexes, validate requirements.
Postgres: introspect ``pg_extension`` / ``pg_indexes`` for schema.sql objects
(no Atlas Admin API, no quota negotiation).
"""

from __future__ import annotations

from server.core.guards.search_index_plan import (
    POSTGRES_VECTOR_EXTENSION,
    SearchIndexAssessment,
    SearchIndexMismatchError,
    SearchIndexSnapshot,
    assess_search_index_readiness,
    format_mismatch_message,
    format_postgres_mismatch_message,
    preflight_not_applicable,
    required_postgres_catalog_indexes,
    required_search_indexes,
    validate_vector_index_feasibility,
)
from server.db.atlas import CHUNKS_COLLECTION, get_database
from server.db.indexes import (
    M0_SEARCH_INDEX_LIMIT,
    SearchIndexInfo,
    ensure_required_search_indexes,
    list_cluster_search_indexes,
    prune_unknown_search_indexes,
    reconcile_chunks_search_indexes,
)
from server.db.postgres import fetch_all, fetch_one
from server.models.config import ExperimentConfig
from server.settings import normalize_storage_backend, settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

_READY_STATUSES = frozenset({"READY", True})
_CHUNKS_TABLE = "chunks"


def collect_search_index_snapshot(
    *,
    cluster_limit: int = M0_SEARCH_INDEX_LIMIT,
) -> SearchIndexSnapshot:
    """Build a snapshot of search-index readiness from the live Atlas cluster."""
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


def postgres_vector_extension_present() -> bool:
    """True when the ``vector`` extension is installed in the current database."""
    row = fetch_one(
        "SELECT 1 AS ok FROM pg_extension WHERE extname = %s",
        (POSTGRES_VECTOR_EXTENSION,),
    )
    return row is not None


def collect_postgres_index_snapshot(
    required: frozenset[str],
) -> SearchIndexSnapshot:
    """Build a snapshot of required HNSW/GIN indexes from ``pg_indexes``."""
    if not required:
        present: frozenset[str] = frozenset()
    else:
        rows = fetch_all(
            """
            SELECT indexname
              FROM pg_indexes
             WHERE schemaname = current_schema()
               AND tablename = %s
               AND indexname = ANY(%s)
            """,
            (_CHUNKS_TABLE, list(required)),
        )
        present = frozenset(str(row["indexname"]) for row in rows)

    return SearchIndexSnapshot(
        chunks_ready=present,
        chunks_building=frozenset(),
        cluster_total=len(present),
        cluster_limit=max(len(required), 1),
        unknown_count=0,
    )


def validate_postgres_experiment_indexes(
    config: ExperimentConfig,
) -> SearchIndexAssessment:
    """Verify schema.sql catalog objects or raise SearchIndexMismatchError."""
    required = required_postgres_catalog_indexes(config)
    extension_ok = postgres_vector_extension_present()
    snapshot = collect_postgres_index_snapshot(required)
    assessment = assess_search_index_readiness(required=required, snapshot=snapshot)

    if extension_ok and assessment.is_satisfied:
        return assessment

    message = format_postgres_mismatch_message(
        extension_present=extension_ok,
        assessment=assessment,
    )
    logger.error("postgres index preflight failed — %s", message)
    raise SearchIndexMismatchError(message)


def validate_experiment_search_indexes(
    config: ExperimentConfig,
    *,
    attempt_ensure: bool = True,
    cluster_limit: int = M0_SEARCH_INDEX_LIMIT,
) -> SearchIndexAssessment:
    """Ensure required indexes exist or raise SearchIndexMismatchError.

    Mongo: Atlas ensure/reconcile path.
    Postgres: catalog introspection only (schema bootstrap remains the ensure path).
    """
    backend = normalize_storage_backend(settings.storage_backend)
    if backend == "postgres":
        logger.info("search index preflight — postgres catalog introspection")
        return validate_postgres_experiment_indexes(config)

    if backend != "mongodb":
        logger.info(
            "search index preflight skipped — unknown backend=%s",
            settings.storage_backend,
        )
        return preflight_not_applicable()

    required = required_search_indexes(config)

    feasibility_error = validate_vector_index_feasibility(required)
    if feasibility_error:
        raise SearchIndexMismatchError(feasibility_error)

    snapshot = collect_search_index_snapshot(cluster_limit=cluster_limit)
    assessment = assess_search_index_readiness(required=required, snapshot=snapshot)

    if assessment.is_satisfied:
        return assessment

    if not attempt_ensure:
        message = format_mismatch_message(assessment)
        raise SearchIndexMismatchError(message)

    dropped = reconcile_chunks_search_indexes(required)
    if dropped:
        logger.info("search index preflight — reconciled chunks indexes: %s", dropped)
        snapshot = collect_search_index_snapshot(cluster_limit=cluster_limit)
        assessment = assess_search_index_readiness(required=required, snapshot=snapshot)
        if assessment.is_satisfied:
            return assessment

    if assessment.missing and len(assessment.missing) > assessment.available_slots:
        unknown_dropped = prune_unknown_search_indexes()
        if unknown_dropped:
            logger.info("search index preflight — pruned unknown indexes: %s", unknown_dropped)
            snapshot = collect_search_index_snapshot(cluster_limit=cluster_limit)
            assessment = assess_search_index_readiness(required=required, snapshot=snapshot)

    can_create = assessment.missing and len(assessment.missing) <= assessment.available_slots
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
