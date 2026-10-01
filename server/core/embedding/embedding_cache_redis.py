"""Redis embedding cache — CacheBackend adapter for EMBEDDING_CACHE_BACKEND=redis.

Keys use the prefix ``rpf:emb:`` and always carry a TTL so they are eligible
for eviction under ``volatile-lru`` when one Redis instance serves both the
vector store and the embedding cache (DECISIONS #273 option a).  Vector keys
written by the vector store have no TTL (TTL = -1), so they are never evicted
under that policy.
"""

from __future__ import annotations

import struct

from server.db.redis.client import build_client, raise_if_unreachable
from server.utils.logger import get_logger

logger = get_logger(__name__)

_CACHE_PREFIX = "rpf:emb:"
_DEFAULT_TTL_S = 604800  # 7 days


class RedisCacheBackend:
    """Redis-backed embedding cache.

    Vectors are stored as raw ``float32`` little-endian BLOBs, identical to
    the SQLite encoding, so the bytes can be read back without re-encoding.
    Every key carries a TTL (default 7 days) to satisfy the ``volatile-lru``
    eviction contract; a zero TTL means keys never expire (for testing).
    """

    def __init__(self, url: str, *, ttl_s: int = _DEFAULT_TTL_S) -> None:
        self._ttl_s = ttl_s
        try:
            self._client = build_client(url)
            self._client.ping()
        except Exception as exc:
            raise_if_unreachable(exc, url)
            raise  # non-connection errors (e.g. auth) propagate as-is

    def _full_key(self, key: str) -> str:
        return f"{_CACHE_PREFIX}{key}"

    def get_many(self, keys: list[str]) -> dict[str, list[float]]:
        """Return vectors for cached keys; missing keys are absent from result."""
        if not keys:
            return {}
        full_keys = [self._full_key(k) for k in keys]
        blobs: list[bytes | None] = self._client.mget(full_keys)
        result: dict[str, list[float]] = {}
        for key, blob in zip(keys, blobs):
            if blob is None:
                continue
            n = len(blob) // 4  # 4 bytes per float32
            result[key] = list(struct.unpack(f"{n}f", blob))
        return result

    def put_many(
        self,
        entries: dict[str, list[float]],
        *,
        prompt_tokens: dict[str, int] | None = None,
    ) -> None:
        """Persist vectors using a pipelined SET with TTL."""
        if not entries:
            return
        pipe = self._client.pipeline()
        for key, vec in entries.items():
            blob = struct.pack(f"{len(vec)}f", *vec)
            full_key = self._full_key(key)
            if self._ttl_s > 0:
                pipe.set(full_key, blob, ex=self._ttl_s)
            else:
                pipe.set(full_key, blob)
        pipe.execute()

    def cached_keys(self, keys: list[str]) -> frozenset[str]:
        """Return the subset of keys already in the cache."""
        return frozenset(self.get_many(keys).keys())
