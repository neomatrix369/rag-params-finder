"""AST guard — no store-string branching outside the adapters/registry/settings/config.

Author: Slice 49A Stream 6
Created: 2026-09-27
Scope: server/ + cli/ — every comparison of a known vector-store/backend name
    literal (``==``, ``!=``, ``in``, ``not in``, and ``match``/``case``
    patterns) must live inside one of the allow-listed modules; everywhere
    else, the decision must be routed through
    ``server.db.ports.registry.resolve_adapter`` (or an equivalent capability
    lookup) instead of comparing strings.

Supersedes the throwaway ``/tmp`` grep-based sweep recorded in
``docs/plan/gate-evidence/slice-49a-store-string-inventory.md`` (Stream 1's
23-site baseline) — that script used a plain ``grep '== *"…"'`` which the
spec calls out as missing ``!=``, set membership, and match/case forms, plus
the whole ``cli/`` package. This test parses real ASTs so all of those forms
are caught.

GWT (docs/plan/slices/05-storage/SLICE-49-VECTOR-STORE-PORT-SPLIT-REGISTRY.md):

    Scenario: No store-string branching outside the adapters/registry/settings
      Given server/ and cli/
      When the AST guard runs
      Then no ==, !=, in-set or match comparison against a store name exists
        outside adapter modules, registry.py, settings.py and config.py

PBT/parametrize handoff note (spec, "nw-distill" pointer): the natural
parametrize axis is "comparison form" (``==``, ``!=``, ``in``, ``not in``,
``match``/``case``). A single comprehensive AST walk covers all forms in one
pass; violations are still collected and reported individually (file:line +
the exact offending comparison) so a failure is attributable per form/site,
which is what parametrizing over forms would buy without the fixture
duplication a full parametrize split would need here.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# The canonical set of store-name literals in active use across the codebase —
# read from server/settings.py's _KNOWN_STORAGE_BACKENDS / _KNOWN_VECTOR_STORE_BACKENDS
# and server/models/config.py's normalize_database_provider aliasing, so this
# guard neither misses a real store name nor over-flags unrelated strings.
#   - "mongodb", "mongo"      (server/settings.py _STORAGE_BACKEND_ALIASES)
#   - "postgres"              (server/settings.py _KNOWN_STORAGE_BACKENDS)
#   - "postgresql"            (defensive alias — some drivers/URIs spell it out)
#   - "supabase"              (server/models/config.py normalize_database_provider)
#   - "elasticsearch"         (server/settings.py _KNOWN_VECTOR_STORE_BACKENDS, Slice 50)
_STORE_NAME_LITERALS: frozenset[str] = frozenset(
    {"mongodb", "mongo", "postgres", "postgresql", "supabase", "elasticsearch"}
)

# Files where comparing against a store-name literal is the module's own job:
# the composite VectorStore adapters, the single-engine StorageBackend/Retriever
# implementations, the registry (the SSOT for store selection — its lookup
# table literally is these names), and the settings/config normalisers that
# own alias mapping and validation for these exact values.
_ALLOWED_RELATIVE_PATHS: frozenset[str] = frozenset(
    {
        # Composite VectorStore adapters (spec: "Composite adapters, not the
        # run-state classes" — Output contract).
        "server/db/mongo/mongo_vector_store.py",
        "server/db/postgres/postgres_vector_store.py",
        # Single-engine StorageBackend/RetrieverBackend implementations — each
        # file only ever talks about its own engine, so a literal here is an
        # identity constant, not cross-engine routing (spec's "adapters").
        "server/db/mongo/mongo_store.py",
        "server/db/postgres/postgres_store.py",
        # The registry — the SSOT table mapping provider name -> adapter class.
        "server/db/ports/registry.py",
        # Settings — owns STORAGE_BACKEND / VECTOR_STORE_BACKEND validation,
        # normalisation, and the known-backend sets themselves.
        "server/settings.py",
        # Config — owns the DatabaseProvider Literal and its normaliser
        # (normalize_database_provider, normalize_stats_database_provider).
        "server/models/config.py",
        # Factory — spec's Output contract explicitly keeps get_storage_backend()
        # "reading STORAGE_BACKEND directly" (unchanged from pre-49A); this is
        # the run-state StorageBackend's own routing primitive, the mirror of
        # registry.py for VectorStore selection. Reuse ledger keeps its
        # if/elif out of the 49A registry migration by design, not oversight.
        "server/db/ports/store_factory.py",
    }
)

# Deprecated shim re-exporting server.db.ports.stats_common for backward
# compatibility (server/db/stats_common.py) — contains no comparisons of its
# own; excluded from the walk entirely below rather than allow-listed, since
# it is a pure re-export with zero AST nodes worth inspecting for this guard.


@dataclass(frozen=True)
class Violation:
    path: str
    lineno: int
    detail: str

    def __str__(self) -> str:  # pragma: no cover - formatting only
        return f"{self.path}:{self.lineno}: {self.detail}"


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for base in ("server", "cli"):
        base_dir = REPO_ROOT / base
        if not base_dir.is_dir():
            continue
        files.extend(sorted(base_dir.rglob("*.py")))
    return files


def _is_store_literal(node: ast.expr) -> str | None:
    """Return the lowercased literal value when ``node`` is a store-name string."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        lowered = node.value.strip().lower()
        if lowered in _STORE_NAME_LITERALS:
            return lowered
    return None


