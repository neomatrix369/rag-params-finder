"""GWT tests for the embedding cache — protocol contract + per-backend units.

Author: Claude Haiku 4.5 (48A), Claude Sonnet 4.6 (54 — parametrize + Redis)
Created: 2026-09-30
Scope: embedding_cache.py (CacheBackend protocol, SQLite adapter, singleton
       lifecycle, temp-dir warning) and embedding_cache_redis.py (Redis adapter,
       TTL, connection failure, zero-TTL path).
"""

from __future__ import annotations

import os
import sqlite3
import struct
import tempfile
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from server.core.embedding.embedding_cache import (
    CacheBackend,
    EmbeddingCache,
    cache_key,
    get_cache_backend,
    get_embedding_cache,
    reset_cache_backend,
    reset_embedding_cache,
)

# ---------------------------------------------------------------------------
# Shared fixture: parametrised over both backends
# ---------------------------------------------------------------------------


def _sqlite_backend(tmp_path: Path) -> EmbeddingCache:
    cache = EmbeddingCache(str(tmp_path / "test_cache.db"))
    cache.init_db()
    return cache


def _redis_backend() -> object:
    """Return a RedisCacheBackend pointing at REDIS_URL, or skip."""
    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        pytest.skip("REDIS_URL not set — skipping Redis backend integration test")
    try:
        from server.core.embedding.embedding_cache_redis import RedisCacheBackend

        return RedisCacheBackend(url=redis_url, ttl_s=60)
    except Exception as exc:
        pytest.skip(f"Redis backend unavailable: {exc}")


@pytest.fixture(params=["sqlite", "redis"])
def cache_backend(request, tmp_path):
    """Parametrised fixture: yields a CacheBackend for each backend type."""
    if request.param == "sqlite":
        yield _sqlite_backend(tmp_path)
    else:
        yield _redis_backend()


# ---------------------------------------------------------------------------
# cache_key — pure function, no backend required
# ---------------------------------------------------------------------------


class TestCacheKeyDeterminism:
    """Scenario: cache_key produces deterministic, stable keys."""

    def test_cache_key_same_inputs_produce_same_key(self):
        """
        Scenario: cache key same inputs produce same key.
        Slice: 48A — pre_embed planning
        Given text="hello", provider="doubleword", model="qwen3-v9", dim=1024
        When cache_key() is called twice with identical inputs
        Then both calls return the same SHA256 string.
        """
        ### Given
        text = "hello world"
        provider = "doubleword"
        model = "qwen3-v9"
        dim = 1024

        ### When
        key1 = cache_key(text, provider=provider, model=model, dim=dim)
        key2 = cache_key(text, provider=provider, model=model, dim=dim)

        ### Then
        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex is 64 chars

    def test_cache_key_different_text_produces_different_key(self):
        """
        Scenario: cache key different text produces different key.
        Slice: 48A — pre_embed planning
        Given two different texts
        When cache_key() is called for each
        Then the keys are different.
        """
        ### Given
        text1 = "hello"
        text2 = "world"

        ### When
        key1 = cache_key(text1, provider="doubleword", model="qwen3-v9", dim=1024)
        key2 = cache_key(text2, provider="doubleword", model="qwen3-v9", dim=1024)

        ### Then
        assert key1 != key2

    def test_cache_key_instruction_changes_key(self):
        """
        Scenario: cache key instruction parameter changes key.
        Slice: 48A — pre_embed planning (query vs doc distinction)
        Given text="hello" with different instruction values
        When cache_key() is called with instruction="" vs instruction="Instruct: ..."
        Then the keys are different.
        """
        ### Given
        text = "hello"

        ### When
        key_no_instr = cache_key(
            text, provider="doubleword", model="qwen3-v9", dim=1024, instruction=""
        )
        key_with_instr = cache_key(
            text,
            provider="doubleword",
            model="qwen3-v9",
            dim=1024,
            instruction="Instruct: Retrieve",
        )

        ### Then
        assert key_no_instr != key_with_instr

    def test_cache_key_role_changes_key(self):
        """
        Scenario: cache key role parameter changes key.
        Slice: 48A — pre_embed planning
        Given same text with role="doc" vs role="query"
        When cache_key() is called for each
        Then the keys are different.
        """
        ### Given
        text = "hello"

        ### When
        key_doc = cache_key(text, provider="doubleword", model="qwen3-v9", dim=1024, role="doc")
        key_query = cache_key(text, provider="doubleword", model="qwen3-v9", dim=1024, role="query")

        ### Then
        assert key_doc != key_query


