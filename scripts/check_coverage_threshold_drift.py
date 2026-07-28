"""Compatibility shim — prefer scripts/ci/check_coverage_threshold_drift.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load() -> ModuleType:
    target = Path(__file__).resolve().parent / "ci" / "check_coverage_threshold_drift.py"
    spec = importlib.util.spec_from_file_location(
        "scripts.ci.check_coverage_threshold_drift",
        target,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load coverage threshold drift checker from {target}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_mod = _load()
drift_failures = _mod.drift_failures
load_pyproject_thresholds = _mod.load_pyproject_thresholds
load_vite_thresholds = _mod.load_vite_thresholds
main = _mod.main

__all__ = [
    "drift_failures",
    "load_pyproject_thresholds",
    "load_vite_thresholds",
    "main",
]

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
