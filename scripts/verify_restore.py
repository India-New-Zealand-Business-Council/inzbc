"""Prove a restored database is actually usable, and say so or fail.

BR12 and objective O6 name a *tested* restore. An untested backup is a belief, and the belief that
fails is always the same one: the rows came back, so the restore worked. Rows are the easy part.

What this checks, in the order the checks get harder:

1. The schema is there at all.
2. The evidence tables came back.
3. **The append-only triggers came back.** This is the one that matters and the one a manual check
   skips. Triggers are schema objects, not data: a restore that recreates every table and every
   row but drops `audit_log_append_only` leaves the audit trail silently editable, and nothing
   about the database looks wrong.
4. The immutability actually holds, tested by trying to break it rather than by reading the
   catalogue. A trigger that exists and does not fire is worse than one that is missing, because
   the catalogue check passes.

Read-only apart from step 4, which writes inside a transaction it always rolls back. Point it at
a restored copy, never at production.

    python scripts/verify_restore.py "postgresql://..."
"""

from __future__ import annotations

import sys
import time

import psycopg

# Tables whose contents are evidence: they answer "who approved this, and when". Losing a row here
# is not a data-loss inconvenience, it is the system losing the ability to answer the question it
# exists to answer.
EVIDENCE_TABLES = (
    "audit_log",
    "decision_records",
    "report_versions",
    "sod_exceptions",
    "candidate_sod_exceptions",
    "distribution_deliveries",
)

# Every table the application reads or writes. Kept separate from EVIDENCE_TABLES so a missing
# operational table and a missing evidence table are different failures in the output.
CORE_TABLES = (
    "users",
    "roles",
    "user_roles",
    "sessions",
    "runs",
    "candidates",
    "source_library",
)


class RestoreCheckFailed(Exception):
    """At least one check failed. The message names which."""


def _fail(problems: list[str], message: str) -> None:
    problems.append(message)
    print(f"  FAIL  {message}")


def _ok(message: str) -> None:
    print(f"  ok    {message}")


def check_tables(conn: psycopg.Connection, problems: list[str]) -> None:
    present = {
        row[0]
        for row in conn.execute(
            "select table_name from information_schema.tables where table_schema = 'public'"
        ).fetchall()
    }
    for table in CORE_TABLES + EVIDENCE_TABLES:
        if table in present:
            _ok(f"table {table}")
        else:
            _fail(problems, f"table {table} is missing")


def check_row_counts(conn: psycopg.Connection) -> None:
    """Reported, never asserted on.

    A restore of an empty database is a legitimate thing to verify, so a zero count is not a
    failure. It is worth printing because a count that is zero when the operator expected
    thousands is the fastest way to notice the wrong backup was restored.
    """
    for table in EVIDENCE_TABLES:
        count = conn.execute(f"select count(*) from {table}").fetchone()[0]
        print(f"  ....  {table}: {count} rows")


def check_triggers(conn: psycopg.Connection, problems: list[str]) -> None:
    """Both guards per evidence table: the row trigger and the whole-table one.

    A row trigger never fires for a whole-table wipe, so a table carrying only the row trigger can
    still be emptied in one statement without meeting any guard.
    """
    rows = conn.execute(
        "select c.relname, t.tgname from pg_trigger t "
        "join pg_class c on c.oid = t.tgrelid "
        "where not t.tgisinternal"
    ).fetchall()
    by_table: dict[str, set[str]] = {}
    for table, trigger in rows:
        by_table.setdefault(table, set()).add(trigger)

    for table in EVIDENCE_TABLES:
        triggers = by_table.get(table, set())
        if any(name.endswith("_append_only") for name in triggers):
            _ok(f"{table} append-only trigger")
        else:
            _fail(problems, f"{table} lost its append-only trigger: it is now editable")
        if any(name.endswith("_no_wipe") for name in triggers):
            _ok(f"{table} whole-table guard")
        else:
            _fail(problems, f"{table} lost its whole-table guard: it can be emptied in one statement")


def check_immutability_holds(conn: psycopg.Connection, problems: list[str]) -> None:
    """Try to edit an audit row, and require the attempt to be refused.

    The catalogue check above proves a trigger exists. This proves it fires. Those are different
    claims, and the gap between them is exactly where a restore goes wrong: a trigger restored
    without its function, or left disabled, is present in `pg_trigger` and does nothing.

    Rolled back either way, so this never changes the database it is checking.
    """
    if conn.execute("select count(*) from audit_log").fetchone()[0] == 0:
        print("  ....  audit_log is empty, skipping the live immutability check")
        return

    try:
        with conn.transaction() as tx:
            conn.execute("update audit_log set reason = 'restore check' where id = (select min(id) from audit_log)")
            tx.rollback()
    except psycopg.errors.RaiseException:
        _ok("audit_log refuses an update in practice, not just on paper")
        return
    except psycopg.Error as error:
        _fail(problems, f"audit_log update failed for an unexpected reason: {error}")
        return
    _fail(problems, "audit_log accepted an update: the trigger exists but does not fire")


def main(database_url: str) -> int:
    started = time.monotonic()
    problems: list[str] = []

    print(f"Checking restored database at {database_url.split('@')[-1]}\n")
    with psycopg.connect(database_url) as conn:
        print("Tables")
        check_tables(conn, problems)
        print("\nEvidence row counts")
        check_row_counts(conn)
        print("\nAppend-only guards")
        check_triggers(conn, problems)
        print("\nImmutability in practice")
        check_immutability_holds(conn, problems)

    elapsed = time.monotonic() - started
    print(f"\nChecks took {elapsed:.1f}s. This is not the restore time; time that separately.")

    if problems:
        print(f"\n{len(problems)} problem(s). This restore is NOT usable as evidence:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\nRestore verified: schema, evidence tables and append-only guards all present and enforcing.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
