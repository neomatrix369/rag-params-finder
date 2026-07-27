"""Repository root discovery for mirrored test modules."""

from __future__ import annotations

from pathlib import Path


def repo_root_from(path: Path) -> Path:
    """Walk parents of ``path`` until ``pyproject.toml`` is found."""
    for parent in path.resolve().parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError(f"Could not locate repo root from {path}")
