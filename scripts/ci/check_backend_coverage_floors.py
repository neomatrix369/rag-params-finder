#!/usr/bin/env python3
"""Enforce BE coverage floors matching FE Vitest quartet (DECISIONS #142).

coverage.py only gates a single combined Cover via ``fail_under``. This script
reads the coverage JSON report and fails unless:

* statements ≥ 95
* branches ≥ 90
* lines ≥ 95  (statement coverage — same denominator as Vitest ``lines``)

Functions are not measured by coverage.py (FE still enforces functions ≥ 95).

Floors load from ``[tool.rag_params_finder.coverage_thresholds]`` in
``pyproject.toml`` when present; otherwise FE-matching defaults apply.

Usage:
  python scripts/ci/check_backend_coverage_floors.py [.reports/coverage-backend-unit.json]
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path
from typing import Any

DEFAULT_FLOORS: dict[str, float] = {
    "statements": 95.0,
    "branches": 90.0,
    "lines": 95.0,
}


def load_floors(pyproject: Path | None = None) -> dict[str, float]:
    """Load statement/branch/line floors from pyproject.toml when configured."""
    path = pyproject or Path("pyproject.toml")
    floors = dict(DEFAULT_FLOORS)
    if not path.is_file():
        return floors
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    section = data.get("tool", {}).get("rag_params_finder", {}).get("coverage_thresholds", {})
    for key in floors:
        if key in section:
            floors[key] = float(section[key])
    return floors


def _pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 100.0
    return 100.0 * numerator / denominator


def metrics_from_totals(totals: dict[str, Any]) -> dict[str, float]:
    """Derive statement / branch / line percentages from coverage.py totals."""
    stmts = float(totals.get("num_statements") or 0)
    missing = float(totals.get("missing_lines") or 0)
    covered_stmts = stmts - missing if stmts else float(totals.get("covered_lines") or 0)

    branches = float(totals.get("num_branches") or 0)
    covered_branches = float(totals.get("covered_branches") or 0)

    stmt_pct = _pct(covered_stmts, stmts) if stmts else 100.0
    branch_pct = _pct(covered_branches, branches) if branches else 100.0
    line_pct = stmt_pct

    return {
        "statements": stmt_pct,
        "branches": branch_pct,
        "lines": line_pct,
    }


def evaluate(
    totals: dict[str, Any],
    floors: dict[str, float] | None = None,
) -> list[str]:
    """Return human-readable failure lines (empty when all floors pass)."""
    active = floors if floors is not None else DEFAULT_FLOORS
    measured = metrics_from_totals(totals)
    failures: list[str] = []
    for key, floor in active.items():
        value = measured[key]
        if value + 1e-9 < floor:
            failures.append(f"{key}: {value:.2f}% < floor {floor:.0f}%")
    return failures


def main(argv: list[str]) -> int:
    report = Path(argv[1] if len(argv) > 1 else ".reports/coverage-backend-unit.json")
    if not report.is_file():
        print(f"ERROR: coverage JSON not found: {report}", file=sys.stderr)
        return 2

    payload = json.loads(report.read_text(encoding="utf-8"))
    totals = payload.get("totals")
    if not isinstance(totals, dict):
        print("ERROR: coverage JSON missing totals object", file=sys.stderr)
        return 2

    floors = load_floors()
    measured = metrics_from_totals(totals)
    print(
        "Backend coverage floors (match FE 95/90/95; functions n/a): "
        f"statements={measured['statements']:.2f}% "
        f"(floor {floors['statements']:.0f}) "
        f"branches={measured['branches']:.2f}% "
        f"(floor {floors['branches']:.0f}) "
        f"lines={measured['lines']:.2f}% "
        f"(floor {floors['lines']:.0f})"
    )
    failures = evaluate(totals, floors)
    if failures:
        print("FAIL — below shared product floors:", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1

    print("PASS — statements/branches/lines meet 95/90/95")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
