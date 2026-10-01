"""GWT tests for embedding_cache — thread-safe SQLite vector cache.

Author: Claude Haiku 4.5
Created: 2026-09-30
Scope: embedding_cache.py module — cache_key determinism, get_many/put_many CRUD,
       singleton lifecycle, temp dir warning.
"""

from __future__ import annotations

import sqlite3
import tempfile
import warnings
from pathlib import Path

import pytest

from server.core.embedding.embedding_cache import (
    EmbeddingCache,
    cache_key,
    get_embedding_cache,
    reset_embedding_cache,
)


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


class TestEmbeddingCacheCRUD:
    """Scenario: EmbeddingCache stores and retrieves vectors."""

    @pytest.fixture
    def temp_cache_path(self) -> str:
        """Temporary cache database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield str(Path(tmpdir) / "test_cache.db")

    def test_get_many_empty_cache_returns_empty_dict(self, temp_cache_path):
        """
        Scenario: get many empty cache returns empty dict.
        Slice: 48A — cache read
        Given an empty cache
        When get_many(keys) is called
        Then an empty dict is returned.
        """
        ### Given
        cache = EmbeddingCache(temp_cache_path)
        cache.init_db()

        ### When
        result = cache.get_many(["key1", "key2"])

        ### Then
        assert result == {}

    def test_put_many_then_get_many_retrieves_vectors(self, temp_cache_path):
        """
        Scenario: put many then get many retrieves vectors.
        Slice: 48A — cache round-trip
        Given vectors to store
        When put_many() stores them and get_many() retrieves them
        Then the retrieved vectors match the stored ones.
        """
        ### Given
        cache = EmbeddingCache(temp_cache_path)
        cache.init_db()
        vectors = {"key1": [0.1, 0.2, 0.3], "key2": [0.4, 0.5, 0.6]}

        ### When
        cache.put_many(vectors)
        result = cache.get_many(["key1", "key2"])

        ### Then
        assert len(result) == 2
        assert result["key1"] == pytest.approx([0.1, 0.2, 0.3])
        assert result["key2"] == pytest.approx([0.4, 0.5, 0.6])

    def test_get_many_missing_keys_absent_from_result(self, temp_cache_path):
        """
        Scenario: get many missing keys absent from result.
        Slice: 48A — cache partial retrieval
        Given some keys in cache and some missing
        When get_many(all_keys) is called
        Then only cached keys appear in result.
        """
        ### Given
        cache = EmbeddingCache(temp_cache_path)
        cache.init_db()
        cache.put_many({"key1": [0.1, 0.2]})

        ### When
        result = cache.get_many(["key1", "key_missing"])

        ### Then
        assert "key1" in result
        assert "key_missing" not in result

    def test_put_many_with_prompt_tokens_stores_metadata(self, temp_cache_path):
        """
        Scenario: put many with prompt tokens stores metadata.
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
        # Verify the data was stored by checking the database directly
        conn = sqlite3.connect(temp_cache_path)
        row = conn.execute(
            "SELECT prompt_tokens FROM embedding_vectors WHERE key='key1'"
        ).fetchone()
        conn.close()
        assert row[0] == 42

    def test_cached_keys_returns_frozenset_of_present_keys(self, temp_cache_path):
        """
        Scenario: cached keys returns frozenset of present keys.
        Slice: 48A — cache subset check
        Given some keys cached, some missing
        When cached_keys(all_keys) is called
        Then a frozenset of present keys is returned.
        """
        ### Given
        cache = EmbeddingCache(temp_cache_path)
        cache.init_db()
        cache.put_many({"key1": [0.1], "key2": [0.2]})

        ### When
        result = cache.cached_keys(["key1", "key2", "key3"])

        ### Then
        assert isinstance(result, frozenset)
        assert result == frozenset(["key1", "key2"])


class TestEmbeddingCacheSingleton:
    """Scenario: get_embedding_cache returns a singleton."""

    def test_get_embedding_cache_returns_singleton(self, monkeypatch):
        """
        Scenario: get embedding cache returns singleton.
        Slice: 48A — cache lifecycle
        Given get_embedding_cache is called twice
        When both calls return a cache
        Then they return the same object instance.
        """
        ### Given
        reset_embedding_cache()  # Clear any prior singleton
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "test.db")
            monkeypatch.setattr("server.settings.settings.embedding_cache_path", cache_path)

            ### When
            cache1 = get_embedding_cache()
            cache2 = get_embedding_cache()

            ### Then
            assert cache1 is cache2

    def test_reset_embedding_cache_clears_singleton(self, monkeypatch):
        """
        Scenario: reset embedding cache clears singleton.
        Slice: 48A — test helper
        Given a cached singleton
        When reset_embedding_cache() is called
        Then get_embedding_cache() returns a different object.
        """
        ### Given
        reset_embedding_cache()
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "test.db")
            monkeypatch.setattr("server.settings.settings.embedding_cache_path", cache_path)
            cache1 = get_embedding_cache()

            ### When
            reset_embedding_cache()
            cache2 = get_embedding_cache()

            ### Then
            assert cache1 is not cache2


class TestEmbeddingCacheWarnings:
    """Scenario: EmbeddingCache warns when path is under temp directory."""

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

        ### When
        with pytest.warns(UserWarning, match="temp directory"):
            EmbeddingCache(temp_path)

        ### Then
        # Warning was raised (assertion is implicit in pytest.warns)

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

        ### When
        with pytest.warns(UserWarning, match="temp directory"):
            EmbeddingCache(temp_path)

        ### Then
        # Warning was raised

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
        # Filter out unrelated warnings from dependencies
        cache_warnings = [x for x in w if "temp directory" in str(x.message)]
        assert len(cache_warnings) == 0
