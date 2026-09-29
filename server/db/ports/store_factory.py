"""Backend factory — resolves the active StorageBackend and VectorStore from settings.

Usage:
    from server.db.ports.store_factory import get_storage_backend, get_retriever_backend
    storage = get_storage_backend()
    retriever = get_retriever_backend()
"""

from server.db.ports.registry import resolve_adapter
from server.db.ports.retriever_backend import RetrieverBackend
from server.db.ports.storage import StorageBackend
from server.db.ports.vector_store import VectorStore
from server.models.status import VectorStoreSnapshot
from server.settings import normalize_storage_backend, settings

# Adapter modules are imported inside the functions below, not at module scope.
# Importing both eagerly would load pymongo and psycopg on every server start,
# including for the backend that is switched off, and each adapter module opens
# its client/pool lazily off settings that tests patch after import. Keeping the
# import at call time is what makes one backend genuinely optional.


def get_storage_backend() -> StorageBackend:
    """Return the configured StorageBackend.

    Reads STORAGE_BACKEND from settings (default ``sqlite``).
    Raises ValueError for unknown backends or a missing connection URI.
    """
    settings.ensure_storage_ready()
    backend = normalize_storage_backend(settings.storage_backend)
    if backend == "mongodb":
        from server.db.mongo.mongo_store import get_mongo_storage

        return get_mongo_storage()
    if backend == "postgres":
        from server.db.postgres.postgres_store import get_postgres_storage

        return get_postgres_storage()
    if backend == "sqlite":
        from server.db.sqlite.sqlite_store import get_sqlite_storage

        return get_sqlite_storage()
    raise ValueError(
        f"Unknown storage backend {backend!r}. "
        "Set STORAGE_BACKEND to 'mongodb', 'postgres', or 'sqlite'."
    )


def get_vector_store() -> VectorStore:
    """Return the configured VectorStore.

    Reads VECTOR_STORE_BACKEND from settings (defaults to STORAGE_BACKEND).
    Resolves the registered composite adapter (``MongoVectorStore`` /
    ``PostgresVectorStore``) via ``server.db.ports.registry.resolve_adapter``,
    which lazily imports the adapter module — a backend that is switched off
    never pulls in its driver.
    """
    settings.ensure_storage_ready()
    backend = normalize_storage_backend(settings.vector_store_backend)
    adapter_class = resolve_adapter(backend)
    return adapter_class()  # type: ignore[no-any-return]


def get_retriever_backend() -> RetrieverBackend:
    """Return the configured RetrieverBackend.

    Delegates to ``get_vector_store().retriever()`` — same name and call
    signature as before this port split (existing ``@patch(...
    get_retriever_backend)`` call-site patches keep working unchanged).
    """
    return get_vector_store().retriever()


def build_vector_store_snapshot(index_names: list[str]) -> VectorStoreSnapshot:
    """Build an immutable snapshot of the active vector store's identity.

    Reads settings + backend-specific cluster metadata without any DB I/O.
    Called at experiment-creation time so the snapshot is captured once and
    stored on the experiment document (Slice 55, ADR-008).
    ``index_names`` comes from the preflight assessment — no new DB query.
    """
    from server.core.guards.local_runtime import local_runtime_fields
    from server.db.mongo.mongodb_uri import mongodb_storage_mode
    from server.db.postgres.postgres_uri import postgres_storage_mode

    vector_backend = normalize_storage_backend(
        settings.vector_store_backend or settings.storage_backend
    )

    if vector_backend == "mongodb":
        vector_mode = mongodb_storage_mode(settings.mongodb_uri or "")
    elif vector_backend == "postgres":
        vector_mode = postgres_storage_mode(settings.database_url or "")
    else:
        vector_mode = f"{vector_backend}-local"

    cluster_host: str | None = None
    collection_name: str | None = None
    if vector_backend == "mongodb":
        from server.db.mongo.mongo_stats import _mongodb_cluster_hint

        cluster_host = _mongodb_cluster_hint()
        collection_name = "chunks"
    elif vector_backend == "postgres":
        from server.db.postgres.postgres_stats import _cluster_host

        cluster_host = _cluster_host()
        collection_name = "chunks"

    runtime = local_runtime_fields(vector_backend, vector_mode)
    return VectorStoreSnapshot(
        provider=vector_backend,
        storage_mode=vector_mode,
        cluster_host=cluster_host,
        collection_name=collection_name,
        index_names=index_names,
        container=runtime.get("container"),
        image=runtime.get("image"),
    )
