"""Verifies the complexity PR-body summary parses both ESLint complexity rules.

Author: project-hygiene uplift
Created: 2026-09-24
Scope: scripts/ci/write_complexity_summary.py — eslint_violations, unit, pure function
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from tests.helpers.repo_paths import repo_root_from

_SCRIPT = repo_root_from(Path(__file__)) / "scripts" / "ci" / "write_complexity_summary.py"


def _load_summary_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("write_complexity_summary", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SUMMARY = _load_summary_module()

_ESLINT_REPORT = [
    {
        "filePath": "/repo/frontend/src/Detail.tsx",
        "messages": [
            {
                "ruleId": "complexity",
                "line": 46,
                "message": "Function 'Detail' has a complexity of 14. Maximum allowed is 10.",
            },
            {
                "ruleId": "sonarjs/cognitive-complexity",
                "line": 46,
                "message": "Refactor this function to reduce its Cognitive Complexity "
                "from 63 to the 15 allowed.",
            },
        ],
    },
    {
        "filePath": "/repo/frontend/src/labels.ts",
        "messages": [
            {
                "ruleId": "sonarjs/cognitive-complexity",
                "line": 35,
                "message": "Refactor this function to reduce its Cognitive Complexity "
                "from 25 to the 15 allowed.",
            },
        ],
    },
]


def test_cyclomatic_violations_ignore_cognitive_messages() -> None:
    """The default rule counts only cyclomatic complexity messages.

    Scenario: Cyclomatic summary is unchanged by the added cognitive rule.
    Slice: project-hygiene uplift — frontend cognitive complexity reporting

    Given an ESLint report with one cyclomatic and two cognitive messages
    When cyclomatic violations are extracted with the default rule
    Then only the cyclomatic violation is returned with its score
    """
    ### Given
    report = _ESLINT_REPORT

    ### When
    violations = _SUMMARY.eslint_violations(report)

    ### Then
    assert violations == [("/repo/frontend/src/Detail.tsx", 46, 14)]


def test_cognitive_violations_are_parsed_and_sorted_by_score() -> None:
    """The sonarjs rule yields cognitive scores, highest first.

    Scenario: Cognitive complexity violations appear in the PR summary.
    Slice: project-hygiene uplift — frontend cognitive complexity reporting

    Given an ESLint report with two cognitive-complexity messages (63 and 25)
    When cognitive violations are extracted with the sonarjs rule and message pattern
    Then both are returned with their scores, highest first
    """
    ### Given
    report = _ESLINT_REPORT

    ### When
    violations = _SUMMARY.eslint_violations(
        report, _SUMMARY.COGNITIVE_RULE, _SUMMARY.COGNITIVE_MESSAGE
    )

    ### Then
    assert violations == [
        ("/repo/frontend/src/Detail.tsx", 46, 63),
        ("/repo/frontend/src/labels.ts", 35, 25),
    ]
