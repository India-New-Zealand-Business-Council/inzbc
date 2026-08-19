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

# Files this scan deliberately does not read, each for a reason that is about the file rather
# than about convenience. Everything else under `services/api/` is scanned, whether or not anyone
# remembered to add it.
NOT_SCANNED = frozenset(
    {
        # The FastAPI app itself: it mounts routers and declares response models, and any write
        # in here would be the bug, caught by the scan of the module it belongs in.
        "main.py",
        # Emits audit rows; it is the mechanism, not a caller of it.
        "audit.py",
        # No database access at all.
        "hardening.py",
        "model_gateway.py",
        "redaction.py",
    }
)


def persistence_modules() -> list[Path]:
    """Every module under `services/api/` that this scan should read.

    **Discovered, not listed.** This was a hand-written list of four files, and `source_checks.py`
    was not one of them - so the scanner never looked at it, reported success, and an unaudited
    upsert on the register an auditor checks a run against shipped behind a green check. Found in
    review of #264 by adding the file to the list by hand, which is exactly the step that cannot
    be relied on.

    That is the fourth hand-written list in this repository to quietly stop covering what it
    names (the whole-table guards missed a table, the route matrix missed a route,
    `VERIFICATION_STATES` drifted from the schema enum). The common shape is a conformance test
    being *told* its subjects instead of finding them, which makes forgetting silent and makes
    the test's green pass mean less the longer it runs. So this globs, and a new router or
    repository is covered the day it lands.

    Exclusions are explicit in `NOT_SCANNED` and each has to justify itself, which is the
    difference between an exemption and an omission: an omission is invisible.
    """
    return sorted(
        path
        for path in (REPO_ROOT / "services" / "api").glob("*.py")
        if not path.name.startswith("_") and path.name not in NOT_SCANNED
    )
# Modules that own writes. Routers are excluded: they delegate, and a router that wrote directly
# would be the bug this test is meant to make visible in whichever module it landed in.
PERSISTENCE_MODULES = [
    REPO_ROOT / "services" / "api" / "persistence.py",
    REPO_ROOT / "services" / "api" / "candidate_persistence.py",
    REPO_ROOT / "services" / "api" / "decisions.py",
    REPO_ROOT / "services" / "api" / "auth.py",
    # #188: this hand-written list already missed one write path once (PR #264's
    # source_checks.py gap) precisely because a new module can land without anyone remembering to
    # add it here. Adding this explicitly rather than leaving it out silently, same failure mode,
    # until #264's glob-based rewrite of this scanner lands on main and this branch rebases onto
    # it.
    REPO_ROOT / "services" / "api" / "facts_persistence.py",
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
    for path in persistence_modules():
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
    # The path the hand-written module list missed. Named explicitly so that if the glob ever
    # stops reaching it, this fails rather than the parametrised test quietly shrinking.
    assert "source_checks.py:record" in names
    assert len(names) >= 8, f"expected the known write paths, found {sorted(names)}"


def test_the_scan_reads_every_module_it_is_not_explicitly_excused() -> None:
    """The exclusion list must stay a list of decisions, not a place things drift into.

    A file added to `services/api/` is scanned by default. If it should not be, it goes in
    `NOT_SCANNED` with a reason - and this asserts that every name in there still exists, so a
    renamed or deleted module cannot leave a stale exemption behind that silently excuses a
    future file of the same name.
    """
    api_dir = REPO_ROOT / "services" / "api"
    for name in NOT_SCANNED:
        assert (api_dir / name).exists(), (
            f"{name} is excused from the audit scan but no longer exists - remove it from "
            f"NOT_SCANNED so the exemption cannot be inherited by a future file of that name."
        )

    scanned = {path.name for path in persistence_modules()}
    assert "source_library.py" in scanned, (
        "read-only modules are scanned too - that is what proves they stay read-only"
    )


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

    # Narrow, named exemptions. An earlier version returned as soon as *any* written table was
    # append-only, which an adversarial review correctly called a bypass: a method could insert
    # into `decision_records` and update any mutable table it liked in the same breath, and the
    # non-empty intersection let the whole method through unchecked. Each exemption below names
    # the exact set it covers, so a method that writes anything else still has to be audited.
    exact_exemptions = {
        # `DecisionRepository.record` moves the CAS pointer in `decision_streams` and inserts the
        # immutable `decision_records` row that justifies the move. That row carries actor,
        # reason and evidence_ref, and the pointer is derivable from it.
        frozenset({"decision_records", "decision_streams"}),
        # Session issue, refresh and sign-out. Authentication bookkeeping, not business state:
        # auditing every session touch writes a row per request and buries the decisions the log
        # exists to make findable. `users` appears here only for `last_login_at`.
        frozenset({"sessions"}),
        frozenset({"sessions", "users"}),
    }
    if frozenset(tables) in exact_exemptions:
        return

    unprotected = tables - append_only_tables()

    assert not unprotected, (
        f"{module}:{func} writes {sorted(unprotected)} without calling record_audit, and those "
        f"tables are neither append-only nor covered by a named exemption. Either record an "
        f"audit row in the same transaction, add an append-only trigger in schema.sql, or add an "
        f"exact exemption here naming the full set of tables the method writes."
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
