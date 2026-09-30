"""
Tests for server.db.redis.schema.

Author: swami
Created: 2026-09-30
Scope: index_name_for, field_for_dims, build_schema_fields (mocked redis imports),
       chunk_key template, constants.
"""

from __future__ import annotations

import pytest

from server.db.redis.schema import (
    ACCEPTED_EVICTION_POLICIES,
    INDEX_PREFIX,
    SUPPORTED_DIMS,
    chunk_key,
    field_for_dims,
    index_name_for,
)


class TestIndexNameForShould:
    def test_default_prefix_yields_rpf_chunks(self) -> None:
        """
        Scenario: Default prefix produces rpf:chunks index name.
        Slice: 53

        Given no prefix override,
        When index_name_for('rpf') is called,
        Then 'rpf:chunks' is returned.
        """
        ### Given / When
        result = index_name_for("rpf")

        ### Then
        assert result == "rpf:chunks"

    def test_custom_prefix_yields_custom_chunks(self) -> None:
        """
        Scenario: Custom prefix is honoured in the index name.
        Slice: 53

        Given prefix 'test',
        When index_name_for('test') is called,
        Then 'test:chunks' is returned.
        """
        ### Given / When
        result = index_name_for("test")

        ### Then
        assert result == "test:chunks"

    def test_empty_prefix_falls_back_to_rpf(self) -> None:
        """
        Scenario: Empty prefix falls back to 'rpf'.
        Slice: 53

        Given an empty string prefix,
        When index_name_for('') is called,
        Then 'rpf:chunks' is returned.
        """
        ### Given / When
        result = index_name_for("")

        ### Then
        assert result == "rpf:chunks"

    def test_whitespace_only_prefix_falls_back_to_rpf(self) -> None:
        """
        Scenario: Whitespace-only prefix falls back to 'rpf'.
        Slice: 53

        Given a whitespace-only prefix,
        When index_name_for('   ') is called,
        Then 'rpf:chunks' is returned.
        """
        ### Given / When
        result = index_name_for("   ")

        ### Then
        assert result == "rpf:chunks"


class TestFieldForDimsShould:
    def test_returns_embedding_384_for_384_dims(self) -> None:
        """
        Scenario: 384-dim maps to the local model VECTOR field.
        Slice: 53

        Given dimensions=384,
        When field_for_dims() is called,
        Then 'embedding_384' is returned.
        """
        ### Given / When
        result = field_for_dims(384)

        ### Then
        assert result == "embedding_384"

    def test_returns_embedding_1024_for_1024_dims(self) -> None:
        """
        Scenario: 1024-dim maps to the Voyage model VECTOR field.
        Slice: 53

        Given dimensions=1024,
        When field_for_dims() is called,
        Then 'embedding_1024' is returned.
        """
        ### Given / When
        result = field_for_dims(1024)

        ### Then
        assert result == "embedding_1024"

    def test_raises_for_unsupported_dims(self) -> None:
        """
        Scenario: Unsupported dimensions raises ValueError with guidance.
        Slice: 53

        Given dimensions=512 (not in SUPPORTED_DIMS),
        When field_for_dims() is called,
        Then ValueError is raised listing supported dims.
        """
        ### Given / When / Then
        with pytest.raises(ValueError, match="512"):
            field_for_dims(512)

    def test_raises_for_sparse_30522_dims(self) -> None:
        """
        Scenario: SPLADE 30522-dim embeddings are rejected.
        Slice: 53

        Given dimensions=30522 (SPLADE sparse),
        When field_for_dims() is called,
        Then ValueError is raised.
        """
        ### Given / When / Then
        with pytest.raises(ValueError):
            field_for_dims(30522)


class TestBuildSchemaFieldsShould:
    def test_returns_list_of_field_objects(self, fake_redis_modules: dict) -> None:
        """
        Scenario: build_schema_fields returns a list of field definitions.
        Slice: 53

        Given the redis.commands.search.field module is available (mocked),
        When build_schema_fields() is called,
        Then a non-empty list is returned.
        """
        ### Given
        from server.db.redis.schema import build_schema_fields

        ### When
        fields = build_schema_fields()

        ### Then
        assert isinstance(fields, list)
        assert len(fields) > 0

    def test_creates_both_vector_fields(self, fake_redis_modules: dict) -> None:
        """
        Scenario: build_schema_fields creates embedding_384 and embedding_1024 VectorField.
        Slice: 53

        Given mock field classes,
        When build_schema_fields() is called,
        Then VectorField is constructed twice (once per supported dim).
        """
        ### Given
        fields_mock = fake_redis_modules["fields"]
        vector_field_cls = fields_mock.VectorField
        from server.db.redis.schema import build_schema_fields

        ### When
        build_schema_fields()

        ### Then
        assert vector_field_cls.call_count == 2

    def test_uses_cosine_distance_for_both_vector_fields(self, fake_redis_modules: dict) -> None:
        """
        Scenario: Both HNSW VECTOR fields use COSINE distance metric.
        Slice: 53

        Given mock VectorField class,
        When build_schema_fields() is called,
        Then all VectorField calls specify DISTANCE_METRIC=COSINE.
        """
        ### Given
        vector_field_cls = fake_redis_modules["fields"].VectorField
        from server.db.redis.schema import build_schema_fields

        ### When
        build_schema_fields()

        ### Then
        for call in vector_field_cls.call_args_list:
            # The HNSW attrs dict is passed as positional arg [2]
            _, _, hnsw_attrs = call[0]
            assert hnsw_attrs["DISTANCE_METRIC"] == "COSINE"


class TestChunkKeyShould:
    def test_produces_canonical_key_format(self) -> None:
        """
        Scenario: chunk_key generates the expected key string.
        Slice: 53

        Given experiment_id, run_id, chunk_id,
        When chunk_key() is called,
        Then the key follows the rpf:chunk:{exp}:{run}:{chunk} pattern.
        """
        ### Given
        exp = "exp-abc"
        run = "run-001"
        chunk = "c42"

        ### When
        result = chunk_key(exp, run, chunk)

        ### Then
        assert result == f"rpf:chunk:{exp}:{run}:{chunk}"

    def test_index_prefix_constant_is_rpf_chunk(self) -> None:
        """
        Scenario: INDEX_PREFIX constant matches the key prefix used by chunk_key.
        Slice: 53

        Given INDEX_PREFIX,
        Then it starts with 'rpf:chunk:'.
        """
        ### Given / Then
        assert INDEX_PREFIX == "rpf:chunk:"


class TestConstantsShould:
    def test_supported_dims_contains_384_and_1024(self) -> None:
        """
        Scenario: SUPPORTED_DIMS includes both local and Voyage dimensions.
        Slice: 53
        """
        ### Given / Then
        assert 384 in SUPPORTED_DIMS
        assert 1024 in SUPPORTED_DIMS

    def test_accepted_eviction_policies_excludes_allkeys(self) -> None:
        """
        Scenario: allkeys-* eviction policies are not in the accepted set.
        Slice: 53

        allkeys-* policies can delete vector data and must be rejected.
        """
        ### Given / Then
        for policy in ACCEPTED_EVICTION_POLICIES:
            assert not policy.startswith("allkeys-"), f"{policy!r} should not be accepted"

    def test_noeviction_is_accepted(self) -> None:
        """
        Scenario: noeviction policy is always safe.
        Slice: 53
        """
        ### Given / Then
        assert "noeviction" in ACCEPTED_EVICTION_POLICIES
