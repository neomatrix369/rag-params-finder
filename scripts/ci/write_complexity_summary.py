"""Render Radon and ESLint complexity data as an anchored PR-body section."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

COMPLEXITY_MESSAGE = re.compile(r"complexity of (?P<score>\d+)", re.IGNORECASE)
MAX_ITEMS = 10


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as report:
        return json.load(report)


def python_summary(report: Mapping[str, Sequence[Mapping[str, Any]]]) -> tuple[int, str, int]:
    entries = [entry for values in report.values() for entry in values]
    if not entries:
        return 0, "A", 0
    highest = max(entries, key=lambda entry: int(entry["complexity"]))
    return int(highest["complexity"]), str(highest["rank"]), len(entries)


def eslint_violations(report: Iterable[Mapping[str, Any]]) -> list[tuple[str, int, int]]:
    violations: list[tuple[str, int, int]] = []
    for file_report in report:
        for message in file_report.get("messages", []):
            match = COMPLEXITY_MESSAGE.search(str(message.get("message", "")))
            if message.get("ruleId") == "complexity" and match:
                violations.append(
                    (
                        str(file_report["filePath"]),
                        int(message.get("line", 0)),
                        int(match.group("score")),
                    )
                )
    return sorted(violations, key=lambda item: item[2], reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python-report", type=Path, required=True)
    parser.add_argument("--node-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    score, rank, count = python_summary(read_json(args.python_report))
    violations = eslint_violations(read_json(args.node_report))
    lines = [
        "<!-- complexity-report:start -->",
        "## Complexity",
        "",
        "_Automatically refreshed by CI for product-code changes._",
        "",
        "| Scope | Tool | Result |",
        "| --- | --- | --- |",
        f"| Python | Radon | highest CC **{score}** (rank **{rank}**), {count} blocks |",
        f"| JS/TS | ESLint | {len(violations)} function(s) above CC 10 |",
        "",
        "<details><summary>Functions above the JavaScript threshold</summary>",
        "",
        *(
            [
                f"- `{Path(path).name}:{line}` — CC {value}"
                for path, line, value in violations[:MAX_ITEMS]
            ]
            or ["- None."]
        ),
        "",
        "</details>",
        "<!-- complexity-report:end -->",
        "",
    ]
    args.output.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
