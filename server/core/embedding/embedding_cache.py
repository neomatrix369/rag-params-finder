"""Thread-safe embedding vector cache with a swappable backend.

Default backend: SQLite WAL (``EMBEDDING_CACHE_BACKEND=sqlite``).
Optional backend: Redis with TTL-tagged keys (``EMBEDDING_CACHE_BACKEND=redis``;
  compatible with ``volatile-lru`` eviction when one Redis instance serves both
  vectors and the cache — DECISIONS #273 option a).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import struct
import threading
import warnings
from pathlib import Path
from typing import Protocol, runtime_checkable

from server.utils.logger import get_logger

logger = get_logger(__name__)

_GLOBAL_CACHE: CacheBackend | None = None
_CACHE_LOCK = threading.Lock()


@runtime_checkable
class CacheBackend(Protocol):
    """Structural protocol satisfied by any embedding-cache adapter."""

    def get_many(self, keys: list[str]) -> dict[str, list[float]]: ...

    def put_many(
        self,
        entries: dict[str, list[float]],
        *,
        prompt_tokens: dict[str, int] | None = None,
    ) -> None: ...

    def cached_keys(self, keys: list[str]) -> frozenset[str]: ...


def cache_key(
    text: str,
    *,
    provider: str,
    model: str,
    dim: int,
    instruction: str = "",
    role: str = "doc",
) -> str:
    """Deterministic cache key — SHA256 of JSON-serialized inputs."""
    payload = json.dumps([provider, model, dim, instruction, role, text], ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


class EmbeddingCache:
    """Shared SQLite cache for embedding vectors."""

    def __init__(self, path: str):
        self._path = path
        self._conn: sqlite3.Connection | None = None
        # Warn if under a temp dir — vectors would be lost on reboot
        if "/tmp/" in path or "/var/folders/" in path or "\\Temp\\" in path:  # nosec B108
            warnings.warn(
                f"embedding_cache_path {path!r} is under a temp directory; "
                "vectors will be lost on reboot",
                stacklevel=2,
            )

    def init_db(self) -> None:
        """Open connection and create table if needed."""
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS embedding_vectors (
                key TEXT PRIMARY KEY,
                dim INT NOT NULL,
                vec BLOB NOT NULL,
                prompt_tokens INT
            )
        """
        )
        self._conn.commit()

    def get_many(self, keys: list[str]) -> dict[str, list[float]]:
        """Return cached vectors for the given keys (missing keys absent from result)."""
        if not keys or self._conn is None:
            return {}
        # Use parameterized query (placeholders are hardcoded, only keys are parameterized)
        placeholders = ",".join("?" * len(keys))
        rows = self._conn.execute(
            f"SELECT key, dim, vec FROM embedding_vectors WHERE key IN ({placeholders})",  # nosec B608
            keys,
        ).fetchall()
        result = {}
        for key, dim, vec_blob in rows:
            floats = list(struct.unpack(f"{dim}f", vec_blob))
            result[key] = floats
        return result

    def put_many(
        self,
        entries: dict[str, list[float]],
        *,
        prompt_tokens: dict[str, int] | None = None,
    ) -> None:
        """Persist vectors. Thread-safe via Python sqlite3 serialization."""
        if not entries or self._conn is None:
            return
        rows = []
        for key, vec in entries.items():
            dim = len(vec)
            vec_blob = struct.pack(f"{dim}f", *vec)
            tokens = (prompt_tokens or {}).get(key)
            rows.append((key, dim, vec_blob, tokens))
        self._conn.executemany(
            "INSERT OR REPLACE INTO embedding_vectors "
            "(key, dim, vec, prompt_tokens) VALUES (?, ?, ?, ?)",
            rows,
        )
        self._conn.commit()

    def cached_keys(self, keys: list[str]) -> frozenset[str]:
        """Return the subset of keys that are already cached."""
        return frozenset(self.get_many(keys).keys())


def get_cache_backend() -> CacheBackend:
    """Singleton factory: dispatches to SQLite or Redis per settings."""
    global _GLOBAL_CACHE
    with _CACHE_LOCK:
        if _GLOBAL_CACHE is None:
            from server.settings import settings

            backend = settings.embedding_cache_backend.strip().lower()
            if backend == "redis":
                from server.core.embedding.embedding_cache_redis import RedisCacheBackend

                _GLOBAL_CACHE = RedisCacheBackend(
                    url=settings.redis_url,
                    ttl_s=settings.embedding_cache_redis_ttl_s,
                )
            else:
                path = settings.embedding_cache_path
                cache = EmbeddingCache(path)
                cache.init_db()
                _GLOBAL_CACHE = cache
        return _GLOBAL_CACHE


def get_embedding_cache() -> CacheBackend:
    """Compat alias for ``get_cache_backend()``."""
    return get_cache_backend()


def reset_cache_backend() -> None:
    """Reset the singleton — test helper only."""
    global _GLOBAL_CACHE
    with _CACHE_LOCK:
        _GLOBAL_CACHE = None


def reset_embedding_cache() -> None:
    """Compat alias for ``reset_cache_backend()``."""
    reset_cache_backend()
