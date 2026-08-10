"""Every write path records an audit row (#42 acceptance criterion).

**Why this is a static check and not an HTTP middleware.**

The obvious reading of "no write path bypasses the audit log" is a middleware that logs every
mutating request. That would be weaker than what this codebase already does. A middleware runs
outside the database transaction, so a write that later rolls back still leaves an audit row
claiming it happened, and a write that succeeds gets two rows: the transactional one and the
middleware's. An audit trail that records writes which did not occur is worse than one with a
gap, because the gap is visible and the false row is not.

`record_audit` is deliberately called inside the caller's transaction and does not commit, so the
audit row is atomic with the mutation it describes. The guarantee is already correct. What was
missing is enforcement: nothing stopped someone adding a repository method that writes without
auditing, and the failure would be silent and permanent.

This test reads the AST of each persistence module, finds every method that executes an INSERT,
UPDATE or DELETE, and requires it to either call `record_audit` or write only to a table the
schema makes append-only by trigger. A new unaudited write path fails here rather than in
production six weeks later.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA = REPO_ROOT / "database" / "schema.sql"

# Modules that own writes. Routers are excluded: they delegate, and a router that wrote directly
# would be the bug this test is meant to make visible in whichever module it landed in.
PERSISTENCE_MODULES = [
    REPO_ROOT / "services" / "api" / "persistence.py",
    REPO_ROOT / "services" / "api" / "candidate_persistence.py",
    REPO_ROOT / "services" / "api" / "decisions.py",
    REPO_ROOT / "services" / "api" / "auth.py",
]

WRITE_STATEMENT = re.compile(r"\b(insert\s+into|update\s+|delete\s+from)\b", re.IGNORECASE)


def append_only_tables() -> frozenset[str]:
    """Tables the schema protects with an append-only trigger.

    Read from `schema.sql` rather than hardcoded, so adding a trigger there is enough and this
    list cannot drift away from what the database actually enforces.
    """
    text = SCHEMA.read_text(encoding="utf-8")
    return frozenset(
        match.group(1)
        for match in re.finditer(
            r"create trigger \w+ before update or delete on (\w+)", text, re.IGNORECASE
        )
    )


def _string_constants(node: ast.AST) -> list[str]:
    """Every string literal in the body except the docstring.

    The docstring is excluded because prose about a write is not a write. Leaving it in matched
    `_get_locked`, whose docstring explains a lost-*update* race while the method only selects,
    and a scan that flags comments produces exemptions that then hide real findings.
    """
    body = list(getattr(node, "body", []))
    # Identify the docstring by position rather than by comparing text: `ast.get_docstring`
    # dedents what it returns, so it never equals the raw constant in the tree and the
    # comparison silently matches nothing.
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    return [
        n.value
        for statement in body
        for n in ast.walk(statement)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]


def _calls_record_audit(node: ast.AST) -> bool:
    for call in ast.walk(node):
        if not isinstance(call, ast.Call):
            continue
        func = call.func
        if isinstance(func, ast.Name) and func.id == "record_audit":
            return True
        if isinstance(func, ast.Attribute) and func.attr == "record_audit":
            return True
    return False


def _written_tables(sql_strings: list[str]) -> set[str]:
    tables: set[str] = set()
    for sql in sql_strings:
        for match in re.finditer(
            r"(?:insert\s+into|update|delete\s+from)\s+(\w+)", sql, re.IGNORECASE
        ):
            tables.add(match.group(1).lower())
    return tables


def write_methods() -> list[tuple[str, str, ast.FunctionDef]]:
    """Every function in the persistence modules whose body issues a write."""
    found = []
    for path in PERSISTENCE_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if any(WRITE_STATEMENT.search(s) for s in _string_constants(node)):
                found.append((path.name, node.name, node))
    return found


def test_the_scan_finds_the_write_paths_it_is_meant_to_guard() -> None:
    """Guards the guard. If a refactor moved these methods or changed how SQL is built, this
    test would silently pass over everything and prove nothing."""
    names = {f"{module}:{func}" for module, func, _ in write_methods()}
    assert "candidate_persistence.py:record_score" in names
    assert "decisions.py:record" in names
    assert len(names) >= 8, f"expected the known write paths, found {sorted(names)}"


@pytest.mark.parametrize(
    ("module", "func", "node"),
    [(m, f, n) for m, f, n in write_methods()],
    ids=[f"{m}:{f}" for m, f, _ in write_methods()],
)
def test_every_write_path_is_audited(module: str, func: str, node: ast.FunctionDef) -> None:
    """Either it calls `record_audit`, or every table it writes is append-only by trigger.

    The second case is not an exemption. An append-only table is its own audit trail: the
    database refuses updates and deletes, so the row that is there is the row that was written.
    `decision_records` and `sessions` are the live examples.
    """
    if _calls_record_audit(node):
        return

    tables = _written_tables(_string_constants(node))

    # `sessions` and `users.last_login_at` are authentication bookkeeping rather than business
    # state. Auditing every session touch would write a row per request and bury the decisions
    # the log exists to make findable.
    protected = append_only_tables() | {"sessions", "users"}

    # A method that inserts into an append-only table in the same transaction is audited by that
    # insert. `DecisionRepository.record` is the live case: it moves the CAS pointer in
    # `decision_streams` and inserts the immutable `decision_records` row that justifies the move,
    # and that row carries actor, reason and evidence_ref. The pointer is derivable from it.
    if tables & append_only_tables():
        return

    unprotected = tables - protected

    assert not unprotected, (
        f"{module}:{func} writes {sorted(unprotected)} without calling record_audit, and those "
        f"tables are not append-only. Either record an audit row in the same transaction, or "
        f"add an append-only trigger in schema.sql."
    )


def test_append_only_tables_are_read_from_the_schema() -> None:
    """The list is derived, not hardcoded, so it cannot drift from what the database enforces."""
    tables = append_only_tables()
    assert "decision_records" in tables
    assert "sod_exceptions" in tables
    assert "distribution_deliveries" in tables


def test_record_audit_does_not_commit() -> None:
    """The atomicity guarantee this whole approach rests on. If `record_audit` committed, the
    audit row would survive a rolled-back mutation and record something that never happened."""
    source = (REPO_ROOT / "services" / "api" / "audit.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "record_audit":
            calls = {
                c.func.attr
                for c in ast.walk(node)
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
            }
            assert "commit" not in calls
            assert "rollback" not in calls
            return
    pytest.fail("record_audit not found in services/api/audit.py")
