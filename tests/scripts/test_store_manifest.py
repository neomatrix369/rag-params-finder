"""
Tests for scripts/lib/stores.tsv and operator script dispatch.

Author: swami
Created: 2026-09-27
Scope: manifest parity with the Python registry; no per-store case arms
"""

from __future__ import annotations

import re
from pathlib import Path

from server.db.ports.registry import known_vector_stores
from tests.helpers.repo_paths import repo_root_from

_REPO = repo_root_from(Path(__file__))
_STORE_CASE = re.compile(r"^\s*(mongodb|postgres|elasticsearch)(-local|-cloud)?\)", re.MULTILINE)
_OPERATOR_SCRIPTS = (
    _REPO / "start-services.sh",
    _REPO / "stop-services.sh",
    _REPO / "scripts" / "docker" / "health-check.sh",
)


def test_given_stores_tsv_when_providers_read_then_they_match_the_registry() -> None:
    """
    Scenario: Script manifest matches the Python registry.
    Slice: 51

    Given scripts/lib/stores.tsv and known_vector_stores(),
    When the providers are compared,
    Then both lists are the same.
    """
    ### Given
    rows = []
    for line in (_REPO / "scripts" / "lib" / "stores.tsv").read_text().splitlines():
        if not line or line.startswith("provider") or line.startswith("#"):
            continue
        rows.append(line.split("\t")[0])

    ### When
    actual = set(rows)

    ### Then
    assert actual == set(known_vector_stores())


def test_given_operator_scripts_when_scanned_then_no_per_store_case_arm() -> None:
    """
    Scenario: start/stop/health-check scripts contain no per-store case branch.
    Slice: 51

    Given the three operator scripts,
    When their case arms are scanned,
    Then none is named after a vector store.
    """
    ### Given / When
    offenders = [
        f"{path.name}: {match.group(0).strip()}"
        for path in _OPERATOR_SCRIPTS
        for match in _STORE_CASE.finditer(path.read_text())
    ]

    ### Then
    assert offenders == []


def test_given_server_dockerfile_when_read_then_extras_build_arg_is_optional() -> None:
    """
    Scenario: Server image extra is opt-in.
    Slice: 51

    Given docker/server.Dockerfile,
    When the deps stage is read,
    Then EXTRAS defaults empty and uv sync adds --extra only when set.
    """
    ### Given
    text = (_REPO / "docker" / "server.Dockerfile").read_text()

    ### When / Then
    assert 'ARG EXTRAS=""' in text
    assert "${EXTRAS:+--extra $EXTRAS}" in text