# ---------------------------------------------------------------------------
# Protocol contract tests — parametrised over SQLite and Redis
# ---------------------------------------------------------------------------


class TestCacheBackendContract:
    """Scenario: both backends honour the same CacheBackend contract."""

    def test_get_many_empty_cache_returns_empty_dict(self, cache_backend):
        """
        Scenario: get many empty cache returns empty dict.
        Slice: 54 — CacheBackend contract
        Given an empty cache
        When get_many(keys) is called
        Then an empty dict is returned.
        """
        ### Given / When
        result = cache_backend.get_many(["key1", "key2"])

        ### Then
        assert result == {}

    def test_get_many_empty_keys_list_returns_empty(self, cache_backend):
        """
        Scenario: get many with empty keys list returns empty dict.
        Slice: 54 — CacheBackend contract
        Given an empty keys list
        When get_many([]) is called
        Then {} is returned immediately.
        """
        ### Given / When / Then
        assert cache_backend.get_many([]) == {}

    def test_put_many_then_get_many_retrieves_vectors(self, cache_backend):
        """
        Scenario: put many then get many retrieves vectors byte-identical.
        Slice: 54 — CacheBackend contract
        Given vectors to store
        When put_many() stores them and get_many() retrieves them
        Then the retrieved vectors are byte-identical to what was stored.
        """
        ### Given
        vectors = {"key1": [0.1, 0.2, 0.3], "key2": [0.4, 0.5, 0.6]}

        ### When
        cache_backend.put_many(vectors)
        result = cache_backend.get_many(["key1", "key2"])

        ### Then
        assert len(result) == 2
        assert result["key1"] == pytest.approx([0.1, 0.2, 0.3], abs=1e-6)
        assert result["key2"] == pytest.approx([0.4, 0.5, 0.6], abs=1e-6)

    def test_get_many_missing_keys_absent_from_result(self, cache_backend):
        """
        Scenario: get many missing keys absent from result rather than raising.
        Slice: 54 — CacheBackend contract
        Given some keys in cache and some missing
        When get_many(all_keys) is called
        Then only cached keys appear in result.
        """
        ### Given
        cache_backend.put_many({"key1": [0.1, 0.2]})

        ### When
        result = cache_backend.get_many(["key1", "key_missing"])

        ### Then
        assert "key1" in result
        assert "key_missing" not in result

    def test_put_many_empty_dict_is_noop(self, cache_backend):
        """
        Scenario: put many with empty dict is a no-op.
        Slice: 54 — CacheBackend contract
        Given an empty entries dict
        When put_many({}) is called
        Then no error is raised.
        """
        ### Given / When / Then
        cache_backend.put_many({})  # must not raise

    def test_cached_keys_returns_frozenset_of_present_keys(self, cache_backend):
        """
        Scenario: cached keys returns frozenset of present keys.
        Slice: 54 — CacheBackend contract
        Given some keys cached, some missing
        When cached_keys(all_keys) is called
        Then a frozenset of present keys is returned.
        """
        ### Given
        cache_backend.put_many({"key1": [0.1], "key2": [0.2]})

        ### When
        result = cache_backend.cached_keys(["key1", "key2", "key3"])

        ### Then
        assert isinstance(result, frozenset)
        assert result == frozenset(["key1", "key2"])

    def test_cache_backend_satisfies_protocol(self, cache_backend):
        """
        Scenario: every adapter satisfies the CacheBackend structural protocol.
        Slice: 54 — CacheBackend contract
        Given a cache backend instance
        When isinstance(backend, CacheBackend) is checked
        Then it returns True (runtime_checkable Protocol).
        """
        ### Given / When / Then
        assert isinstance(cache_backend, CacheBackend)


# ---------------------------------------------------------------------------
# SQLite-specific tests (not in the shared fixture)
# ---------------------------------------------------------------------------


