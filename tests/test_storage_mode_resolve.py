"""
Author: Slice 37 planning/execution
Created: 2026-07-26
Scope: start-services mode resolver (engine × location) — scripts/lib/storage_mode.sh
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_LIB = _REPO / "scripts" / "lib" / "storage_mode.sh"


def _resolve(
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    Run resolve_stack_mode in a clean bash and print STACK_STORAGE_MODE.
    """
    quoted = " ".join(f"'{a}'" for a in args)
    script = f"""
set -euo pipefail
source '{_LIB}'
resolve_stack_mode {quoted}
printf 'mode=%s\\n' "$STACK_STORAGE_MODE"
printf 'db=%s\\n' "$STACK_DB_TYPE"
printf 'loc=%s\\n' "$STACK_LOCATION"
printf 'atlas=%s\\n' "$LOCAL_ATLAS"
printf 'pg=%s\\n' "$LOCAL_POSTGRES"
"""
    merged = os.environ.copy()
    for key in (
        "RAG_MONGODB_LOCAL",
        "RAG_MONGODB_CLOUD",
        "RAG_POSTGRES_LOCAL",
        "RAG_POSTGRES_CLOUD",
        "RAG_LOCAL_ATLAS",
        "RAG_LOCAL_POSTGRES",
        "STORAGE_BACKEND",
        "DATABASE_URL",
        "MONGODB_URI",
        "RAG_FORCE_BUILD",
    ):
        merged.pop(key, None)
    if env:
        merged.update(env)
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        cwd=_REPO,
        env=merged,
        check=False,
    )


def _kv(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.strip().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            out[key] = value
    return out


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (("--mongodb-local",), "mongodb-local"),
        (("--mongodb-cloud",), "mongodb-cloud"),
        (("--postgres-local",), "postgres-local"),
        (("--postgres-cloud",), "postgres-cloud"),
        (("--local",), "mongodb-local"),
        (("--postgres",), "postgres-local"),
        (("-l",), "mongodb-local"),
        (("-p",), "postgres-local"),
    ],
)
def test_canonical_and_legacy_flags_resolve_storage_mode(
    args: tuple[str, ...],
    expected: str,
) -> None:
    """
    Scenario: Each canonical flag and legacy alias maps to one storage_mode compound.
    Slice: slice-37-postgres-local-cloud-parity

    Given a single mode selector
    When resolve_stack_mode runs
    Then STACK_STORAGE_MODE equals the expected compound.
    """
    ### Given / When
    result = _resolve(*args)

    ### Then
    assert result.returncode == 0, result.stderr
    assert _kv(result.stdout)["mode"] == expected


def test_conflicting_flags_fail_before_mode_export() -> None:
    """
    Scenario: Conflicting mode selectors fail with actionable output.
    Slice: slice-37-postgres-local-cloud-parity

    Given --postgres-local and --mongodb-cloud together
    When resolve_stack_mode runs
    Then it exits non-zero and names both selectors.
    """
    ### Given / When
    result = _resolve("--postgres-local", "--mongodb-cloud")

    ### Then
    assert result.returncode == 1
    assert "conflicting mode selectors" in result.stderr
    assert "--postgres-local" in result.stderr
    assert "--mongodb-cloud" in result.stderr


def test_legacy_alias_prints_deprecation_notice() -> None:
    """
    Scenario: Legacy --postgres alias still works and warns.
    Slice: slice-37-postgres-local-cloud-parity

    Given --postgres
    When resolve_stack_mode runs
    Then mode is postgres-local and stderr mentions deprecation.
    """
    ### Given / When
    result = _resolve("--postgres")

    ### Then
    assert result.returncode == 0
    assert _kv(result.stdout)["mode"] == "postgres-local"
    assert "Deprecated:" in result.stderr
    assert "--postgres-local" in result.stderr


def test_bare_start_respects_storage_backend_postgres() -> None:
    """
    Scenario: Bare start resolves from STORAGE_BACKEND=postgres.
    Slice: slice-37-postgres-local-cloud-parity

    Given STORAGE_BACKEND=postgres and a local DATABASE_URL
    When resolve_stack_mode runs with no flags
    Then mode is postgres-local and LOCAL_POSTGRES=1.
    """
    ### Given / When
    result = _resolve(
        env={
            "STORAGE_BACKEND": "postgres",
            "DATABASE_URL": "postgresql://rag:rag@localhost:5433/rag_params_finder",
        }
    )

    ### Then
    assert result.returncode == 0, result.stderr
    data = _kv(result.stdout)
    assert data["mode"] == "postgres-local"
    assert data["pg"] == "1"
    assert data["atlas"] == "0"


def test_bare_start_defaults_to_mongodb_cloud() -> None:
    """
    Scenario: Bare start with no backend flag defaults to mongodb-cloud.
    Slice: slice-37-postgres-local-cloud-parity

    Given an empty mode environment
    When resolve_stack_mode runs with no flags
    Then mode is mongodb-cloud.
    """
    ### Given / When
    result = _resolve()

    ### Then
    assert result.returncode == 0, result.stderr
    assert _kv(result.stdout)["mode"] == "mongodb-cloud"


def test_ensure_postgres_cloud_requires_database_url_not_mongodb_uri() -> None:
    """
    Scenario: Hosted postgres ensure_env demands DATABASE_URL only.
    Slice: slice-37-postgres-local-cloud-parity

    Given --postgres-cloud without DATABASE_URL
    When ensure_stack_mode_env runs
    Then it fails mentioning DATABASE_URL and not MONGODB_URI.
    """
    ### Given
    script = f"""
set -euo pipefail
source '{_LIB}'
resolve_stack_mode --postgres-cloud
ensure_stack_mode_env
"""
    env = os.environ.copy()
    for key in (
        "RAG_MONGODB_LOCAL",
        "RAG_MONGODB_CLOUD",
        "RAG_POSTGRES_LOCAL",
        "RAG_POSTGRES_CLOUD",
        "RAG_LOCAL_ATLAS",
        "RAG_LOCAL_POSTGRES",
        "DATABASE_URL",
        "MONGODB_URI",
    ):
        env.pop(key, None)

    ### When
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        cwd=_REPO,
        env=env,
        check=False,
    )

    ### Then
    assert result.returncode == 1
    assert "DATABASE_URL" in result.stderr
    assert "MONGODB_URI" not in result.stderr


def test_ensure_postgres_local_does_not_require_mongodb_uri() -> None:
    """
    Scenario: Local postgres ensure_env never requires MONGODB_URI.
    Slice: slice-37-postgres-local-cloud-parity

    Given --postgres-local
    When ensure_stack_mode_env runs without MONGODB_URI
    Then it succeeds.
    """
    ### Given
    script = f"""
set -euo pipefail
source '{_LIB}'
resolve_stack_mode --postgres-local
ensure_stack_mode_env
printf 'ok\\n'
"""
    env = os.environ.copy()
    env.pop("MONGODB_URI", None)
    env.pop("DATABASE_URL", None)

    ### When
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        cwd=_REPO,
        env=env,
        check=False,
    )

    ### Then
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
