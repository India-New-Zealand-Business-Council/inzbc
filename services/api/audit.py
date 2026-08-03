"""Transactional audit-write service (#118).

Writes an append-only row to `audit_log` using the *caller's* open psycopg connection, so the audit
record and the mutation it describes share one transaction: they commit together or not at all. This
is the deeper control #118 asks for over the audit-log middleware in #42 — the trail is immutable in
the database (an INSERT/SELECT-only app role plus an UPDATE/DELETE-blocking trigger; see
`database/schema.sql` and `database/audit_role.sql`), not merely by application convention.

`record_audit` deliberately does not open its own connection and never commits or rolls back. A
function that committed here would defeat the entire point, making the audit row durable independently
of the mutation it records; one that opened its own connection could not share the mutation's
transaction at all. The caller owns the transaction boundary; this writes inside it.
"""

from __future__ import annotations

import psycopg
from psycopg.rows import tuple_row


def record_audit(
    conn: psycopg.Connection,
    *,
    action: str,
    user_id: str | None = None,
    record_type: str | None = None,
    record_id: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    reason: str | None = None,
    approval_ref: str | None = None,
) -> int:
    """Insert one row into `audit_log` on `conn`, without committing; returns the new row id.

    `action` is required because `audit_log.action` is NOT NULL; every other column is nullable in
    the schema and so stays optional here. `user_id` is a `users.id` (the actor) or None for a
    system action. Does not commit or roll back — the caller's transaction owns durability, which is
    exactly what makes the audit row atomic with the mutation it describes.

    Uses an explicit `tuple_row` cursor so the returned id is read the same way regardless of the
    connection's own `row_factory` (the persistence adapter uses `dict_row`).
    """
    with conn.cursor(row_factory=tuple_row) as cur:
        cur.execute(
            "insert into audit_log "
            "(user_id, action, record_type, record_id, old_value, new_value, reason, approval_ref) "
            "values (%s, %s, %s, %s, %s, %s, %s, %s) returning id",
            (user_id, action, record_type, record_id, old_value, new_value, reason, approval_ref),
        )
        return cur.fetchone()[0]