class TestEmbeddingCacheSQLiteSpecific:
    """Scenario: SQLite-specific behavior of EmbeddingCache."""

    @pytest.fixture
    def temp_cache_path(self) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            yield str(Path(tmpdir) / "test_cache.db")

    def test_put_many_with_prompt_tokens_stores_metadata(self, temp_cache_path):
        """
        Scenario: put many with prompt tokens stores metadata in SQLite.
        Slice: 48A — cache with token tracking
        Given vectors and prompt_tokens metadata
        When put_many(vectors, prompt_tokens=...) stores them
        Then the metadata persists in the database.
        """
        ### Given
        cache = EmbeddingCache(temp_cache_path)
        cache.init_db()
        vectors = {"key1": [0.1, 0.2]}
        prompt_tokens = {"key1": 42}

        ### When
        cache.put_many(vectors, prompt_tokens=prompt_tokens)

        ### Then
        conn = sqlite3.connect(temp_cache_path)
        row = conn.execute(
            "SELECT prompt_tokens FROM embedding_vectors WHERE key='key1'"
        ).fetchone()
        conn.close()
        assert row[0] == 42


# ---------------------------------------------------------------------------
# Singleton lifecycle
# ---------------------------------------------------------------------------


class TestCacheSingleton:
    """Scenario: get_cache_backend/get_embedding_cache return the same singleton."""

    def test_get_cache_backend_returns_singleton(self, monkeypatch):
        """
        Scenario: get cache backend returns singleton.
        Slice: 54 — singleton lifecycle
        Given get_cache_backend is called twice
        When both calls succeed
        Then they return the same object instance.
        """
        ### Given
        reset_cache_backend()
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "test.db")
            monkeypatch.setattr("server.settings.settings.embedding_cache_path", cache_path)
            monkeypatch.setattr("server.settings.settings.embedding_cache_backend", "sqlite")

            ### When
            c1 = get_cache_backend()
            c2 = get_cache_backend()

            ### Then
            assert c1 is c2

    def test_get_embedding_cache_is_alias_for_get_cache_backend(self, monkeypatch):
        """
        Scenario: get_embedding_cache is a compat alias for get_cache_backend.
        Slice: 54 — backward compat
        Given both functions are called after a reset
        When both return a backend
        Then they return the same singleton object.
        """
        ### Given
        reset_cache_backend()
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "test.db")
            monkeypatch.setattr("server.settings.settings.embedding_cache_path", cache_path)
            monkeypatch.setattr("server.settings.settings.embedding_cache_backend", "sqlite")

            ### When
            c1 = get_cache_backend()
            c2 = get_embedding_cache()

            ### Then
            assert c1 is c2

    def test_reset_cache_backend_clears_singleton(self, monkeypatch):
        """
        Scenario: reset clears the singleton so the next call returns a fresh one.
        Slice: 54 — singleton lifecycle
        Given a cached singleton
        When reset_cache_backend() is called
        Then get_cache_backend() returns a different object.
        """
        ### Given
        reset_cache_backend()
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "test.db")
            monkeypatch.setattr("server.settings.settings.embedding_cache_path", cache_path)
            monkeypatch.setattr("server.settings.settings.embedding_cache_backend", "sqlite")
            c1 = get_cache_backend()

            ### When
            reset_cache_backend()
            c2 = get_cache_backend()

            ### Then
            assert c1 is not c2

    def test_reset_embedding_cache_alias_clears_singleton(self, monkeypatch):
        """
        Scenario: reset_embedding_cache compat alias also clears the singleton.
        Slice: 54 — backward compat
        Given a cached singleton
        When reset_embedding_cache() (compat alias) is called
        Then get_cache_backend() returns a new object.
        """
        ### Given
        reset_cache_backend()
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "test.db")
            monkeypatch.setattr("server.settings.settings.embedding_cache_path", cache_path)
            monkeypatch.setattr("server.settings.settings.embedding_cache_backend", "sqlite")
            c1 = get_cache_backend()

            ### When
            reset_embedding_cache()
            c2 = get_cache_backend()

            ### Then
            assert c1 is not c2


# ---------------------------------------------------------------------------
# Temp-dir warning (SQLite-specific guard)
# ---------------------------------------------------------------------------


