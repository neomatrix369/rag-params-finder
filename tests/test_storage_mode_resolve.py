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

# Every env var that can steer mode resolution. Cleared before each scenario so a
# developer's own .env / shell (e.g. an exported SUPABASE_URI) cannot change outcomes.
_MODE_ENV_KEYS = (
    "RAG_MONGODB_LOCAL",
    "RAG_MONGODB_CLOUD",
    "RAG_POSTGRES_LOCAL",
    "RAG_POSTGRES_CLOUD",
    "RAG_LOCAL_ATLAS",
    "RAG_LOCAL_POSTGRES",
    "STORAGE_BACKEND",
    "DATABASE_URL",
    "SUPABASE_URI",
    "MONGODB_URI",
    "RAG_FORCE_BUILD",
)


def _clean_env(**overrides: str) -> dict[str, str]:
    """Process env with every mode selector removed, plus explicit overrides."""
    env = os.environ.copy()
    for key in _MODE_ENV_KEYS:
        env.pop(key, None)
    env.update(overrides)
    return env


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
    merged = _clean_env(**(env or {}))
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
    ],
)
def test_canonical_flags_resolve_storage_mode(
    args: tuple[str, ...],
    expected: str,
) -> None:
    """
    Scenario: Each canonical flag maps to one storage_mode compound.
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


@pytest.mark.parametrize(
    ("env_var", "expected"),
    [
        ("RAG_MONGODB_LOCAL", "mongodb-local"),
        ("RAG_MONGODB_CLOUD", "mongodb-cloud"),
        ("RAG_POSTGRES_LOCAL", "postgres-local"),
        ("RAG_POSTGRES_CLOUD", "postgres-cloud"),
    ],
)
def test_canonical_env_selectors_resolve_storage_mode(env_var: str, expected: str) -> None:
    """
    Scenario: Each canonical RAG_* env selector maps to one storage_mode compound.
    Slice: slice-37-postgres-local-cloud-parity

    Given a single RAG_* env selector set to 1 and no flags
    When resolve_stack_mode runs
    Then STACK_STORAGE_MODE equals the expected compound.
    """
    ### Given / When
    result = _resolve(env={env_var: "1"})

    ### Then
    assert result.returncode == 0, result.stderr
    assert _kv(result.stdout)["mode"] == expected


@pytest.mark.parametrize(
    ("env_var", "expected", "replacement"),
    [
        ("RAG_LOCAL_ATLAS", "mongodb-local", "--mongodb-local"),
        ("RAG_LOCAL_POSTGRES", "postgres-local", "--postgres-local"),
    ],
)
def test_deprecated_env_selectors_still_resolve_and_warn(
    env_var: str,
    expected: str,
    replacement: str,
) -> None:
    """
    Scenario: Deprecated RAG_LOCAL_* env selectors keep working and warn.
    Slice: slice-37-postgres-local-cloud-parity

    Given a deprecated RAG_LOCAL_* env selector set to 1
    When resolve_stack_mode runs
    Then the mode still resolves and stderr names the canonical replacement.
    """
    ### Given / When
    result = _resolve(env={env_var: "1"})

    ### Then
    assert result.returncode == 0, result.stderr
    assert _kv(result.stdout)["mode"] == expected
    assert "Deprecated:" in result.stderr
    assert replacement in result.stderr


def test_empty_database_url_resolves_postgres_cloud() -> None:
    """
    Scenario: An empty DATABASE_URL is treated as unset, not as a local URI.
    Slice: slice-37-postgres-local-cloud-parity

    Given STORAGE_BACKEND=postgres and DATABASE_URL set to an empty string
    When resolve_stack_mode runs with no flags
    Then the location falls back to cloud rather than matching localhost.
    """
    ### Given / When
    result = _resolve(env={"STORAGE_BACKEND": "postgres", "DATABASE_URL": ""})

    ### Then
    assert result.returncode == 0, result.stderr
    assert _kv(result.stdout)["mode"] == "postgres-cloud"


def test_local_postgres_hints_never_echo_operator_database_url() -> None:
    """
    Scenario: Post-start hints never leak the operator's connection secret.
    Slice: slice-37-postgres-local-cloud-parity

    Given DATABASE_URL holds a hosted URI containing a password
    When print_local_postgres_cli_hints renders the operator hints
    Then the password never appears in the output.
    """
    ### Given
    secret = "s3cr3t-not-for-stdout"  # noqa: S105 - test fixture, not a real credential
    hosted_uri = (
        f"postgresql://postgres.ref:{secret}@aws-0-eu-west-2.pooler.supabase.com:5432/postgres"
    )
    script = f"""
