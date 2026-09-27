"""Anti test-theater guard: no assertions on removed StorageBackend chunk methods.

Author: Claude (Crafter)
Created: 2026-09-27
Scope: SLICE-49B "Test infrastructure" — AST-scans every test file under
``tests/`` (excluding ``tests/server/db/`` and ``tests/contract/``, the two
directories that legitimately exercise the concrete Mongo/Postgres adapter
methods) for any mock-expectation assertion (``assert_called*`` /
``.call_count`` / ``.return_value = ...`` / ``.side_effect = ...``) targeting
``insert_chunks`` or ``delete_chunks_for_experiment``. Both methods were
removed from the ``StorageBackend`` Protocol in Slice 49B — chunk writes and
deletes now route through ``get_vector_store()`` exclusively. A surviving
expectation on either method, outside the two allowed adapter-test
directories, would mean a test still polices the pre-49B (defective)
chunk-routing behaviour this slice fixed: Testing Theater, not coverage.

This is a plain pytest test (not a hook/plugin), so it runs in PR CI with
everything else, per SLICE-49B-VECTOR-STORE-DATA-PATH-REWIRE.md line 127.
"""

from __future__ import annotations

import ast
from pathlib import Path

_TARGET_METHODS = {"insert_chunks", "delete_chunks_for_experiment"}
_ALLOWED_DIR_PARTS: tuple[tuple[str, ...], ...] = (
    ("tests", "server", "db"),
    ("tests", "contract"),
)
# The 49A/49B characterization golden-record suite (SLICE-49B "Test files by
# kind" — "49A golden records, replayed") pins the *concrete* Mongo/Postgres
# adapter's insert_chunks/delete_chunks_for_experiment pass-through contract
# via get_storage_backend() directly — the same legitimate adapter-level
# concern as tests/server/db/, just not physically nested under it. It is
# allow-listed by file, not by a broader directory rule, to keep the blast
# radius of this exception to exactly the one file the slice spec names.
_ALLOWED_FILE_PARTS: tuple[tuple[str, ...], ...] = (
    ("tests", "server", "test_vector_store_characterization.py"),
)
_ASSERT_CALLED_PREFIX = "assert_called"

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TESTS_ROOT = _REPO_ROOT / "tests"


def _is_allowed_path(relative_path: Path) -> bool:
    """True if ``relative_path`` is an adapter-level test dir or allow-listed file."""
    parts = relative_path.parts
    if any(parts[: len(allowed)] == allowed for allowed in _ALLOWED_DIR_PARTS):
        return True
    return parts in _ALLOWED_FILE_PARTS


def _dotted_chain(node: ast.AST) -> list[str]:
    """Flatten a (possibly-called) attribute chain into an ordered name list.

    ``a.b.c()`` parses to ``Call(func=Attribute(attr="c", value=Attribute(
    attr="b", value=Name(id="a"))))``; walking ``.value``/``.func`` down to
    the root ``Name`` and reversing yields ``["a", "b", "c"]``. Stops at the
    first node that is not a ``Name``/``Attribute``/``Call``.
    """
    names: list[str] = []
    current = node
    while True:
        if isinstance(current, ast.Attribute):
            names.append(current.attr)
            current = current.value
        elif isinstance(current, ast.Call):
            current = current.func
        elif isinstance(current, ast.Name):
            names.append(current.id)
            break
        else:
            break
    return list(reversed(names))


def _find_theater_violations(source: str, relative_path: Path) -> list[str]:
    """Return one message per mock-expectation on a removed chunk method."""
    tree = ast.parse(source, filename=str(relative_path))
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            chain = _dotted_chain(node.func)
            if (
                chain
                and chain[-1].startswith(_ASSERT_CALLED_PREFIX)
                and _TARGET_METHODS & set(chain[:-1])
            ):
                violations.append(
                    f"{relative_path}:{node.lineno}: {'.'.join(chain)}(...) — "
                    "mock expectation on a removed StorageBackend chunk method"
                )
        elif isinstance(node, ast.Attribute) and node.attr == "call_count":
            chain = _dotted_chain(node)
            if _TARGET_METHODS & set(chain[:-1]):
                violations.append(
                    f"{relative_path}:{node.lineno}: {'.'.join(chain)} — "
                    "call_count assertion on a removed StorageBackend chunk method"
                )
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr in (
                    "return_value",
                    "side_effect",
                ):
                    chain = _dotted_chain(target)
                    if _TARGET_METHODS & set(chain[:-1]):
                        violations.append(
                            f"{relative_path}:{node.lineno}: {'.'.join(chain)} = ... — "
                            f"{target.attr} stubbed on a removed StorageBackend chunk method"
                        )

    return violations


def _candidate_test_files() -> list[Path]:
    """Every ``tests/**/*.py`` file outside the allowed adapter directories."""
    return [
        path
        for path in sorted(_TESTS_ROOT.rglob("*.py"))
        if "__pycache__" not in path.parts and not _is_allowed_path(path.relative_to(_REPO_ROOT))
    ]


def test_no_test_asserts_chunk_calls_on_the_run_state_mock() -> None:
    """
    Scenario: No test asserts chunk calls on the run-state mock
    Slice: 49B — anti test-theater guard (SLICE-49B-VECTOR-STORE-DATA-PATH-REWIRE.md)

    Given the test suite (excluding tests/server/db/ and tests/contract/,
        which legitimately exercise the concrete adapter methods)
    When the anti test-theater guard AST-scans every remaining test file
    Then no test sets insert_chunks / delete_chunks_for_experiment
        expectations (assert_called* / call_count / return_value /
        side_effect) on a StorageBackend mock — a survivor would mean the
        Slice 49B chunk data-path migration missed a call site.
    """
    ### Given
    files = _candidate_test_files()
    assert files, "expected to scan at least one test file under tests/"

    ### When
    all_violations: list[str] = []
    for path in files:
        source = path.read_text()
        all_violations.extend(_find_theater_violations(source, path.relative_to(_REPO_ROOT)))

    ### Then
    assert not all_violations, "Test-theater violations found:\n" + "\n".join(all_violations)
