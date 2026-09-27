"""Vector-store registry — table-driven provider→adapter resolution.

Generalizes the lazy per-backend ``if/elif`` import pattern in
``store_factory.py`` (``get_storage_backend`` / ``get_retriever_backend``)
into data: adding a new vector store (e.g. Elasticsearch, Slice 50) means
adding one entry here, not a new branch. The registry only names the dotted
adapter path; importing it happens inside ``resolve_adapter`` so a backend
that is switched off never pulls in its driver (pymongo / psycopg / an
Elasticsearch client) at process start.
"""

from __future__ import annotations

import importlib

# provider -> "module.path:ClassName". Composite adapters (Stream 3) compose
# each store's existing chunk methods, its RetrieverBackend, index bootstrap,
# and the chunk half of its stats module — see SLICE-49-VECTOR-STORE-PORT-SPLIT-REGISTRY.md
# "Reuse ledger". The classes need not exist yet for the registry itself to be
# correct; `resolve_adapter` only imports the target at call time.
_VECTOR_STORE_REGISTRY: dict[str, str] = {
    "mongodb": "server.db.mongo.mongo_vector_store:MongoVectorStore",
    "postgres": "server.db.postgres.postgres_vector_store:PostgresVectorStore",
}


def known_vector_stores() -> frozenset[str]:
    """Return the set of registered vector-store provider keys."""
    return frozenset(_VECTOR_STORE_REGISTRY)


def resolve_adapter(provider: str) -> type:
    """Lazily import and return the adapter class registered for ``provider``.

    Raises ValueError naming the unknown provider and listing the known
    vector stores. A registry entry whose target module/class does not exist
    yet fails at import time with the same underlying ``ModuleNotFoundError``
    / ``AttributeError`` — the registry does not special-case that.
    """
    target = _VECTOR_STORE_REGISTRY.get(provider)
    if target is None:
        known = ", ".join(sorted(_VECTOR_STORE_REGISTRY)) or "<none>"
        raise ValueError(f"Unknown vector store {provider!r}. Known vector stores: {known}.")
    module_path, _, class_name = target.partition(":")
    module = importlib.import_module(module_path)
    adapter_class: type = getattr(module, class_name)
    return adapter_class


def is_same_adapter(provider: str, other: str) -> bool:
    """True when ``provider`` resolves to the same registered class as ``other``.

    Lets call sites ask "is the active backend the postgres/mongodb one?"
    by comparing resolved *classes* instead of a ``== "postgres"`` /
    ``== "mongodb"`` string literal (Slice 49A output contract — the guards
    already do this inline; this names the pattern as one reusable registry
    primitive rather than a third copy of it). An unrecognised ``provider``
    returns False rather than raising, matching the guards' existing
    try/except-ValueError fallback behaviour.
    """
    try:
        return resolve_adapter(provider) is resolve_adapter(other)
    except ValueError:
        return False
