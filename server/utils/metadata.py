"""Collect experiment metadata: git info, runtime versions, and non-sensitive env params."""

import importlib.metadata as _importlib_metadata
import os
import subprocess
import sys
from functools import lru_cache

from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

_SENSITIVE_FIELDS = frozenset({"voyage_api_key", "mongodb_uri", "sie_api_key"})


def _run_git(*args: str) -> str:
    """Run a git command and return stripped stdout, or 'unknown' on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


@lru_cache(maxsize=1)
def get_git_commit() -> str:
    if commit := os.environ.get("GIT_COMMIT", "").strip():
        return commit
    return _run_git("rev-parse", "--short", "HEAD")


@lru_cache(maxsize=1)
def get_git_branch() -> str:
    if branch := os.environ.get("GIT_BRANCH", "").strip():
        return branch
    return _run_git("rev-parse", "--abbrev-ref", "HEAD")


@lru_cache(maxsize=1)
def get_git_dirty() -> bool:
    """True if the working tree has uncommitted changes."""
    return _run_git("status", "--porcelain") != ""


@lru_cache(maxsize=1)
def get_python_version() -> str:
    v = sys.version_info
    return f"{v.major}.{v.minor}.{v.micro}"


@lru_cache(maxsize=1)
def get_app_version() -> str:
    try:
        return _importlib_metadata.version("rag-params-finder")
    except _importlib_metadata.PackageNotFoundError:
        return "dev"


def get_env_params() -> dict:
    """Return non-sensitive settings from the environment/.env file."""
    return {
        k: v
        for k, v in {
            "server_url": settings.server_url,
            "voyage_rpm_limit": settings.voyage_rpm_limit,
            "voyage_tpm_limit": settings.voyage_tpm_limit,
            "recover_on_boot": settings.recover_on_boot,
        }.items()
        if k not in _SENSITIVE_FIELDS
    }


def collect_experiment_metadata() -> dict:
    """Build the full metadata dict to embed in an experiment document."""
    metadata = {
        "git_commit": get_git_commit(),
        "git_branch": get_git_branch(),
        "git_dirty": get_git_dirty(),
        "python_version": get_python_version(),
        "app_version": get_app_version(),
        "env_params": get_env_params(),
    }
    logger.debug("metadata snapshot — git_commit=%s", metadata["git_commit"])
    return metadata
