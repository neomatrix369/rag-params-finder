"""
Static "no duplicate run-state DB" guard (Slice 65B, DECISIONS #301 option A).

Author: Mani Sarkar
Created: 2026-11-05
Scope: Assert the repo declares exactly one SQLite run-state source — one
       named volume, one /app/data mount, one SQLITE_DB_PATH value — and that no
       script, workflow, or ignore file reintroduces a second DB or volume.

Static-only limit: this test parses compose + scans tracked text; it cannot
prove the *running* system has one file. The runtime check is
``find / -name 'run_state*.db'`` on host and in the container, plus the boot log
and ``/healthz`` ``stores.run_state.diagnostics`` (Slice 65B).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

# Option A (DECISIONS #301): the one run-state source is the named volume.
RUN_STATE_VOLUME = "sqlite_run_state"
RUN_STATE_MOUNT_TARGET = "/app/data"
EXPECTED_SQLITE_DB_PATH = "/app/data/run_state.db"

# Only the merge script may legitimately name the volume / issue volume commands.
_MERGE_SCRIPT = REPO_ROOT / "scripts" / "migrate" / "merge_run_state_dbs.py"

_VOLUME_LITERAL = "sqlite_run_state"
_DOCKER_VOLUME_CMD = re.compile(r"docker\s+volume\s+(create|rm)\b.*sqlite")
_TRACKED_DB_SUFFIX = re.compile(r"\.db(-wal|-shm)?$")
_SKIP_SUFFIXES = {".pyc"}


def _compose_files() -> list[Path]:
    return sorted(REPO_ROOT.glob("docker-compose*.yml"))


def _load_compose(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


def _service_volume_targets(doc: dict) -> list[str]:
    """Container-side mount targets across all services (short + long syntax)."""
    targets: list[str] = []
    for service in (doc.get("services") or {}).values():
        for mount in service.get("volumes") or []:
            if isinstance(mount, str):
                parts = mount.split(":")
                if len(parts) >= 2:
                    targets.append(parts[1])
            elif isinstance(mount, dict):
                target = mount.get("target")
                if target:
                    targets.append(str(target))
    return targets


def _sqlite_db_path_values(doc: dict) -> list[str]:
    """Every SQLITE_DB_PATH value declared in any service environment."""
    values: list[str] = []
    for service in (doc.get("services") or {}).values():
        env = service.get("environment")
        if isinstance(env, dict):
            if "SQLITE_DB_PATH" in env:
                values.append(str(env["SQLITE_DB_PATH"]))
        elif isinstance(env, list):
            for item in env:
                if isinstance(item, str) and item.startswith("SQLITE_DB_PATH="):
                    values.append(item.split("=", 1)[1])
    return values


def test_given_compose_files_when_parsed_then_single_run_state_volume() -> None:
    """
    Scenario: Exactly one run-state named volume exists across all compose files.
    Slice: 65B

    Given every docker-compose*.yml,
    When their top-level volumes are parsed,
    Then the only sqlite/run_state volume is the option-A sqlite_run_state.
    """
    ### Given / When
    matching: set[str] = set()
    for path in _compose_files():
        for name in _load_compose(path).get("volumes") or {}:
            lowered = name.lower()
            if "sqlite" in lowered or "run_state" in lowered:
                matching.add(name)

    ### Then
    assert matching == {RUN_STATE_VOLUME}, f"unexpected run-state volumes: {matching}"


def test_given_compose_files_when_parsed_then_app_data_target_defined_once() -> None:
    """
    Scenario: /app/data is mounted once (base) and never redefined in the overlay.
    Slice: 65B

    Given the base compose and the dev overlay,
    When their service volume targets are parsed,
    Then the base defines /app/data exactly once and the dev overlay not at all.
    """
    ### Given / When
    base = REPO_ROOT / "docker-compose.yml"
    base_targets = _service_volume_targets(_load_compose(base))

    ### Then
    assert base_targets.count(RUN_STATE_MOUNT_TARGET) == 1
    for overlay in _compose_files():
        if overlay == base:
            continue
        overlay_targets = _service_volume_targets(_load_compose(overlay))
        assert overlay_targets.count(RUN_STATE_MOUNT_TARGET) == 0, (
            f"{overlay.name} redefines {RUN_STATE_MOUNT_TARGET}"
        )


def test_given_compose_files_when_parsed_then_sqlite_db_path_is_single_value() -> None:
    """
    Scenario: SQLITE_DB_PATH resolves to the one canonical path everywhere.
    Slice: 65B

    Given every docker-compose*.yml,
    When SQLITE_DB_PATH values are collected,
    Then at least one is set and every one equals /app/data/run_state.db.
    """
    ### Given / When
    values: list[str] = []
    for path in _compose_files():
        values.extend(_sqlite_db_path_values(_load_compose(path)))

    ### Then
    assert values, "SQLITE_DB_PATH is not set in any compose file"
    assert set(values) == {EXPECTED_SQLITE_DB_PATH}, f"unexpected SQLITE_DB_PATH values: {values}"


def _scoped_text_files() -> list[Path]:
    """start-services.sh, scripts/** (incl. scripts/lib/*.tsv), and workflows.

    Compose files are validated structurally above; docs/ADR/DECISIONS are
    excluded by design (history is annotated, not rewritten).
    """
    files: list[Path] = []
    start_services = REPO_ROOT / "start-services.sh"
    if start_services.exists():
        files.append(start_services)
    for root in (REPO_ROOT / "scripts", REPO_ROOT / ".github" / "workflows"):
        if root.exists():
            files.extend(
                p
                for p in root.rglob("*")
                if p.is_file() and p.suffix not in _SKIP_SUFFIXES and "__pycache__" not in p.parts
            )
    return files


def test_given_scripts_and_workflows_when_scanned_then_no_rogue_volume_reference() -> None:
    """
    Scenario: No script or workflow names the volume or (create|rm)s a sqlite volume.
    Slice: 65B

    Given start-services.sh, scripts/** and .github/workflows/**,
    When scanned for sqlite_run_state and `docker volume (create|rm) ... sqlite`,
    Then only the allowlisted merge script may match (nothing else does).
    """
    ### Given / When
    offenders: list[str] = []
    for path in _scoped_text_files():
        if path == _MERGE_SCRIPT:
            continue
        text = path.read_text(errors="ignore")
        if _VOLUME_LITERAL in text or _DOCKER_VOLUME_CMD.search(text):
            offenders.append(str(path.relative_to(REPO_ROOT)))

    ### Then
    assert not offenders, f"rogue run-state volume references: {offenders}"


def test_given_ignore_files_when_read_then_data_dir_ignored_in_both() -> None:
    """
    Scenario: data/ is ignored for git and excluded from the Docker build context.
    Slice: 65B

    Given .gitignore and .dockerignore,
    When their entries are read,
    Then both ignore the data/ directory (no run-state DB is committed or baked).
    """

    ### Given / When
    def _entries(name: str) -> set[str]:
        return {
            line.strip()
            for line in (REPO_ROOT / name).read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        }

    ### Then
    assert "data/" in _entries(".gitignore")
    assert "data/" in _entries(".dockerignore")


def test_given_git_index_when_listed_then_no_db_files_tracked() -> None:
    """
    Scenario: No run-state DB, WAL, or SHM file is tracked in git.
    Slice: 65B

    Given the git index,
    When tracked paths are listed,
    Then none ends in .db / .db-wal / .db-shm.
    """
    ### Given / When
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    tracked_dbs = [line for line in result.stdout.splitlines() if _TRACKED_DB_SUFFIX.search(line)]

    ### Then
    assert not tracked_dbs, f"run-state DB files tracked in git: {tracked_dbs}"
