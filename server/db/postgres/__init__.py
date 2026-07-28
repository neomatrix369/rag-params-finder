"""Postgres/pgvector adapters — Behavior | Feature (Slice 45).

Import from submodules (e.g. ``server.db.postgres.postgres_store``).
Temporary shims remain at ``server.db.postgres_*`` for one release.

The former flat module ``server.db.postgres`` is this package: pool helpers
are re-exported here so ``from server.db import postgres`` / ``postgres.close_pool()``
and ``patch("server.db.postgres.*")`` keep working. There is no ``server/db/postgres.py``
shim — it would collide with this package directory.
"""

from server.db.postgres.postgres import (
    CHUNKS_TABLE,
    EXPERIMENTS_TABLE,
    RESULTS_TABLE,
    RUN_STATUS_TABLE,
    SCHEMA_PATH,
    bootstrap_schema,
    close_pool,
    connection,
    execute,
    execute_many,
    fetch_all,
    fetch_one,
    fetch_value,
    get_pool,
    postgres_connect_kwargs,
)

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
