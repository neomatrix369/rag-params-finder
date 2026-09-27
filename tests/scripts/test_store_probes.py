"""
Executable checks for manifest health probes and teardown profile flags.

Author: RAG Params Finder contributors
Created: 2026-09-27
Scope: cmd: probe execution and stop-services profile coverage
"""

from __future__ import annotations

import os
import stat
import subprocess
import textwrap
from pathlib import Path

from tests.helpers.repo_paths import repo_root_from

_REPO = repo_root_from(Path(__file__))


def _fake_docker(bin_dir: Path, log_path: Path, exec_status: int) -> None:
    script = textwrap.dedent(
        f"""\
        #!/bin/bash
        printf '%s\\n' "$*" >> "{log_path}"
        if [[ "$1" == "inspect" ]]; then
          if [[ "$*" == *State.Status* ]]; then
            echo running
          elif [[ "$*" == *Health.Status* ]]; then
            echo healthy
          else
            echo container-id
          fi
          exit 0
        fi
        if [[ "$1" == "exec" ]]; then
          exit {exec_status}
        fi
        exit 1
        """
    )
    path = bin_dir / "docker"
    path.write_text(script)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _run_probe(tmp_path: Path, exec_status: int) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_path = tmp_path / "docker.log"
    _fake_docker(bin_dir, log_path, exec_status)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    script = textwrap.dedent(
        """\
        set -e
        source scripts/docker/health-check.sh
        failures=0
        _probe_manifest_row postgres postgres-local --postgres-local \
          "cmd:pg_isready -U rag -d rag_params_finder"
        """
    )
    return subprocess.run(
        ["bash", "-c", script],
        cwd=_REPO,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_given_cmd_probe_when_health_check_sourced_then_docker_exec_runs(tmp_path: Path) -> None:
    """
    Scenario: A store with a command health probe is checked.

    Given a stores.tsv-style cmd: probe and a present container,
    When the health-check probe function runs,
    Then docker exec receives that command.
    """
    ### Given / When
    completed = _run_probe(tmp_path, exec_status=0)
    log = (tmp_path / "docker.log").read_text()

    ### Then
    assert completed.returncode == 0, completed.stderr
    assert "OK   postgres cmd probe" in completed.stdout
    assert "exec rag-params-finder-postgres-local pg_isready -U rag -d rag_params_finder" in log


def test_given_cmd_probe_fails_when_health_check_sourced_then_hint_is_printed(
    tmp_path: Path,
) -> None:
    """
    Scenario: A failed command probe reports the failure and a hint.

    Given docker exec exits non-zero,
    When the probe function runs,
    Then the line is FAIL and the status hint is printed.
    """
    ### Given / When
    completed = _run_probe(tmp_path, exec_status=1)

    ### Then
    assert "FAIL postgres cmd probe" in completed.stdout
    assert "Hint: ./start-services.sh postgres status" in completed.stdout


def test_given_http_probe_down_when_elasticsearch_checked_then_remediation_is_printed(
    tmp_path: Path,
) -> None:
    """
    Scenario: ES unreachable is reported by the health-check probe.

    Given the Elasticsearch container is present and its HTTP probe fails,
    When the probe function runs,
    Then the result is FAIL and the status hint names elasticsearch.
    """
    ### Given
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _fake_docker(bin_dir, tmp_path / "docker.log", exec_status=0)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    script = textwrap.dedent(
        """\
        set -e
        source scripts/docker/health-check.sh
        failures=0
        _probe_manifest_row elasticsearch elasticsearch-local --elasticsearch-local \
          "http://127.0.0.1:9/_cluster/health"
        """
    )

    ### When
    completed = subprocess.run(
        ["bash", "-c", script],
        cwd=_REPO,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    ### Then
    assert "FAIL elasticsearch health probe" in completed.stdout
    assert "Hint: ./start-services.sh elasticsearch status" in completed.stdout


def test_given_manifest_when_down_flags_listed_then_every_local_profile_is_included() -> None:
    """
    Scenario: Teardown iterates all local profiles.

    Given the store manifest,
    When stop profile flags are listed,
    Then each registered local profile is present and stop-services.sh uses that list.
    """
    ### Given / When
    completed = subprocess.run(
        ["bash", "-c", "source scripts/lib/store_manifest.sh && store_down_profile_flags"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    stop_script = (_REPO / "stop-services.sh").read_text()

    ### Then
    flags = completed.stdout.split()
    assert flags == [
        "--profile",
        "mongodb-local",
        "--profile",
        "postgres-local",
        "--profile",
        "elasticsearch-local",
    ]
    assert "store_down_profile_flags" in stop_script
