"""Backend factory — resolves the active StorageBackend and RetrieverBackend from settings.

Usage:
    from server.db.store_factory import get_storage_backend, get_retriever_backend
    storage = get_storage_backend()
    retriever = get_retriever_backend()
"""

from server.db.retriever_backend import RetrieverBackend
from server.db.storage import StorageBackend
from server.settings import settings

# Adapter modules are imported inside the functions below, not at module scope.
# Importing both eagerly would load pymongo and psycopg on every server start,
# including for the backend that is switched off, and each adapter module opens
# its client/pool lazily off settings that tests patch after import. Keeping the
# import at call time is what makes one backend genuinely optional.


def get_storage_backend() -> StorageBackend:
    """Return the configured StorageBackend.

    Reads STORAGE_BACKEND from settings (default "mongo").
    Raises ValueError for unknown backends or a missing connection URI.
    """
    settings.ensure_storage_ready()
    backend = settings.storage_backend.lower()
    if backend == "mongo":
        from server.db.mongo_store import get_mongo_storage

        return get_mongo_storage()
    if backend == "postgres":
        from server.db.postgres_store import get_postgres_storage

        return get_postgres_storage()
    raise ValueError(
        f"Unknown storage backend {backend!r}. Set STORAGE_BACKEND to 'mongo' or 'postgres'."
    )


def get_retriever_backend() -> RetrieverBackend:
    """Return the configured RetrieverBackend.

    Reads STORAGE_BACKEND from settings (default "mongo").
    Postgres serves dense, sparse, and hybrid retrieval (Slice 35).
    """
    settings.ensure_storage_ready()
    backend = settings.storage_backend.lower()
    if backend == "mongo":
        from server.db.mongo_store import get_mongo_retriever

        return get_mongo_retriever()
    if backend == "postgres":
        from server.db.postgres_store import get_postgres_retriever

        return get_postgres_retriever()
    raise ValueError(
        f"Unknown storage backend {backend!r}. Set STORAGE_BACKEND to 'mongo' or 'postgres'."
    )
