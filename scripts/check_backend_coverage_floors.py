"""Compatibility shim — prefer scripts/ci/check_backend_coverage_floors.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load() -> ModuleType:
    target = Path(__file__).resolve().parent / "ci" / "check_backend_coverage_floors.py"
    spec = importlib.util.spec_from_file_location(
        "scripts.ci.check_backend_coverage_floors",
        target,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load coverage floors checker from {target}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_mod = _load()
evaluate = _mod.evaluate
metrics_from_totals = _mod.metrics_from_totals
main = _mod.main

__all__ = ["evaluate", "main", "metrics_from_totals"]

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
