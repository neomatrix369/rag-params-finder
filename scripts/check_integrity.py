#!/usr/bin/env python3
"""Repository integrity check: unit tests, import smoke, optional full gates.

Adapted from price-analysis/scripts/check_integrity.py for rag-params-finder.

Usage:
  python scripts/check_integrity.py
  python scripts/check_integrity.py --full
  python scripts/check_integrity.py --history 10
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], *, env: dict | None = None) -> int:
    print(f"\n{'─' * 72}\n$ {' '.join(cmd)}\n{'─' * 72}")
    result = subprocess.run(cmd, cwd=ROOT, env=env or os.environ.copy())
    return result.returncode


def check_unit_tests() -> int:
    """Fast regression: pytest on tests/ (excludes integration unless --full)."""
    return _run(
        [
            "uv",
            "run",
            "pytest",
            "tests/",
            "-q",
            "--tb=short",
            "-m",
            "not integration",
        ]
    )


def check_import_smoke() -> int:
    """Verify core package imports without starting the server."""
    return _run(["uv", "run", "python", "-c", _IMPORT_SMOKE_CODE])


_IMPORT_SMOKE_CODE = """
import sys

checks = [
    ("server.settings", lambda: __import__("server.settings")),
    ("server.models.config", lambda: __import__("server.models.config")),
    ("server.core.search_index_plan", lambda: __import__("server.core.search_index_plan")),
    ("cli.main", lambda: __import__("cli.main")),
]

failed = False
for label, fn in checks:
    try:
        fn()
        print(f"  OK   {label}")
    except Exception as exc:
        print(f"  FAIL {label}: {exc}")
        failed = True

sys.exit(1 if failed else 0)
"""


def check_quality_gates() -> int:
    """Run the unified quality-gates script (matches CI)."""
    script = ROOT / "scripts" / "quality-gates.sh"
    return _run(["bash", str(script)])


def check_precommit() -> int:
    return _run(["pre-commit", "run", "--all-files"])


def check_history(n: int) -> int:
    """Bisect last N commits: run unit tests at each."""
    log = subprocess.run(
        ["git", "log", "--oneline", f"-{n}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    shas = [line.split()[0] for line in log.stdout.strip().splitlines() if line.strip()]
    original = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    failures: list[str] = []
    for sha in shas:
        print(f"\n{'=' * 72}\nChecking commit {sha}\n{'=' * 72}")
        subprocess.run(["git", "checkout", sha], cwd=ROOT, check=True)
        if check_unit_tests() != 0:
            failures.append(sha)

    subprocess.run(["git", "checkout", original], cwd=ROOT, check=True)

    if failures:
        print(f"\n❌ Failed at commits: {', '.join(failures)}")
        return 1
    print(f"\n✅ All {len(shas)} commits passed unit tests.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Repository integrity check")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run quality-gates.sh --full + pre-commit",
    )
    parser.add_argument(
        "--history",
        type=int,
        metavar="N",
        help="Run unit tests on last N commits (bisect mode)",
    )
    args = parser.parse_args()

    if args.history:
        return check_history(args.history)

    steps: list[tuple[str, int]] = [
        ("unit tests", check_unit_tests()),
        ("import smoke", check_import_smoke()),
    ]

    if args.full:
        steps.append(("quality gates", check_quality_gates()))
        steps.append(("pre-commit", check_precommit()))

    failed = [name for name, code in steps if code != 0]
    if failed:
        print(f"\n❌ Integrity check failed: {', '.join(failed)}")
        return 1

    print("\n✅ Integrity check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
