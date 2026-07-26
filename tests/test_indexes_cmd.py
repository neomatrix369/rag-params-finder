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


class TestIndexesCmdBackendGuardShould:
    """Scenario: Atlas index commands are Mongo-only."""

    def test_given_postgres_backend_when_indexes_list_then_exits_without_atlas(
        self,
    ) -> None:
        """
        Scenario: Postgres stacks do not open Atlas for index listing.
        Slice: 43 — Supabase/Postgres operator parity

        Given STORAGE_BACKEND=postgres,
        When indexes list runs,
        Then it exits as not applicable and never lists Atlas indexes.
        """
        ### Given / When / Then
        with (
            patch("cli.indexes_cmd.settings.storage_backend", "postgres"),
            patch("cli.indexes_cmd.list_cluster_search_indexes") as list_indexes,
            pytest.raises(typer.Exit) as exited,
        ):
            indexes_list()

        ### Then
        assert exited.value.exit_code == 0
        list_indexes.assert_not_called()

    def test_given_postgres_backend_when_indexes_reset_then_exits_without_atlas(
        self,
    ) -> None:
        """
        Scenario: Postgres stacks do not open Atlas for index reset.
        Slice: 43 — Supabase/Postgres operator parity

        Given STORAGE_BACKEND=postgres,
        When indexes reset runs,
        Then it exits as not applicable and never mutates Atlas indexes.
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
