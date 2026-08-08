"""Verifies CLI index commands respect storage backend — Postgres catalog, Atlas reset only.

Author: Mani Sarkar
Created: 2026-07-26
Scope: cli/indexes_cmd.py — list and reset subcommands, unit, mocked search index adapters
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import typer

from cli.indexes_cmd import indexes_list, indexes_reset
from server.core.search_index_plan import SearchIndexSnapshot


class TestIndexesCmdBackendGuardShould:
    """Verifies storage-backend-aware index commands — Postgres and Atlas switching."""

    def test_indexes_list_command_uses_postgres_catalog_when_backend_is_postgres(
        self,
    ) -> None:
        """Postgres backend skips Atlas APIs when listing search indexes.

        Scenario: Postgres RAG backend lists vector search indexes from local catalog.
        Slice: slice-36 — Postgres preflight and statistics

        Given STORAGE_BACKEND is set to "postgres" with valid pgvector catalog
        When the indexes list command runs
        Then command calls Postgres catalog introspection (vector extension checks,
        HNSW/GIN index presence) and does not invoke Atlas list APIs
        """
        ### Given
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

        ### When
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

    def test_indexes_reset_command_exits_when_backend_is_postgres(
        self,
    ) -> None:
        """Postgres backend does not support index reset — exits gracefully.

        Scenario: Atlas-only index management commands block on non-Atlas backends.
        Slice: slice-36 — Postgres preflight and statistics

        Given STORAGE_BACKEND is set to "postgres"
        When the indexes reset command is called
        Then command exits with status 0 (informative exit, not error) and does not
        call Atlas APIs or prune any indexes
        """
        ### Given
        ### When
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
