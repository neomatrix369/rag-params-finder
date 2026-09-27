"""Search-index preflight guard — Atlas (Mongo) and Postgres catalog paths.

Mongo: load Atlas cluster state, ensure indexes, validate requirements.
Postgres: introspect ``pg_extension`` / ``pg_indexes`` for schema.sql objects
(no Atlas Admin API, no quota negotiation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from server.core.guards.search_index_plan import (
    POSTGRES_VECTOR_EXTENSION,
    SearchIndexAssessment,
    SearchIndexMismatchError,
    SearchIndexSnapshot,
    assess_search_index_readiness,
    format_mismatch_message,
    format_postgres_mismatch_message,
    required_postgres_catalog_indexes,
    required_search_indexes,
    validate_vector_index_feasibility,
)
from server.db.ports.registry import is_same_adapter, resolve_adapter
from server.models.config import ExperimentConfig
from server.models.enums import RetrieverType
from server.settings import normalize_storage_backend, settings
from server.utils.logger import get_logger

if TYPE_CHECKING:
    # Type-only — under `from __future__ import annotations` this never
    # forces a runtime import, so it does not reintroduce the pymongo leak
    # the lazy imports below exist to avoid.
    from server.db.mongo.indexes import SearchIndexInfo

logger = get_logger(__name__)

_READY_STATUSES = frozenset({"READY", True})
_CHUNKS_TABLE = "chunks"


def collect_search_index_snapshot(
    *,
    cluster_limit: int | None = None,
) -> SearchIndexSnapshot:
    """Build a snapshot of search-index readiness from the live Atlas cluster."""
    # Lazy import (same convention as postgres_vector_extension_present below,
    # and the reciprocal of the psycopg leak fix in this same file): this
    # module is shared by both backends' preflight paths — reached from the
    # Postgres path too (PostgresVectorStore -> validate_postgres_experiment_indexes),
    # so importing pymongo at module scope would leak the Mongo driver into a
    # Postgres-only process (GWT-1 reciprocal).
    from server.db.mongo.atlas import CHUNKS_COLLECTION, get_database
    from server.db.mongo.indexes import M0_SEARCH_INDEX_LIMIT, list_cluster_search_indexes

    if cluster_limit is None:
        cluster_limit = M0_SEARCH_INDEX_LIMIT

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
    # Lazy import (same convention as store_factory.py): this module is shared
    # by both backends' preflight paths, so importing psycopg at module scope
    # would leak the Postgres driver into a Mongo-only process (GWT-1).
    from server.db.postgres.postgres import fetch_one

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
        # Lazy import — see postgres_vector_extension_present() above.
        from server.db.postgres.postgres import fetch_all

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


def preflight_stores(config: ExperimentConfig) -> SearchIndexAssessment:
    """Dual-store preflight — one entry point (Slice 49B, DECISIONS #253).

    Step 1 (vector store): health -> plan/ensure indexes -> capabilities
    checks (retrieval methods). The first failure raises
    ``SearchIndexMismatchError`` (HTTP 422 at submit) and stops; run-state
    checks are not attempted. Step 2 (run-state store): health only, and
    only when the run-state store differs from the vector store — in
    single-store mode both steps would hit the same database, so skipping
    the redundant second probe there keeps single-store behaviour byte-
    identical (characterization).
    """
    assessment = validate_experiment_search_indexes(config)
    vector_backend = normalize_storage_backend(
        settings.vector_store_backend or settings.storage_backend
    )
    run_state_backend = normalize_storage_backend(settings.storage_backend)
    if not is_same_adapter(vector_backend, run_state_backend):
        _preflight_run_state_store(run_state_backend)
    return assessment


def _preflight_run_state_store(run_state_backend: str) -> None:
    """Step 2 — run-state store health only (no search-index concept there)."""
    # Lazy import — health_check.py is shared by both backends' probes and
    # this module is imported by the vector-store composites, so importing it
    # at module scope here would risk the same driver-leak class this file's
    # other lazy imports already guard against.
    from server.core.guards.health_check import mongodb_health_status, postgres_health_status

    if is_same_adapter(run_state_backend, "postgres"):
        status = postgres_health_status()
    elif is_same_adapter(run_state_backend, "mongodb"):
        status = mongodb_health_status()
    else:
        status = "error"

    if status == "error":
        raise SearchIndexMismatchError(
            f"Run-state store {run_state_backend!r} is unreachable. Check its "
            "connection settings and that the service is running."
        )


def _validate_vector_capabilities(
    config: ExperimentConfig,
    capabilities: object,
    backend: str,
) -> None:
    """Fail closed when the vector store does not declare a requested retrieval method."""
    requested = {
        r.type.value
        for r in config.retrieval.retrievers
        if r.type in (RetrieverType.DENSE, RetrieverType.SPARSE, RetrieverType.HYBRID)
    }
    supported = {m.value for m in capabilities.retrieval_methods}  # type: ignore[attr-defined]
    unsupported = requested - supported
    if unsupported:
        raise SearchIndexMismatchError(
            f"Vector store {backend!r} does not support retrieval method(s) "
            f"{sorted(unsupported)}. Supported: {sorted(supported)}."
        )


def _validate_generic_vector_store_indexes(
    config: ExperimentConfig, backend: str
) -> SearchIndexAssessment:
    """Preflight for a registered vector store outside the mongodb/postgres pair.

    No skip path (DECISIONS #253, walkthrough G3): dispatches only through
    the vector store's own port methods. An adapter that raises on
    ``plan_indexes`` (no index plan published) fails closed with the
    preflight error naming the store, rather than passing silently.
    """
    # Lazy import — avoids a hard dependency on store_factory at module
    # import time for callers that never reach this generic branch.
    from server.db.ports.store_factory import get_vector_store

    try:
        store = get_vector_store()
    except ValueError as exc:
        # Unregistered/misconfigured VECTOR_STORE_BACKEND — fails closed as
        # SearchIndexMismatchError (not a raw ValueError) so the orchestrator's
        # existing SearchIndexMismatchError catch still fails the experiment
        # cleanly instead of crashing the sweep thread.
        raise SearchIndexMismatchError(
            f"Vector store {backend!r} is not configured: {exc}"
        ) from exc
    if not store.health_check():
        raise SearchIndexMismatchError(
            f"Vector store {backend!r} is unreachable. Check its connection "
            "settings and that the service is running."
        )

    def _plan() -> SearchIndexAssessment:
        try:
            return store.plan_indexes(config)
        except (AttributeError, NotImplementedError) as exc:
            raise SearchIndexMismatchError(
                f"Vector store {backend!r} publishes no index plan for this "
                f"config — cannot verify readiness: {exc}"
            ) from exc

    assessment = _plan()
    if not assessment.is_satisfied:
        store.ensure_indexes()
        assessment = _plan()
        if not assessment.is_satisfied:
            message = format_mismatch_message(assessment)
            raise SearchIndexMismatchError(f"Vector store {backend!r}: {message}")

    _validate_vector_capabilities(config, store.capabilities(), backend)
    return assessment


def validate_experiment_search_indexes(
    config: ExperimentConfig,
    *,
    attempt_ensure: bool = True,
    cluster_limit: int | None = None,
) -> SearchIndexAssessment:
    """Ensure required indexes exist or raise SearchIndexMismatchError.

    Mongo: Atlas ensure/reconcile path.
    Postgres: catalog introspection only (schema bootstrap remains the ensure path).
    Any other registered vector store: generic plan/ensure + capabilities
    dispatch through the ``VectorStore`` port (Slice 49B) — fails closed
    rather than skipping (no ``preflight_not_applicable()`` fallback).

    Scoped by ``VECTOR_STORE_BACKEND`` (falling back to ``STORAGE_BACKEND``
    when unset) — identical to ``STORAGE_BACKEND`` in single-store mode, so
    this is a no-op change there (characterization).
    """
    backend = normalize_storage_backend(settings.vector_store_backend or settings.storage_backend)
    try:
        adapter_class: type | None = resolve_adapter(backend)
    except ValueError:
        adapter_class = None

    if adapter_class is resolve_adapter("postgres"):
        logger.info("search index preflight — postgres catalog introspection")
        return validate_postgres_experiment_indexes(config)

    if adapter_class is not resolve_adapter("mongodb"):
        logger.info(
            "search index preflight — generic vector-store dispatch, backend=%s",
            backend,
        )
        return _validate_generic_vector_store_indexes(config, backend)

    # Lazy import — see collect_search_index_snapshot() above. Only reached
    # once the backend is confirmed to be mongodb, so a Postgres-only process
    # never executes this line.
    from server.db.mongo.indexes import (
        ensure_required_search_indexes,
        prune_unknown_search_indexes,
        reconcile_chunks_search_indexes,
    )

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
