"""
Tests for scripts/lib/stores.tsv and operator script dispatch.

Author: swami
Created: 2026-09-27
Scope: manifest parity with the Python registry; no per-store case arms
"""

from __future__ import annotations

import re
from pathlib import Path

from server.db.ports.registry import example_config_for, known_vector_stores
from tests.helpers.repo_paths import repo_root_from

_REPO = repo_root_from(Path(__file__))
_STORE_CASE = re.compile(r"^\s*(mongodb|postgres|elasticsearch)(-local|-cloud)?\)", re.MULTILINE)
_PER_STORE_LIFECYCLE = re.compile(
    r"^cmd_(mongodb|postgres|elasticsearch)_(start|stop|reset|status)\(\)"
    r"|^run_(mongodb|postgres)_subcommand\(\)",
    re.MULTILINE,
)
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
    lifecycle = [
        f"{path.name}: {match.group(0)}"
        for path in _OPERATOR_SCRIPTS
        for match in _PER_STORE_LIFECYCLE.finditer(path.read_text())
    ]
    assert lifecycle == []
    start_script = (_REPO / "start-services.sh").read_text()
    compose = (_REPO / "scripts" / "lib" / "compose.sh").read_text()
    assert "cmd_store_start()" in start_script
    assert "wait_for_named_container_healthy()" in compose


def test_given_stores_tsv_when_example_config_read_then_it_matches_the_registry() -> None:
    """
    Scenario: The manifest example config is the registry example config.
    Slice: 51

    Given scripts/lib/stores.tsv,
    When each provider's example_config column is read,
    Then it matches example_config_for(provider).
    """
    ### Given / When
    rows = [
        line.split("\t")
        for line in (_REPO / "scripts" / "lib" / "stores.tsv").read_text().splitlines()
        if line and not line.startswith("provider") and not line.startswith("#")
    ]

    ### Then
    for columns in rows:
        provider, example_config, volumes = columns[0], columns[6], columns[7]
        assert example_config == example_config_for(provider)
        assert volumes.strip() != ""


def test_given_server_dockerfile_when_read_then_extras_build_arg_is_optional() -> None:
    """
    Scenario: Server image extra is opt-in.
    Slice: 51

    Given docker/server.Dockerfile (base+derived stage pattern),
    When the deps stages are read,
    Then the default server target installs no VDB extras,
    and each VDB extra gets its own named deps stage.
    """
    ### Given
    text = (_REPO / "docker" / "server.Dockerfile").read_text()

    ### When / Then
    # Default core-deps stage has no --extra flag
    assert "AS core-deps" in text
    assert (
        "--extra elasticsearch"
        not in text.split("AS core-deps")[1].split("AS elasticsearch-deps")[0]
    )
    # VDB-specific extras go in dedicated named stages
    assert "AS elasticsearch-deps" in text
    assert "--extra elasticsearch" in text
    assert "AS redis-deps" in text
    assert "--extra redis" in text
