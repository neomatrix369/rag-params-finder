"""
Tests for server.db.ports.vector_store.VectorCapabilities.

Author: Mani Sarkar
Created: 2026-09-27
Scope: VectorCapabilities value-object contract — construction, defaults,
       immutability, and value equality (Slice 49A Stream 2).
"""

from __future__ import annotations

import dataclasses

import pytest

from server.db.ports.vector_store import VectorCapabilities
from server.models.enums import RetrievalMethod


def _mongodb_like_capabilities() -> VectorCapabilities:
    return VectorCapabilities(
        retrieval_methods=frozenset(
            {RetrievalMethod.DENSE, RetrievalMethod.SPARSE, RetrievalMethod.HYBRID}
        ),
        similarity_metrics=frozenset({"cosine"}),
        index_types=frozenset({"atlas_vector_search", "atlas_search"}),
        supported_embedding_dims=frozenset({384, 1024}),
        supports_metadata_filters=True,
        can_host_run_state=True,
    )


class TestVectorCapabilitiesShould:
    """Scenario: VectorCapabilities is the declared capability set guards read
    instead of branching on engine name."""

    def test_given_required_fields_when_constructed_then_every_field_is_readable(
        self,
    ) -> None:
        """
        Scenario: build a capability set with no hidden state or defaults required.

        Given the full set of required VectorCapabilities fields,
        When VectorCapabilities is constructed,
        Then every field is available for read exactly as passed.
        """
        ### Given
        fields = {
            "retrieval_methods": frozenset({RetrievalMethod.DENSE}),
            "similarity_metrics": frozenset({"cosine"}),
            "index_types": frozenset({"hnsw"}),
            "supported_embedding_dims": frozenset({1024}),
            "supports_metadata_filters": True,
            "can_host_run_state": True,
        }

        ### When
        capabilities = VectorCapabilities(**fields)

        ### Then
        assert capabilities.retrieval_methods == fields["retrieval_methods"]
        assert capabilities.similarity_metrics == fields["similarity_metrics"]
        assert capabilities.index_types == fields["index_types"]
        assert capabilities.supported_embedding_dims == fields["supported_embedding_dims"]
        assert capabilities.supports_metadata_filters is True
        assert capabilities.can_host_run_state is True

    def test_given_no_labels_argument_when_constructed_then_labels_defaults_to_empty_frozenset(
        self,
    ) -> None:
        """
        Scenario: labels is an optional, additive field.

        Given no labels keyword argument,
        When VectorCapabilities is constructed,
        Then labels defaults to an empty frozenset rather than requiring the
        caller to pass one.
        """
        ### Given
        ### When
        capabilities = _mongodb_like_capabilities()

        ### Then
        assert capabilities.labels == frozenset()

    def test_given_constructed_instance_when_field_assigned_then_frozen_instance_error_raised(
        self,
    ) -> None:
        """
        Scenario: capability sets are immutable value objects.

        Given a constructed VectorCapabilities,
        When a field is assigned after construction,
        Then a FrozenInstanceError is raised, matching the frozen-dataclass
        convention already used by server/core/guards/search_index_plan.py.
        """
        ### Given
        capabilities = _mongodb_like_capabilities()

        ### When
        ### Then
        with pytest.raises(dataclasses.FrozenInstanceError):
            capabilities.can_host_run_state = False  # type: ignore[misc]

    def test_given_two_equivalent_instances_when_compared_then_they_are_equal_but_not_identical(
        self,
    ) -> None:
        """
        Scenario: two capability sets built from the same fields are equal.

        Given two VectorCapabilities built from identical arguments,
        When they are compared with ==,
        Then they compare equal (dataclass value semantics) while remaining
        two distinct objects.
        """
        ### Given
        first = _mongodb_like_capabilities()
        second = _mongodb_like_capabilities()

        ### When
        ### Then
        assert first == second
        assert first is not second

    def test_given_can_host_run_state_false_when_compared_to_run_state_capable_set_then_differ(
        self,
    ) -> None:
        """
        Scenario: an Elasticsearch-shaped store declares can_host_run_state=False.

        Given a capability set with can_host_run_state=False,
        When it is compared to a run-state-capable set,
        Then the two are not equal and the flag is readable directly.
        """
        ### Given
        run_state_capable = _mongodb_like_capabilities()
        vector_only = dataclasses.replace(
            run_state_capable,
            can_host_run_state=False,
            index_types=frozenset({"hnsw_es"}),
        )

        ### When
        ### Then
        assert vector_only.can_host_run_state is False
        assert vector_only != run_state_capable
