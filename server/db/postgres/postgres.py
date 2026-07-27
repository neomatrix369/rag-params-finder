"""Postgres/pgvector connection pool and schema bootstrap.

Counterpart to ``server.db.mongo.atlas`` for the Postgres backend. Owns the pool
singleton and the idempotent DDL apply; all query code lives in
``server.db.postgres.postgres_store``.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from server.db.postgres.postgres_uri import postgres_connect_kwargs, postgres_storage_mode

__all__ = [
    "CHUNKS_TABLE",
    "EXPERIMENTS_TABLE",
    "RESULTS_TABLE",
    "RUN_STATUS_TABLE",
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
from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

# Table names — mirrors the *_COLLECTION constants in server.db.mongo.atlas.
EXPERIMENTS_TABLE = "experiments"
RUN_STATUS_TABLE = "run_status"
CHUNKS_TABLE = "chunks"
RESULTS_TABLE = "results"

_pool: ConnectionPool | None = None

# Serializes schema DDL across processes that reopen the pool (tests call
# close_pool frequently). Without this, concurrent CREATE INDEX / ALTER TABLE
# on the same relation deadlocks under AccessExclusiveLock.
_SCHEMA_ADVISORY_LOCK_KEY = 0x524147_504F53  # "RAGPOS" in hex-ish


def _require_database_url() -> str:
    uri = settings.database_url.strip()
    if not uri:
        raise ValueError(
            "DATABASE_URL not set in .env or environment — required when STORAGE_BACKEND=postgres"
        )
    return uri


def bootstrap_schema(uri: str) -> None:
    """Apply ``schema.sql`` on a standalone connection.

    Runs before the pool opens so ``register_vector`` can resolve the ``vector``
    type OID — the extension must already exist on the first pooled connection.
    """
    ddl = SCHEMA_PATH.read_text(encoding="utf-8")
    with psycopg.connect(uri, autocommit=True, **postgres_connect_kwargs(uri)) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (_SCHEMA_ADVISORY_LOCK_KEY,))
        try:
            conn.execute(ddl)
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (_SCHEMA_ADVISORY_LOCK_KEY,))
    logger.info("postgres schema ready — mode=%s", postgres_storage_mode(uri))


# An HNSW index cannot filter inside itself, so `experiment_id`/`embedding_model`/
# `run_id` are applied *after* it returns its ef_search candidate set. When the
# planner picks that path, a filtered top-k query silently comes back short —
# measured on this schema: 3 rows for a LIMIT of 20, with 39 discarded by the
# filter. Truncated result sets would quietly change the scores this tool exists
# to compare, so recall is not negotiable here.
#
# strict_order (pgvector >= 0.8) keeps re-scanning until the limit is satisfied
# and yields exact distance order. Older servers lack the GUC; they still return
# exact results via the planner's non-index path, so a warning is enough.
_HNSW_ITERATIVE_SCAN = "SET hnsw.iterative_scan = strict_order"


def _configure_connection(conn: psycopg.Connection) -> None:
    register_vector(conn)
    try:
        conn.execute(_HNSW_ITERATIVE_SCAN)
        conn.commit()
    except psycopg.Error as exc:
        conn.rollback()
        logger.warning(
            "could not enable hnsw.iterative_scan (%s) — filtered vector search may "
            "return fewer than top_k rows if the planner chooses the HNSW index; "
            "upgrade pgvector to 0.8+",
            exc,
        )


def get_pool() -> ConnectionPool:
    """Return the process-wide connection pool, creating it on first use."""
    global _pool
    if _pool is None:
        uri = _require_database_url()
        bootstrap_schema(uri)
        pool = ConnectionPool(
            uri,
            kwargs=postgres_connect_kwargs(uri),
            configure=_configure_connection,
            min_size=1,
            max_size=settings.postgres_pool_max_size,
            timeout=settings.postgres_pool_timeout_s,
            open=False,
        )
        pool.open()
        _pool = pool
        logger.info(
            "postgres pool ready — max_size=%s mode=%s",
            settings.postgres_pool_max_size,
            postgres_storage_mode(uri),
        )
    return _pool


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    """Check out a pooled connection; commits on success, rolls back on error."""
    with get_pool().connection() as conn:
        yield conn


Query = str | psycopg.sql.Composed | psycopg.sql.SQL
# Positional (%s) or named (%(name)s) parameters — psycopg accepts either.
Params = Sequence[Any] | Mapping[str, Any]


def fetch_all(query: Query, params: Params = ()) -> list[dict]:
    """Run a query and return every row as a dict."""
    with connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return list(cur.fetchall())


def fetch_one(query: Query, params: Params = ()) -> dict | None:
    """Run a query and return the first row as a dict, or None."""
    with connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return cur.fetchone()


def fetch_value(query: Query, params: Params = (), default: Any = None) -> Any:
    """Run a query and return the first column of the first row."""
    with connection() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        return default if row is None else row[0]


def execute(query: Query, params: Params = ()) -> int:
    """Run a statement and return the number of affected rows."""
    with connection() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        return cur.rowcount


def execute_many(query: Query, params_seq: Sequence[Sequence[Any]]) -> None:
    """Run a statement once per parameter tuple."""
    if not params_seq:
        return
    with connection() as conn, conn.cursor() as cur:
        cur.executemany(query, params_seq)


def close_pool() -> None:
    """Close the pool — used by server shutdown and test teardown."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
        logger.info("postgres pool closed")