class TestEmbeddingCacheWarnings:
    """Scenario: EmbeddingCache warns when path is under a temp directory."""

    def test_temp_dir_path_triggers_warning(self):
        """
        Scenario: temp dir path triggers warning.
        Slice: 48A — cache durability safeguard
        Given path contains "/tmp/"
        When EmbeddingCache is instantiated
        Then a UserWarning is issued.
        """
        ### Given
        temp_path = "/tmp/test_cache.db"

        ### When / Then
        with pytest.warns(UserWarning, match="temp directory"):
            EmbeddingCache(temp_path)

    def test_var_folders_path_triggers_warning(self):
        """
        Scenario: var folders path triggers warning.
        Slice: 48A — cache durability safeguard
        Given path contains "/var/folders/"
        When EmbeddingCache is instantiated
        Then a UserWarning is issued.
        """
        ### Given
        temp_path = "/var/folders/test_cache.db"

        ### When / Then
        with pytest.warns(UserWarning, match="temp directory"):
            EmbeddingCache(temp_path)

    def test_normal_path_does_not_warn(self):
        """
        Scenario: normal path does not warn.
        Slice: 48A — cache durability safeguard
        Given path in a normal directory
        When EmbeddingCache is instantiated
        Then no warning is issued.
        """
        ### Given
        normal_path = "/home/user/.rpf_cache/embeddings.db"

        ### When
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            EmbeddingCache(normal_path)

        ### Then
        cache_warnings = [x for x in w if "temp directory" in str(x.message)]
        assert len(cache_warnings) == 0


# ---------------------------------------------------------------------------
# Redis adapter unit tests (mocked — no live Redis required)
# ---------------------------------------------------------------------------


