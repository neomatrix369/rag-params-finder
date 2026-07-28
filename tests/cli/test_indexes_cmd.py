"""
Tests for cli.indexes_cmd.

Author: Mani Sarkar
Created: 2026-07-26
Scope: non-mongo STORAGE_BACKEND short-circuit for indexes list/reset
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import typer

from cli.indexes_cmd import indexes_list, indexes_reset
from server.core.search_index_plan import SearchIndexSnapshot


class TestIndexesCmdBackendGuardShould:
    """Scenario: indexes list works on Postgres catalog; reset stays Atlas-only."""

    def test_given_postgres_backend_when_indexes_list_then_lists_catalog(
        self,
    ) -> None:
        """
        Scenario: given postgres backend when indexes list then lists catalog.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Postgres stacks list HNSW/GIN presence without Atlas I/O.
        Slice: slice-36-postgres-preflight-stats

        Given STORAGE_BACKEND=postgres and a catalog snapshot,
        When indexes list runs,
        Then it does not call Atlas list APIs.
        """
        ### Given / When
        required = frozenset(
            {
                "chunks_embedding_384_hnsw",
                "chunks_embedding_1024_hnsw",
                "chunks_text_search_gin",
            }
        )
        ready = SearchIndexSnapshot(
            chunks_ready=required,
            chunks_building=frozenset(),
            cluster_total=3,
            cluster_limit=3,
            unknown_count=0,
        )
        with (
            patch("cli.indexes_cmd.settings.storage_backend", "postgres"),
            patch("cli.indexes_cmd.list_cluster_search_indexes") as list_indexes,
            patch(
                "cli.indexes_cmd.postgres_vector_extension_present",
                return_value=True,
            ),
            patch(
                "cli.indexes_cmd.collect_postgres_index_snapshot",
                return_value=ready,
            ),
        ):
            indexes_list()

        ### Then
        list_indexes.assert_not_called()

    def test_given_postgres_backend_when_indexes_reset_then_exits_without_atlas(
        self,
    ) -> None:
        """
        Scenario: given postgres backend when indexes reset then exits without atlas.
        Slice: 45 — GWT-on-touch (module theme separation)
        """
        ### Given
        ### When
        ### Then
        """
        Scenario: Postgres stacks do not open Atlas for index reset.
        Slice: slice-36-postgres-preflight-stats

        Given STORAGE_BACKEND=postgres,
        When indexes reset runs,
        Then it exits as Atlas-only and never mutates Atlas indexes.
        """
        ### Given / When / Then
        with (
            patch("cli.indexes_cmd.settings.storage_backend", "postgres"),
            patch("cli.indexes_cmd.list_cluster_search_indexes") as list_indexes,
            patch("cli.indexes_cmd.prune_unknown_search_indexes") as prune_indexes,
            pytest.raises(typer.Exit) as exited,
        ):
            indexes_reset(unknown_only=True, force=True)

        ### Then
        assert exited.value.exit_code == 0
        list_indexes.assert_not_called()
        prune_indexes.assert_not_called()
