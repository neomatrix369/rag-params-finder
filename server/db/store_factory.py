"""Backend factory — resolves the active StorageBackend and RetrieverBackend from settings.

Usage:
    from server.db.store_factory import get_storage_backend, get_retriever_backend
    storage = get_storage_backend()
    retriever = get_retriever_backend()
"""

from server.db.retriever_backend import RetrieverBackend
from server.db.storage import StorageBackend


def get_storage_backend() -> StorageBackend:
    """Return the configured StorageBackend.

    Reads STORAGE_BACKEND from settings (default "mongo").
    Raises ValueError for unknown backends.
    Postgres adapter raises NotImplementedError until Slice 33.
    """
    from server.settings import settings

    backend = settings.storage_backend.lower()
    if backend == "mongo":
        from server.db.mongo_store import get_mongo_storage

        return get_mongo_storage()
    if backend == "postgres":
        raise NotImplementedError(
            "Postgres StorageBackend is not yet implemented — available in Slice 33+"
        )
    raise ValueError(
        f"Unknown storage backend {backend!r}. Set STORAGE_BACKEND to 'mongo' or 'postgres'."
    )


def get_retriever_backend() -> RetrieverBackend:
    """Return the configured RetrieverBackend.

    Reads STORAGE_BACKEND from settings (default "mongo").
    """
    from server.settings import settings

    backend = settings.storage_backend.lower()
    if backend == "mongo":
        from server.db.mongo_store import get_mongo_retriever

        return get_mongo_retriever()
    if backend == "postgres":
        raise NotImplementedError(
            "Postgres RetrieverBackend is not yet implemented — available in Slice 34+"
        )
    raise ValueError(
        f"Unknown storage backend {backend!r}. Set STORAGE_BACKEND to 'mongo' or 'postgres'."
    )
