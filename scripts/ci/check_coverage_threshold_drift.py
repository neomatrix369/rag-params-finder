#!/usr/bin/env python3
"""Assert FE Vitest floors stay aligned with pyproject thresholds (Slice 45 Could).

Compares ``frontend/vite.config.ts`` ``coverage.thresholds`` with
``[tool.rag_params_finder.coverage_thresholds]`` in ``pyproject.toml``.

Shared metrics (statements / branches / lines) must match. Vitest also
enforces ``functions``; that key is FE-only (coverage.py does not measure
functions) and is checked when present in pyproject.

Usage:
  python scripts/ci/check_coverage_threshold_drift.py
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
VITE_CONFIG = ROOT / "frontend" / "vite.config.ts"

SHARED_KEYS = ("statements", "branches", "lines")
FE_ONLY_KEYS = ("functions",)


def load_pyproject_thresholds(path: Path = PYPROJECT) -> dict[str, float]:
    """Load coverage floors from ``[tool.rag_params_finder.coverage_thresholds]``."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    section = data.get("tool", {}).get("rag_params_finder", {}).get("coverage_thresholds", {})
    return {str(k): float(v) for k, v in section.items()}


def load_vite_thresholds(path: Path = VITE_CONFIG) -> dict[str, float]:
    """Parse numeric thresholds from the Vitest coverage block in vite.config.ts."""
    text = path.read_text(encoding="utf-8")
    block = re.search(
        r"thresholds\s*:\s*\{([^}]+)\}",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if block is None:
        raise ValueError(f"no coverage.thresholds object found in {path}")
    found = {
        key: float(value)
        for key, value in re.findall(
            r"(statements|branches|functions|lines)\s*:\s*(\d+(?:\.\d+)?)",
            block.group(1),
        )
    }
    if not found:
        raise ValueError(f"empty coverage.thresholds object in {path}")
    return found


def drift_failures(
    pyproject: dict[str, float],
    vite: dict[str, float],
) -> list[str]:
    """Return human-readable drift lines (empty when aligned)."""
    failures: list[str] = []
    for key in SHARED_KEYS:
        if key not in pyproject:
            failures.append(f"pyproject missing shared key: {key}")
            continue
        if key not in vite:
            failures.append(f"vite.config.ts missing shared key: {key}")
            continue
        if pyproject[key] != vite[key]:
            failures.append(f"{key}: pyproject={pyproject[key]} vite={vite[key]}")
    for key in FE_ONLY_KEYS:
        if key in pyproject and key in vite and pyproject[key] != vite[key]:
            failures.append(f"{key}: pyproject={pyproject[key]} vite={vite[key]}")
        elif key in vite and key not in pyproject:
            failures.append(f"pyproject missing FE-only key documented in vite: {key}")
    return failures


def main(argv: list[str] | None = None) -> int:
    """CLI entry — exit 1 on drift."""
    del argv  # unused; keeps signature testable
    try:
        pyproject = load_pyproject_thresholds()
        vite = load_vite_thresholds()
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"coverage threshold drift: failed to load configs: {exc}", file=sys.stderr)
        return 1
    failures = drift_failures(pyproject, vite)
    if failures:
        print(
            "coverage threshold drift detected (DECISIONS #142 / Slice 45 Could):",
            file=sys.stderr,
        )
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        print(
            "Align frontend/vite.config.ts thresholds with "
            "[tool.rag_params_finder.coverage_thresholds] in pyproject.toml "
            "(Decision Log row required to change floors).",
            file=sys.stderr,
        )
        return 1
    shared = ", ".join(f"{k}={vite[k]:g}" for k in SHARED_KEYS)
    functions = vite.get("functions")
    extra = f" functions={functions:g}" if functions is not None else ""
    print(f"coverage threshold drift: OK ({shared}{extra})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
