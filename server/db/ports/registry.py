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
    "elasticsearch": (
        "server.db.elasticsearch.elasticsearch_vector_store:ElasticsearchVectorStore"
    ),
}

# Declarative mirror of each adapter's ``VectorCapabilities.can_host_run_state``
# (DECISIONS #241 pairing rule (ii)). Kept alongside the dotted-path registry
# above rather than resolved by importing the adapter class: settings.py's
# pairing-rule validator runs during ``Settings()`` construction, and the
# adapter modules import ``server.core.guards.health_check`` which imports
# ``server.settings`` — importing an adapter mid-construction is a circular
# import. A provider absent here defaults to ``False`` (vector-only) — a new
# store must opt in to being trusted with run state, not the other way round.
_CAN_HOST_RUN_STATE: dict[str, bool] = {
    "mongodb": True,
    "postgres": True,
    "elasticsearch": False,
}

# Example sweep YAML for each provider. The 422 hint and the dashboard empty
# state both read this map, so a new store cannot update one surface and
# forget the other (Slice 51, DECISIONS #253).
_EXAMPLE_CONFIG: dict[str, str] = {
    "mongodb": "configs/mongodb/example-local.yaml",
    "postgres": "configs/supabase/example-local.yaml",
    "elasticsearch": "configs/elasticsearch/example-local.yaml",
}


def known_vector_stores() -> frozenset[str]:
    """Return the set of registered vector-store provider keys."""
    return frozenset(_VECTOR_STORE_REGISTRY)


def example_config_for(provider: str) -> str:
    """Return the example YAML path registered for ``provider``.

    Raises ValueError (same shape as ``resolve_adapter``) when ``provider``
    is not a registered vector store.
    """
    if provider not in _VECTOR_STORE_REGISTRY:
        known = ", ".join(sorted(_VECTOR_STORE_REGISTRY)) or "<none>"
        raise ValueError(f"Unknown vector store {provider!r}. Known vector stores: {known}.")
    return _EXAMPLE_CONFIG[provider]


# Catalog modules expose labels, capabilities, and index summaries without
# importing pymongo, psycopg, or the Elasticsearch client. GET /api/stores
# resolves these, not the full adapters.
_CATALOG_REGISTRY: dict[str, str] = {
    "mongodb": "server.db.mongo.mongo_catalog:MongoCatalog",
    "postgres": "server.db.postgres.postgres_catalog:PostgresCatalog",
    "elasticsearch": "server.db.elasticsearch.elasticsearch_catalog:ElasticsearchCatalog",
}


def resolve_catalog(provider: str) -> type:
    """Lazily import the driver-free catalog class for ``provider``.

    Same error shape as ``resolve_adapter``. The catalog class must stay
    free of store drivers so listing stores does not require every extra.
    """
    if provider not in _VECTOR_STORE_REGISTRY:
        known = ", ".join(sorted(_VECTOR_STORE_REGISTRY)) or "<none>"
        raise ValueError(f"Unknown vector store {provider!r}. Known vector stores: {known}.")
    target = _CATALOG_REGISTRY.get(provider)
    if target is None:
        known = ", ".join(sorted(_CATALOG_REGISTRY)) or "<none>"
        raise ValueError(f"Unknown vector store {provider!r}. Known vector stores: {known}.")
    return _load_registered_class(target)


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
    return _load_registered_class(target)


def _load_registered_class(target: str) -> type:
    module_path, _, class_name = target.partition(":")
    module = importlib.import_module(module_path)
    registered: type = getattr(module, class_name)
    return registered


def vector_store_can_host_run_state(provider: str) -> bool:
    """Return the registered vector store's declared ``can_host_run_state``.

    Pairing rule (ii) (DECISIONS #241) decides by capability, not a branch
    keyed on the provider string. Reads ``_CAN_HOST_RUN_STATE`` (declared
    alongside the adapter registry, not by importing/constructing the
    adapter — see that dict's docstring for why). Raises ``ValueError``
    (same as ``resolve_adapter``) when ``provider`` is not registered —
    callers decide the not-yet-registered fallback (e.g. Elasticsearch/Redis
    before their adapter lands).
    """
    if provider not in _VECTOR_STORE_REGISTRY:
        known = ", ".join(sorted(_VECTOR_STORE_REGISTRY)) or "<none>"
        raise ValueError(f"Unknown vector store {provider!r}. Known vector stores: {known}.")
    return _CAN_HOST_RUN_STATE.get(provider, False)


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