def _literal_set_members(node: ast.expr) -> list[str]:
    """Store-name literals found inside a set/tuple/list/dict-keys container."""
    elements: list[ast.expr] = []
    if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        elements = list(node.elts)
    elif isinstance(node, ast.Dict):
        elements = [k for k in node.keys if k is not None]
    found = []
    for element in elements:
        literal = _is_store_literal(element)
        if literal is not None:
            found.append(literal)
    return found


def _describe_compare(node: ast.Compare) -> str | None:
    """Describe a Compare node's offending store-literal form, or None."""
    operands = [node.left, *node.comparators]
    ops = node.ops

    for op, left, right in zip(ops, operands, operands[1:]):
        if isinstance(op, (ast.Eq, ast.NotEq)):
            op_str = "==" if isinstance(op, ast.Eq) else "!="
            left_lit = _is_store_literal(left)
            right_lit = _is_store_literal(right)
            if left_lit or right_lit:
                return f"{op_str} comparison against store literal {left_lit or right_lit!r}"
        elif isinstance(op, (ast.In, ast.NotIn)):
            op_str = "in" if isinstance(op, ast.In) else "not in"
            members = _literal_set_members(right)
            single = _is_store_literal(right)
            if members:
                return f"{op_str} comparison against store-literal set {sorted(members)!r}"
            if single:
                return f"{op_str} comparison against store literal {single!r}"
    return None


def _describe_match_case(node: ast.match_case) -> str | None:
    """Describe a match-case pattern matching a store-name literal, or None."""
    pattern = node.pattern
    if isinstance(pattern, ast.MatchValue):
        literal = _is_store_literal(pattern.value)
        if literal is not None:
            return f"match case against store literal {literal!r}"
    if isinstance(pattern, ast.MatchOr):
        for sub in pattern.patterns:
            if isinstance(sub, ast.MatchValue):
                literal = _is_store_literal(sub.value)
                if literal is not None:
                    return f"match case (or-pattern) against store literal {literal!r}"
    return None


def _find_violations(tree: ast.AST, relative_path: str) -> list[Violation]:
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            detail = _describe_compare(node)
            if detail:
                violations.append(Violation(relative_path, node.lineno, detail))
        elif isinstance(node, ast.match_case):
            detail = _describe_match_case(node)
            if detail:
                violations.append(Violation(relative_path, node.lineno, detail))
    return violations


def _collect_all_violations() -> list[Violation]:
    all_violations: list[Violation] = []
    for path in _iter_python_files():
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        if relative_path in _ALLOWED_RELATIVE_PATHS:
            continue
        source = path.read_text()
        tree = ast.parse(source, filename=relative_path)
        all_violations.extend(_find_violations(tree, relative_path))
    return all_violations


class TestNoStoreStringBranchingOutsideAllowedModules:
    """AST guard: store-name literal comparisons stay inside the allowed modules."""

    def test_given_server_and_cli_when_ast_walked_then_no_violations_outside_allowlist(
        self,
    ) -> None:
        """
        Scenario: No store-string branching outside the adapters/registry/settings/config.
        Slice: 49A Stream 6 — hardened AST guard (supersedes grep-based Stream 1 inventory)

        Given every ``.py`` file under server/ and cli/,
        When each file's AST is walked for ==, !=, in, not in, and match/case
            comparisons against a known store-name literal,
        Then every match is inside one of the explicitly allow-listed modules
            (composite adapters, registry.py, settings.py, config.py, and the
            store_factory.py run-state routing module) — no relocatable
            store-string branching escapes the port/registry seam.
        """
        ### Given
        # (files discovered by _iter_python_files; allow-list defined above)

        ### When
        violations = _collect_all_violations()

        ### Then
        assert violations == [], (
            "Found store-name literal comparisons outside the allow-listed "
            "modules (adapters, registry.py, settings.py, config.py, "
            "store_factory.py). Route the decision through "
            "server.db.ports.registry.resolve_adapter() (or a capability on "
            "the resolved VectorStore) instead:\n" + "\n".join(f"  - {v}" for v in violations)
        )

    def test_given_known_allowed_files_when_ast_walked_then_each_carries_a_real_hit(
        self,
    ) -> None:
        """
        Scenario: Allow-list entries are load-bearing, not decorative.
        Slice: 49A Stream 6 — guards the guard itself

        Given the allow-listed modules that are expected to legitimately
            branch on a store-name literal (settings.py, config.py,
            store_factory.py — the ones with genuine ``==``/``!=``/``in``
            store-literal comparisons today),
        When the same AST walk runs over just those files,
        Then each reports at least one hit — proving the allow-list isn't
            silently exempting files that no longer need the exemption.
        """
        ### Given
        files_expected_to_have_hits = (
            "server/settings.py",
            "server/models/config.py",
            "server/db/ports/store_factory.py",
        )

        ### When / Then
        for relative_path in files_expected_to_have_hits:
            path = REPO_ROOT / relative_path
            tree = ast.parse(path.read_text(), filename=relative_path)
            violations = _find_violations(tree, relative_path)
            assert violations, (
                f"{relative_path} is allow-listed but has zero store-literal "
                "comparisons — remove it from the allow-list if it no longer "
                "needs the exemption."
            )