class TestRedisCacheBackend:
    """Scenario: RedisCacheBackend stores and retrieves embedding vectors via Redis."""

    def _make_backend(self, ttl_s: int = 3600):
        """Return a RedisCacheBackend with a mocked Redis client."""
        from server.core.embedding.embedding_cache_redis import RedisCacheBackend

        with patch("server.core.embedding.embedding_cache_redis.build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_build.return_value = mock_client
            backend = RedisCacheBackend(url="redis://localhost:6379", ttl_s=ttl_s)
            backend._client = mock_client  # keep mock accessible
        return backend

    def test_get_many_empty_keys_returns_empty_dict(self):
        """
        Scenario: get_many with empty key list returns empty dict without calling Redis.
        Slice: 54 — Redis adapter
        Given an empty key list
        When get_many([]) is called
        Then {} is returned and MGET is not called.
        """
        ### Given
        backend = self._make_backend()

        ### When
        result = backend.get_many([])

        ### Then
        assert result == {}
        backend._client.mget.assert_not_called()

    def test_get_many_decodes_float32_blobs(self):
        """
        Scenario: get_many decodes float32 BLOB values from Redis MGET.
        Slice: 54 — Redis adapter
        Given keys in Redis with float32-encoded blobs
        When get_many(keys) is called
        Then the returned vectors are decoded correctly.
        """
        ### Given
        backend = self._make_backend()
        vec = [0.1, 0.2, 0.3]
        blob = struct.pack("3f", *vec)
        backend._client.mget.return_value = [blob, None]

        ### When
        result = backend.get_many(["key1", "key_missing"])

        ### Then
        assert "key_missing" not in result
        assert result["key1"] == pytest.approx(vec, abs=1e-6)

    def test_get_many_calls_mget_with_prefixed_keys(self):
        """
        Scenario: get_many prefixes all keys with rpf:emb: before calling MGET.
        Slice: 54 — key namespace isolation
        Given keys without the prefix
        When get_many(keys) is called
        Then MGET is called with rpf:emb:<key> for each.
        """
        ### Given
        backend = self._make_backend()
        backend._client.mget.return_value = [None, None]

        ### When
        backend.get_many(["abc", "def"])

        ### Then
        backend._client.mget.assert_called_once_with(["rpf:emb:abc", "rpf:emb:def"])

    def test_put_many_empty_entries_is_noop(self):
        """
        Scenario: put_many with empty entries is a no-op and does not call pipeline.
        Slice: 54 — Redis adapter
        Given an empty entries dict
        When put_many({}) is called
        Then no pipeline is started.
        """
        ### Given
        backend = self._make_backend()

        ### When
        backend.put_many({})

        ### Then
        backend._client.pipeline.assert_not_called()

    def test_put_many_uses_pipeline_with_ttl(self):
        """
        Scenario: put_many stores vectors via pipeline SET with TTL.
        Slice: 54 — volatile-lru option (a) — all cache keys carry a TTL
        Given entries to store and ttl_s=3600
        When put_many(entries) is called
        Then each key is set via pipeline.set with ex=3600.
        """
        ### Given
        backend = self._make_backend(ttl_s=3600)
        mock_pipe = MagicMock()
        backend._client.pipeline.return_value = mock_pipe
        vec = [0.5, 0.6]
        blob = struct.pack("2f", *vec)

        ### When
        backend.put_many({"mykey": vec})

        ### Then
        mock_pipe.set.assert_called_once_with("rpf:emb:mykey", blob, ex=3600)
        mock_pipe.execute.assert_called_once()

    def test_put_many_zero_ttl_stores_without_expiry(self):
        """
        Scenario: put_many with ttl_s=0 stores keys without a TTL.
        Slice: 54 — test helper / manual override
        Given ttl_s=0
        When put_many(entries) is called
        Then SET is called without the ex parameter.
        """
        ### Given
        backend = self._make_backend(ttl_s=0)
        mock_pipe = MagicMock()
        backend._client.pipeline.return_value = mock_pipe

        ### When
        backend.put_many({"k": [1.0]})

        ### Then
        mock_pipe.set.assert_called_once_with("rpf:emb:k", struct.pack("1f", 1.0))
        # Confirm ex was NOT passed
        args, kwargs = mock_pipe.set.call_args
        assert "ex" not in kwargs

    def test_cached_keys_delegates_to_get_many(self):
        """
        Scenario: cached_keys returns frozenset of keys present in Redis.
        Slice: 54 — Redis adapter
        Given some keys in Redis and some missing
        When cached_keys(all_keys) is called
        Then a frozenset of only the present keys is returned.
        """
        ### Given
        backend = self._make_backend()
        vec = [0.1]
        blob = struct.pack("1f", *vec)
        backend._client.mget.return_value = [blob, None]

        ### When
        result = backend.cached_keys(["present", "absent"])

        ### Then
        assert result == frozenset(["present"])

    def test_constructor_pings_redis(self):
        """
        Scenario: constructor calls ping to verify connectivity.
        Slice: 54 — fail-closed startup
        Given a reachable Redis
        When RedisCacheBackend is instantiated
        Then ping() is called once.
        """
        ### Given / When
        backend = self._make_backend()

        ### Then
        backend._client.ping.assert_called()

    def test_constructor_raises_on_unreachable_redis(self):
        """
        Scenario: unreachable Redis raises RedisUnreachableError on construction.
        Slice: 54 — fail-closed startup
        Given REDIS_URL points to an unreachable host
        When RedisCacheBackend is instantiated
        Then RedisUnreachableError is raised.
        """
        ### Given
        from server.core.embedding.embedding_cache_redis import RedisCacheBackend
        from server.db.redis.client import RedisUnreachableError

        ### When / Then
        with patch("server.core.embedding.embedding_cache_redis.build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.ping.side_effect = OSError("Connection refused")
            mock_build.return_value = mock_client
            with pytest.raises(RedisUnreachableError):
                RedisCacheBackend(url="redis://localhost:9999")

    def test_cache_keys_use_rpf_emb_prefix(self):
        """
        Scenario: cache keys cannot collide with vector-store keys.
        Slice: 54 — key namespace isolation (GWT spec)
        Given any content key
        When the full Redis key is computed
        Then it starts with rpf:emb: and never matches a vector key (rpf:chunks:*).
        """
        ### Given
        backend = self._make_backend()

        ### When
        full_key = backend._full_key("abc123")

        ### Then
        assert full_key.startswith("rpf:emb:")
        assert not full_key.startswith("rpf:chunks:")


# ---------------------------------------------------------------------------
# Settings: ensure_cache_backend_ready validation
# ---------------------------------------------------------------------------


class TestEnsureCacheBackendReady:
    """Scenario: ensure_cache_backend_ready raises when redis backend has no URL."""

    def test_sqlite_backend_always_ready(self, monkeypatch):
        """
        Scenario: sqlite backend requires no REDIS_URL.
        Slice: 54 — settings validation
        Given EMBEDDING_CACHE_BACKEND=sqlite
        When ensure_cache_backend_ready() is called
        Then no error is raised.
        """
        ### Given
        from server.settings import Settings

        s = Settings(
            embedding_cache_backend="sqlite",
            storage_backend="sqlite",
            vector_store_backend="mongodb",
        )

        ### When / Then
        s.ensure_cache_backend_ready()  # must not raise

    def test_redis_backend_without_redis_url_raises(self):
        """
        Scenario: redis backend requires REDIS_URL.
        Slice: 54 — settings validation
        Given EMBEDDING_CACHE_BACKEND=redis and REDIS_URL unset
        When ensure_cache_backend_ready() is called
        Then ValueError is raised naming REDIS_URL.
        """
        ### Given
        from server.settings import Settings

        s = Settings(
            embedding_cache_backend="redis",
            redis_url="",
            storage_backend="sqlite",
            vector_store_backend="mongodb",
        )

        ### When / Then
        with pytest.raises(ValueError, match="REDIS_URL"):
            s.ensure_cache_backend_ready()

    def test_redis_backend_with_redis_url_is_ready(self):
        """
        Scenario: redis backend with REDIS_URL set passes validation.
        Slice: 54 — settings validation
        Given EMBEDDING_CACHE_BACKEND=redis and REDIS_URL set
        When ensure_cache_backend_ready() is called
        Then no error is raised.
        """
        ### Given
        from server.settings import Settings

        s = Settings(
            embedding_cache_backend="redis",
            redis_url="redis://localhost:6379",
            storage_backend="sqlite",
            vector_store_backend="mongodb",
        )

        ### When / Then
        s.ensure_cache_backend_ready()  # must not raise


# ---------------------------------------------------------------------------
# Factory Redis dispatch (coverage for get_cache_backend redis branch)
# ---------------------------------------------------------------------------


class TestCacheBackendFactoryRedisDispatch:
    """Scenario: get_cache_backend() dispatches to RedisCacheBackend when configured."""

    def test_get_cache_backend_redis_dispatch(self, monkeypatch):
        """
        Scenario: factory returns RedisCacheBackend when EMBEDDING_CACHE_BACKEND=redis.
        Slice: 54 — factory dispatch
        Given EMBEDDING_CACHE_BACKEND=redis and REDIS_URL set
        When get_cache_backend() is called
        Then a RedisCacheBackend is returned.
        """
        ### Given
        from server.core.embedding.embedding_cache_redis import RedisCacheBackend

        reset_cache_backend()
        monkeypatch.setattr("server.settings.settings.embedding_cache_backend", "redis")
        monkeypatch.setattr("server.settings.settings.redis_url", "redis://localhost:6379")
        monkeypatch.setattr("server.settings.settings.embedding_cache_redis_ttl_s", 3600)

        ### When
        with patch("server.core.embedding.embedding_cache_redis.build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_build.return_value = mock_client
            backend = get_cache_backend()

        ### Then
        assert isinstance(backend, RedisCacheBackend)
        reset_cache_backend()  # clean up singleton for other tests


# ---------------------------------------------------------------------------
# Redis non-connection error propagates (coverage for bare raise in constructor)
# ---------------------------------------------------------------------------


class TestRedisCacheBackendNonConnectionError:
    """Scenario: non-connection errors from Redis ping propagate unchanged."""

    def test_non_connection_error_from_ping_propagates(self):
        """
        Scenario: non-connection error (e.g. auth) from ping re-raises unchanged.
        Slice: 54 — fail-closed startup
        Given a Redis client whose ping() raises a non-connection error
        When RedisCacheBackend is instantiated
        Then the original exception propagates (not wrapped as RedisUnreachableError).
        """
        ### Given
        from server.core.embedding.embedding_cache_redis import RedisCacheBackend

        class _FakeAuthError(Exception):
            pass

        ### When / Then
        with patch("server.core.embedding.embedding_cache_redis.build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.ping.side_effect = _FakeAuthError("WRONGPASS")
            mock_build.return_value = mock_client
            with pytest.raises(_FakeAuthError):
                RedisCacheBackend(url="redis://localhost:6379")
