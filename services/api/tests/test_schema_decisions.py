"""Source-shape checks on the ADR-0005 decision tables in database/schema.sql.

This parses SQL text. It does not run Postgres, so it cannot prove the DDL applies or that any
constraint fires; the constraint behaviour was verified against Postgres 16 by hand and belongs in
an integration test once CI has a database (ADR-0005 required follow-up 6). What it does catch is
the vocabulary drifting away from the accepted ADR, and the superseded shape coming back.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "database" / "schema.sql"

DECISION_KINDS = ["CEO Ruling", "Report Approval", "Distribution Authority"]

# The union of every value the three streams may carry. Which kind may carry which is a CHECK
# constraint, not something this text-level test can see.
DECISION_VALUES = [
    "Continue",
    "Continue With Correction",
    "Pause",
    "Stop",
    "Approved",
    "Rejected",
    "Returned for Correction",
    "Authorised",
    "Not Authorised",
]

DECISION_TABLES = [
    "user_roles",
    "decision_role_permissions",
    "decision_sod_role_pairs",
    "distribution_configuration",
    "report_versions",
    "decision_streams",
    "sod_exceptions",
    "decision_records",
    "distribution_deliveries",
]


def _schema() -> str:
    return SCHEMA_PATH.read_text(encoding="utf-8")


def _enum_values(sql_text: str, type_name: str) -> list[str]:
    match = re.search(
        rf"create type {type_name}\s+as enum\s*\((.*?)\)",
        sql_text,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, f"{type_name} is not declared in schema.sql"
    return re.findall(r"'([^']*)'", match.group(1))


def test_decision_kind_vocabulary_matches_adr() -> None:
    assert _enum_values(_schema(), "decision_kind") == DECISION_KINDS


def test_decision_value_vocabulary_matches_adr() -> None:
    assert _enum_values(_schema(), "decision_value") == DECISION_VALUES


def test_decision_tables_exist() -> None:
    sql = _schema()
    missing = [t for t in DECISION_TABLES if f"create table {t} (" not in sql]
    assert not missing, f"missing decision tables: {missing}"


def test_superseded_approvals_shape_is_gone() -> None:
    """The mutable approvals row could not distinguish an explicit refusal from undecided."""
    sql = _schema()
    assert "create table approvals (" not in sql
    assert "create type distribution_state" not in sql


def test_users_has_no_single_role_column() -> None:
    """Roles are many-to-many so one principal can hold every role after the placement ends."""
    users_block = re.search(r"create table users \((.*?)\n\);", _schema(), re.DOTALL)
    assert users_block, "users table not found"
    assert "role_id" not in users_block.group(1)


def test_current_decision_view_is_the_named_combined_read() -> None:
    assert "create view current_report_decisions as" in _schema()


def test_audit_log_is_append_only_by_trigger() -> None:
    """#118: audit_log must carry the same UPDATE/DELETE-blocking trigger the decision tables use.

    Behaviour is proven against a real Postgres in test_audit.py; this text-level guard runs with no
    database, so removing the trigger line fails CI even on the no-DB path rather than silently
    dropping immutability.
    """
    sql = _schema()
    assert (
        "create trigger audit_log_append_only before update or delete on audit_log" in sql
    ), "audit_log lost its append-only trigger"
    assert "execute function reject_evidence_change()" in sql
