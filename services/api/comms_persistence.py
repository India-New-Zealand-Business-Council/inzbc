"""Postgres persistence for Comms Assistant drafts and their approval (#193/#60/#65 dependency).

Two acts, two audited writes: `create()` records a generated draft; `approve()` records a named
human's approval of it. Deliberately no `reject`/`return for correction`/`supersede` path -
`database/schema.sql`'s `comms_draft_status` enum only has `Draft`/`Approved`, matching what this
module actually does. Nothing here sends or publishes anything; the send/publish handoff mechanism
is unspecified anywhere in this codebase (`docs/api-integration-spec.md` Open item #4), so building
one here would be inventing a control this platform cannot yet enforce.

**Self-approval is refused outright, no exception mechanism.** `services/api/auth.py`'s
`refuse_self_review` (BR8: the person who produced something does not also approve it) is reused
as-is rather than reimplementing the candidate-style `sod_exceptions` override - INZBC's staffing
reality that motivates that override on candidates (one person often holding every SIP role) is a
SIP-specific fact, not something this module should assume applies to comms approval without a
product decision saying so. If a real single-operator deadlock shows up here, it is a decision to
make deliberately, not to default into by copying the pattern.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

from services.api.audit import record_audit
from services.api.auth import Principal, refuse_self_review

_SELECT_COLUMNS = (
    "id, content_type, brief, draft_text, status, authored_by, approved_by, "
    "approved_at, approval_reason, created_at"
)


@dataclass(frozen=True)
class CommsDraftRecord:
    id: str
    content_type: str
    brief: str
    draft_text: str
    status: str
    authored_by: str
    approved_by: str | None
    approved_at: str | None
    approval_reason: str | None
    created_at: str


def _row_to_record(row: dict) -> CommsDraftRecord:
    return CommsDraftRecord(
        id=str(row["id"]),
        content_type=row["content_type"],
        brief=row["brief"],
        draft_text=row["draft_text"],
        status=row["status"],
        authored_by=str(row["authored_by"]),
        approved_by=str(row["approved_by"]) if row["approved_by"] else None,
        approved_at=row["approved_at"].isoformat() if row["approved_at"] else None,
        approval_reason=row["approval_reason"],
        created_at=row["created_at"].isoformat(),
    )


class CommsDraftRepository:
    """Postgres-backed persistence for `comms_drafts`."""

    def __init__(self, database_url: str | None = None):
        self._database_url = database_url or os.environ["DATABASE_URL"]

    def create(
        self,
        content_type: str,
        brief: str,
        draft_text: str,
        *,
        authored_by: str,
    ) -> CommsDraftRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                "insert into comms_drafts (content_type, brief, draft_text, authored_by) "
                "values (%s, %s, %s, %s) "
                f"returning {_SELECT_COLUMNS}",
                (content_type, brief, draft_text, authored_by),
            ).fetchone()
            record_audit(
                conn,
                user_id=authored_by,
                action="comms_draft.create",
                record_type="comms_drafts",
                record_id=str(row["id"]),
                new_value=content_type,
                reason=f"{content_type} draft generated",
            )
            conn.commit()
        return _row_to_record(row)

    def approve(
        self,
        draft_id: str,
        *,
        principal: Principal,
        reason: str | None = None,
    ) -> CommsDraftRecord:
        """Sets `status` to `Approved`. Refuses (via `refuse_self_review`) an approver who
        authored the draft being approved - BR8 applied to comms, same shape as the candidate
        verification gate.
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            # Locked, then checked, inside the same transaction - a concurrent create cannot
            # slip a different authored_by in between the read and the update, and two approvers
            # racing the same draft cannot both succeed against a row already marked Approved.
            current = conn.execute(
                f"select {_SELECT_COLUMNS} from comms_drafts where id = %s for update",
                (draft_id,),
            ).fetchone()
            if current is None:
                raise KeyError(f"no comms draft {draft_id!r}")

            refuse_self_review(principal, current["authored_by"])

            if current["status"] == "Approved":
                # Idempotent read of the existing approval rather than a second audit row -
                # approving twice is not a new act, and re-recording it would let a duplicate
                # request read as two independent reviewers having signed off.
                return _row_to_record(current)

            row = conn.execute(
                "update comms_drafts set status = 'Approved', approved_by = %s, "
                "approved_at = now(), approval_reason = %s where id = %s "
                f"returning {_SELECT_COLUMNS}",
                (principal.user_id, reason, draft_id),
            ).fetchone()
            record_audit(
                conn,
                user_id=principal.user_id,
                action="comms_draft.approve",
                record_type="comms_drafts",
                record_id=draft_id,
                old_value="Draft",
                new_value="Approved",
                reason=reason or f"{current['content_type']} draft approved",
            )
            conn.commit()
        return _row_to_record(row)

    def delete(self, draft_id: str, *, principal: Principal, reason: str) -> None:
        """Removes a draft. The act is audited; the text is not (#342).

        **Why this exists.** `comms_drafts.brief` is the one field in the system where personal
        data can arrive without anyone deciding it should: a staff member types it, and redaction
        cannot remove a name from prose (ADR-0006). Until this existed, someone who typed a
        member's name into a brief had no way to remove it.

        **The audit row deliberately does not record what was deleted**, and that is the whole
        design. `record_audit` normally captures `old_value` so a reader can see what changed;
        doing that here would copy the brief's text into `audit_log`, which *is* append-only and
        whose grant is insert/select only. The sensitive text would become permanent in the one
        table nothing can remove it from - the exact opposite of what a caller invoking this is
        trying to achieve. So the record says a deletion happened, who did it, and why; it does
        not say what it contained.

        For the same reason `reason` is operator free text and is stored in an append-only table:
        it must describe *why*, not repeat the thing being removed. The API docstring says so to
        the caller, since this function cannot enforce it.

        **Any status may be deleted, including Approved.** Deleting the row does not erase the
        approval: `comms_draft.approve` already wrote its own audit entry, and that entry survives.
        The act stays on the record; only the text goes.
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            # Locked before deleting so a concurrent approve cannot land between the existence
            # check and the delete, which would record an approval of a row that no longer exists.
            current = conn.execute(
                "select id, content_type from comms_drafts where id = %s for update",
                (draft_id,),
            ).fetchone()
            if current is None:
                raise KeyError(f"no comms draft {draft_id!r}")

            conn.execute("delete from comms_drafts where id = %s", (draft_id,))
            record_audit(
                conn,
                user_id=principal.user_id,
                action="comms_draft.delete",
                record_type="comms_drafts",
                record_id=draft_id,
                # No old_value. See the docstring - this omission is the point, not an oversight.
                new_value=None,
                reason=reason,
            )
            conn.commit()

    def get(self, draft_id: str) -> CommsDraftRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                f"select {_SELECT_COLUMNS} from comms_drafts where id = %s", (draft_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"no comms draft {draft_id!r}")
        return _row_to_record(row)

    def list_all(self) -> list[CommsDraftRecord]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            rows = conn.execute(
                f"select {_SELECT_COLUMNS} from comms_drafts order by created_at desc"
            ).fetchall()
        return [_row_to_record(row) for row in rows]


def get_comms_draft_repository() -> CommsDraftRepository:
    """FastAPI dependency, overridden in tests - same pattern as `services/api/runs.py`'s
    `get_run_repository`.
    """
    return CommsDraftRepository()
