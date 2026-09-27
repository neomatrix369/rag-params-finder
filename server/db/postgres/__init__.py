"""Postgres/pgvector adapters — Behavior | Feature (Slice 45).

Import from submodules (e.g. ``server.db.postgres.postgres_store``).
Temporary shims remain at ``server.db.postgres_*`` for one release.

The former flat module ``server.db.postgres`` is this package: pool helpers
are re-exported here so ``from server.db import postgres`` / ``postgres.close_pool()``
and ``patch("server.db.postgres.*")`` keep working. There is no ``server/db/postgres.py``
shim — it would collide with this package directory.

The re-export is lazy (``__getattr__``, PEP 562): importing *any* submodule of
this package (e.g. ``server.db.postgres.postgres_uri``, which the Mongo-only
health-check guard needs) first runs this ``__init__.py`` — Python always
imports a package before one of its submodules. An eager
``from server.db.postgres.postgres import ...`` here would therefore load
psycopg into a Mongo-only process just from importing a sibling submodule
(GWT-1). ``__getattr__`` defers that import until a name is actually
accessed off the package, e.g. ``postgres.close_pool()``.
"""

from typing import Any

__all__ = [
    "CHUNKS_TABLE",
    "EXPERIMENTS_TABLE",
    "RESULTS_TABLE",
    "RUN_STATUS_TABLE",
    "SCHEMA_PATH",
    "bootstrap_schema",
    "close_pool",
    "connection",
    "execute",
    "execute_many",
    "fetch_all",
    "fetch_one",
    "fetch_value",
    "get_pool",
    "postgres_connect_kwargs",
]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from server.db.postgres import postgres as _postgres_module

    return getattr(_postgres_module, name)