set -euo pipefail
source '{_LIB}'
source '{_REPO / "scripts" / "lib" / "compose.sh"}'
print_local_postgres_cli_hints
"""
    env = _clean_env(DATABASE_URL=hosted_uri, SUPABASE_URI=hosted_uri)

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
    assert secret not in result.stdout
    assert secret not in result.stderr


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


@pytest.mark.parametrize("flag", ["--local", "-l", "--postgres", "-p"])
def test_removed_alias_flags_are_rejected(flag: str) -> None:
    """
    Scenario: Removed alias flags fail as unknown options.
    Slice: slice-37-postgres-local-cloud-parity

    Given a removed alias flag such as --local or --postgres
    When resolve_stack_mode runs
    Then it exits non-zero and reports an unknown option.
    """
    ### Given / When
    result = _resolve(flag)

    ### Then
    assert result.returncode != 0
    assert "Unknown option" in result.stderr


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
    env = _clean_env()

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
    assert "DATABASE_URL" in result.stderr or "SUPABASE_URI" in result.stderr
    assert "MONGODB_URI" not in result.stderr


def test_ensure_postgres_cloud_accepts_supabase_uri_alias() -> None:
    """
    Scenario: SUPABASE_URI satisfies hosted postgres ensure_env when DATABASE_URL unset.
    Slice: slice-37-postgres-local-cloud-parity

    Given --postgres-cloud with SUPABASE_URI only
    When ensure_stack_mode_env runs
    Then it succeeds and DATABASE_URL is exported from the alias.
    """
    ### Given
    script = f"""
set -euo pipefail
source '{_LIB}'
resolve_stack_mode --postgres-cloud
ensure_stack_mode_env
printf 'database_url=%s\\n' "$DATABASE_URL"
"""
    env = _clean_env(
        SUPABASE_URI="postgresql://postgres:secret@db.example.supabase.co:5432/postgres"
    )

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
    expected = "database_url=postgresql://postgres:secret@db.example.supabase.co:5432/postgres"
    assert expected in result.stdout


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
    env = _clean_env()

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


def test_mongodb_local_exports_storage_backend_over_hostile_postgres_env() -> None:
    """
    Scenario: --mongodb-local forces STORAGE_BACKEND=mongodb despite leftover postgres.
    Slice: slice-38-cutover-adr-004

    Given STORAGE_BACKEND=postgres in the environment
    When resolve_stack_mode --mongodb-local and export_storage_backend_for_stack run
    Then STORAGE_BACKEND is mongodb.
    """
    ### Given
    script = f"""
set -euo pipefail
source '{_LIB}'
resolve_stack_mode --mongodb-local
export_storage_backend_for_stack
printf 'backend=%s\\n' "$STORAGE_BACKEND"
printf 'mode=%s\\n' "$STACK_STORAGE_MODE"
"""
    env = _clean_env(STORAGE_BACKEND="postgres")

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
    data = _kv(result.stdout)
    assert data["backend"] == "mongodb", result.stdout
    assert data["mode"] == "mongodb-local"


def test_mongodb_cloud_exports_storage_backend_over_hostile_postgres_env() -> None:
    """
    Scenario: --mongodb-cloud forces STORAGE_BACKEND=mongodb despite leftover postgres.
    Slice: slice-38-cutover-adr-004

    Given STORAGE_BACKEND=postgres in the environment
    When resolve_stack_mode --mongodb-cloud and export_storage_backend_for_stack run
    Then STORAGE_BACKEND is mongodb.
    """
    ### Given
    script = f"""
set -euo pipefail
source '{_LIB}'
resolve_stack_mode --mongodb-cloud
export_storage_backend_for_stack
printf 'backend=%s\\n' "$STORAGE_BACKEND"
"""
    env = _clean_env(STORAGE_BACKEND="postgres")

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
    assert _kv(result.stdout)["backend"] == "mongodb"


def test_ensure_postgres_cloud_rejects_project_ref_placeholder() -> None:
    """
    Scenario: Placeholder Supabase URI fails closed with a clear remediation.
    Slice: slice-38-cutover-adr-004

    Given --postgres-cloud and DATABASE_URL containing <project-ref>
    When ensure_stack_mode_env runs
    Then it exits non-zero and names DATABASE_URL / SUPABASE_URI.
    """
    ### Given
    placeholder = (
        "postgresql://postgres.<project-ref>:<password>"
        "@aws-0-<region>.pooler.supabase.com:5432/postgres"
    )
    script = f"""
set -euo pipefail
source '{_LIB}'
resolve_stack_mode --postgres-cloud
ensure_stack_mode_env
"""
    env = _clean_env(DATABASE_URL=placeholder)

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
    assert "placeholder" in result.stderr.lower() or "<project-ref>" in result.stderr
    assert "DATABASE_URL" in result.stderr or "SUPABASE_URI" in result.stderr
