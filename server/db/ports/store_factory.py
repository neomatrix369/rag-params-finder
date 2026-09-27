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
from server.settings import normalize_storage_backend, settings

# Adapter modules are imported inside the functions below, not at module scope.
# Importing both eagerly would load pymongo and psycopg on every server start,
# including for the backend that is switched off, and each adapter module opens
# its client/pool lazily off settings that tests patch after import. Keeping the
# import at call time is what makes one backend genuinely optional.


def get_storage_backend() -> StorageBackend:
    """Return the configured StorageBackend.

    Reads STORAGE_BACKEND from settings (default ``mongodb``).
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
    raise ValueError(
        f"Unknown storage backend {backend!r}. Set STORAGE_BACKEND to 'mongodb' or 'postgres'."
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
