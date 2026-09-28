"""
Tests for registry-driven setup-guide parity.

Author: swami
Created: 2026-09-27
Scope: required headings, config basename parity, operator-doc mentions
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from server.db.ports.registry import example_config_for, known_vector_stores
from tests.helpers.repo_paths import repo_root_from

_REPO = repo_root_from(Path(__file__))
_REQUIRED_SECTIONS: dict[str, re.Pattern[str]] = {
    "choose": re.compile(r"^## Choose your ", re.MULTILINE),
    "environment": re.compile(r"^## Environment variables", re.MULTILINE),
    "path_a": re.compile(r"^## Path A", re.MULTILINE),
    "path_b": re.compile(r"^## Path B", re.MULTILINE),
    "index_lifecycle": re.compile(r"^## (Index lifecycle|Schema)", re.MULTILINE),
    "before_sweep": re.compile(r"^## Before you run a sweep", re.MULTILINE),
    "smoke": re.compile(r"^## Run the (smoke )?sweep", re.MULTILINE),
    "switching": re.compile(r"^## Switching", re.MULTILINE),
    "sizing": re.compile(r"^## Sizing", re.MULTILINE),
    "troubleshooting": re.compile(r"^## (Troubleshooting|If something fails)", re.MULTILINE),
    "diagnostics": re.compile(r"^## Diagnostics cheat sheet", re.MULTILINE),
}
_PLACEHOLDER = re.compile(r"^\s*(TODO|TBD|Coming soon)\s*$", re.IGNORECASE)
_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _setup_guide(provider: str) -> Path:
    return _REPO / "docs" / "user-guide" / f"{provider}-setup.md"


def missing_sections(text: str) -> list[str]:
    """Return required section names whose heading is absent or empty."""
    missing: list[str] = []
    for name, pattern in _REQUIRED_SECTIONS.items():
        match = pattern.search(text)
        if match is None:
            missing.append(name)
            continue
        rest = text[match.end() :]
        next_heading = re.search(r"^## ", rest, re.MULTILINE)
        body = rest[: next_heading.start()] if next_heading else rest
        stripped = body.strip()
        if not stripped or _PLACEHOLDER.match(stripped):
            missing.append(name)
            continue
        has_prose = bool(re.search(r"\w{8,}", stripped))
        has_list = bool(re.search(r"^\s*[-|] ", stripped, re.MULTILINE))
        has_code = "```" in stripped
        if not (has_prose or has_list or has_code):
            missing.append(name)
    return missing


def _config_dir(provider: str) -> Path:
    example = example_config_for(provider)
    return _REPO / Path(example).parent


@pytest.mark.parametrize("provider", sorted(known_vector_stores()))
def test_given_registered_provider_when_docs_checked_then_parity_holds(provider: str) -> None:
    """
    Scenario: Docs-parity check passes for every registered store.
    Slice: 51

    Given a registered vector store,
    When its setup guide, config dir, and operator docs are checked,
    Then the required sections, basenames, and mentions are present.
    """
    ### Given
    guide = _setup_guide(provider)
    text = guide.read_text() if guide.is_file() else ""

    ### When
    missing = missing_sections(text)
    mongo_names = {path.name for path in (_REPO / "configs" / "mongodb").glob("*.yaml")}
    provider_names = {path.name for path in _config_dir(provider).glob("*.yaml")}

    ### Then
    assert guide.is_file(), f"missing setup guide {guide}"
    assert missing == [], f"{guide.name} missing or empty sections: {missing}"
    assert provider_names == mongo_names
    for mention_path in (
        _REPO / ".env.example",
        _REPO / "README.md",
        _REPO / "QUICKSTART.md",
        _REPO / "docs" / "README.md",
        _REPO / "docs" / "user-guide" / "troubleshooting.md",
        _REPO / "docs" / "user-guide" / "cli-reference.md",
    ):
        body = mention_path.read_text().casefold()
        assert provider.casefold() in body, f"{provider} not mentioned in {mention_path}"
    help_text = (_REPO / "start-services.sh").read_text()
    assert f"--{provider}-local" in help_text
    assert f"{provider} start|stop|reset|status" in help_text or f"{provider} start" in help_text
    assert "## Teardown" in (_REPO / "QUICKSTART.md").read_text()


def test_given_guide_missing_a_heading_when_checked_then_the_name_is_reported() -> None:
    """
    Scenario: Docs-parity check fails on a missing heading.
    Slice: 51

    Given a setup guide that omits Sizing,
    When the section check runs,
    Then the failure names that section.
    """
    ### Given
    incomplete = "## Choose your deployment\n\nA real paragraph about deployment.\n"

    ### When
    missing = missing_sections(incomplete)

    ### Then
    assert "sizing" in missing
    assert "choose" not in missing


def test_given_setup_guide_links_when_resolved_then_relative_targets_exist() -> None:
    """
    Scenario: Setup-guide relative links resolve.
    Slice: 51

    Given each registered setup guide,
    When its relative markdown links are resolved,
    Then each target file exists.
    """
    ### Given / When / Then
    for provider in sorted(known_vector_stores()):
        guide = _setup_guide(provider)
        for target in _LINK.findall(guide.read_text()):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            path = (guide.parent / target.split("#", 1)[0]).resolve()
            if target.startswith("#"):
                continue
            assert path.is_file(), f"{guide.name} link {target} -> {path}"
