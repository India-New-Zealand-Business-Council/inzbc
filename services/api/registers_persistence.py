"""Postgres persistence for the Intelligence Database's registers (#209).

`database/schema.sql` already models `action_register`, `watch_lists` and `exceptions` -
Bhanu's Workstream A, per `docs/sip/build-plan.md`. Nothing wrote to them: the controlled launch
recorded source outcomes, exceptions and carried-forward actions by hand, so a failed source or
an overdue action was invisible unless someone remembered to check the workbook. This module is
the write path that makes them part of the application rather than a manual habit.

**Scope note, so the lane split stays explicit.** `docs/sip/build-plan.md`'s Workstream C
("Registers UI: Action Register... Watch Lists... Exceptions/Corrections") is Paras's, not this
module's. This is persistence and API only - the same split as `source_checks.py`/
`comms_persistence.py` this week: the write path exists so a UI has something to build against,
it is not the UI.

**Exceptions are append-only, everything else is not.** SIP-050's own rule ("Do not overwrite
run evidence... exceptions and corrections. Correct a record through a linked correction or
superseding record") means `ExceptionRepository` has no update method at all - only `record()`
and `correct()`, and `correct()` inserts a new row rather than touching the one it corrects, the
same shape `decision_records.supersedes_id` already uses elsewhere in this schema.
`action_register`/`watch_lists` are operational trackers, not evidence, so they update in place -
same distinction the schema itself draws by giving `decision_records` a `supersedes_id` chain and
giving `action_register` a plain mutable `status`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

from services.api.audit import record_audit

_ACTION_COLUMNS = (
    "id, action_code, title, description, owner_id, owner_text, priority, due_date, "
    "review_date, status, evidence_ref, closed_at, created_at"
)
_WATCH_COLUMNS = "id, watch_code, title, category, frequency, escalation, status, next_review"
_EXCEPTION_COLUMNS = (
    "id, run_id, exception_type, severity, owner_id, status, original_preserved, "
    "correction_ref, created_at"
)


def _iso(value):
    return value.isoformat() if value is not None else None


@dataclass(frozen=True)
class ActionRegisterRecord:
    id: str
    action_code: str
    title: str
    description: str | None
    owner_id: str | None
    owner_text: str | None
    priority: str | None
    due_date: str | None
    review_date: str | None
    status: str
    evidence_ref: str | None
    closed_at: str | None
    created_at: str


def _action_row_to_record(row: dict) -> ActionRegisterRecord:
    return ActionRegisterRecord(
        id=str(row["id"]),
        action_code=row["action_code"],
        title=row["title"],
        description=row["description"],
        owner_id=str(row["owner_id"]) if row["owner_id"] else None,
        owner_text=row["owner_text"],
        priority=row["priority"],
        due_date=_iso(row["due_date"]),
        review_date=_iso(row["review_date"]),
        status=row["status"],
        evidence_ref=row["evidence_ref"],
        closed_at=_iso(row["closed_at"]),
        created_at=_iso(row["created_at"]),
    )


class ActionRegisterRepository:
    """SIP-050: "A named owner must perform and evidence an action." `owner_id` (a real user) and
    `owner_text` (free text, for an owner outside the platform's user table - a board member, an
    external contact) are both optional individually, but a row naming neither has no owner at
    all, which is the one thing this register exists to prevent going unnoticed.
    """

    def __init__(self, database_url: str | None = None):
        self._database_url = database_url or os.environ["DATABASE_URL"]

    def create(
        self,
        action_code: str,
        title: str,
        status: str,
        *,
        actor_id: str,
        description: str | None = None,
        owner_id: str | None = None,
        owner_text: str | None = None,
        priority: str | None = None,
        due_date: str | None = None,
        review_date: str | None = None,
        evidence_ref: str | None = None,
    ) -> ActionRegisterRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                "insert into action_register (action_code, title, description, owner_id, "
                "owner_text, priority, due_date, review_date, status, evidence_ref) "
                "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                f"returning {_ACTION_COLUMNS}",
                (
                    action_code, title, description, owner_id, owner_text, priority,
                    due_date, review_date, status, evidence_ref,
                ),
            ).fetchone()
            record_audit(
                conn,
                user_id=actor_id,
                action="action_register.create",
                record_type="action_register",
                record_id=str(row["id"]),
                new_value=status,
                reason=f"{action_code}: {title}",
            )
            conn.commit()
        return _action_row_to_record(row)

    def update_status(
        self,
        action_id: str,
        status: str,
        *,
        actor_id: str,
        evidence_ref: str | None = None,
    ) -> ActionRegisterRecord:
        """Sets `status`. `closed_at` is set only when the new status is exactly `Closed` - a
        status of `Controlled Monitoring` or any other value must not look closed by accident.
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            current = conn.execute(
                "select status from action_register where id = %s for update", (action_id,)
            ).fetchone()
            if current is None:
                raise KeyError(f"no action {action_id!r}")

            closed_at_clause = "now()" if status == "Closed" else "null"
            row = conn.execute(
                f"update action_register set status = %s, closed_at = {closed_at_clause}, "
                "evidence_ref = coalesce(%s, evidence_ref) where id = %s "
                f"returning {_ACTION_COLUMNS}",
                (status, evidence_ref, action_id),
            ).fetchone()
            record_audit(
                conn,
                user_id=actor_id,
                action="action_register.update_status",
                record_type="action_register",
                record_id=action_id,
                old_value=current["status"],
                new_value=status,
                reason=evidence_ref,
            )
            conn.commit()
        return _action_row_to_record(row)

    def get(self, action_id: str) -> ActionRegisterRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                f"select {_ACTION_COLUMNS} from action_register where id = %s", (action_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"no action {action_id!r}")
        return _action_row_to_record(row)

    def list_all(self) -> list[ActionRegisterRecord]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            rows = conn.execute(
                f"select {_ACTION_COLUMNS} from action_register order by created_at desc"
            ).fetchall()
        return [_action_row_to_record(row) for row in rows]


@dataclass(frozen=True)
class WatchListRecord:
    id: str
    watch_code: str
    title: str
    category: str | None
    frequency: str | None
    escalation: str | None
    status: str
    next_review: str | None


def _watch_row_to_record(row: dict) -> WatchListRecord:
    return WatchListRecord(
        id=str(row["id"]),
        watch_code=row["watch_code"],
        title=row["title"],
        category=row["category"],
        frequency=row["frequency"],
        escalation=row["escalation"],
        status=row["status"],
        next_review=_iso(row["next_review"]),
    )


class WatchListRepository:
    """Items requiring monitoring across more than one run (SIP-050 routing table: Opportunity
    Register, Threat Register and ongoing watches all land here as one table, distinguished by
    `category` rather than three separate tables the schema does not have).
    """

    def __init__(self, database_url: str | None = None):
        self._database_url = database_url or os.environ["DATABASE_URL"]

    def create(
        self,
        watch_code: str,
        title: str,
        status: str,
        *,
        actor_id: str,
        category: str | None = None,
        frequency: str | None = None,
        escalation: str | None = None,
        next_review: str | None = None,
    ) -> WatchListRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                "insert into watch_lists (watch_code, title, category, frequency, escalation, "
                "status, next_review) values (%s, %s, %s, %s, %s, %s, %s) "
                f"returning {_WATCH_COLUMNS}",
                (watch_code, title, category, frequency, escalation, status, next_review),
            ).fetchone()
            record_audit(
                conn,
                user_id=actor_id,
                action="watch_list.create",
                record_type="watch_lists",
                record_id=str(row["id"]),
                new_value=status,
                reason=f"{watch_code}: {title}",
            )
            conn.commit()
        return _watch_row_to_record(row)

    def update_status(
        self,
        watch_id: str,
        status: str,
        *,
        actor_id: str,
        next_review: str | None = None,
    ) -> WatchListRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            current = conn.execute(
                "select status from watch_lists where id = %s for update", (watch_id,)
            ).fetchone()
            if current is None:
                raise KeyError(f"no watch-list entry {watch_id!r}")

            row = conn.execute(
                "update watch_lists set status = %s, "
                "next_review = coalesce(%s, next_review) where id = %s "
                f"returning {_WATCH_COLUMNS}",
                (status, next_review, watch_id),
            ).fetchone()
            record_audit(
                conn,
                user_id=actor_id,
                action="watch_list.update_status",
                record_type="watch_lists",
                record_id=watch_id,
                old_value=current["status"],
                new_value=status,
            )
            conn.commit()
        return _watch_row_to_record(row)

    def get(self, watch_id: str) -> WatchListRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                f"select {_WATCH_COLUMNS} from watch_lists where id = %s", (watch_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"no watch-list entry {watch_id!r}")
        return _watch_row_to_record(row)

    def list_all(self) -> list[WatchListRecord]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            rows = conn.execute(f"select {_WATCH_COLUMNS} from watch_lists order by title").fetchall()
        return [_watch_row_to_record(row) for row in rows]


@dataclass(frozen=True)
class ExceptionRecord:
    id: str
    run_id: str | None
    exception_type: str
    severity: str
    owner_id: str | None
    status: str
    original_preserved: bool
    correction_ref: str | None
    created_at: str


def _exception_row_to_record(row: dict) -> ExceptionRecord:
    return ExceptionRecord(
        id=str(row["id"]),
        run_id=str(row["run_id"]) if row["run_id"] else None,
        exception_type=row["exception_type"],
        severity=row["severity"],
        owner_id=str(row["owner_id"]) if row["owner_id"] else None,
        status=row["status"],
        original_preserved=row["original_preserved"],
        correction_ref=row["correction_ref"],
        created_at=_iso(row["created_at"]),
    )


class ExceptionRepository:
    """Append-only. `record()` and `correct()` both insert; neither updates a row in place.

    A `correct()` call creates a new row whose `correction_ref` carries the original row's id,
    the same superseding-record shape `decision_records.supersedes_id` uses elsewhere in this
    schema - the original stays exactly as it was recorded, which is the entire point of an
    append-only evidence trail: a corrected exception is a second event, not a rewritten first one.
    """

    def __init__(self, database_url: str | None = None):
        self._database_url = database_url or os.environ["DATABASE_URL"]

    def record(
        self,
        exception_type: str,
        severity: str,
        status: str,
        *,
        actor_id: str,
        run_id: str | None = None,
        owner_id: str | None = None,
        original_preserved: bool = True,
    ) -> ExceptionRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                "insert into exceptions (run_id, exception_type, severity, owner_id, status, "
                "original_preserved) values (%s, %s, %s, %s, %s, %s) "
                f"returning {_EXCEPTION_COLUMNS}",
                (run_id, exception_type, severity, owner_id, status, original_preserved),
            ).fetchone()
            record_audit(
                conn,
                user_id=actor_id,
                action="exception.record",
                record_type="exceptions",
                record_id=str(row["id"]),
                new_value=exception_type,
                reason=f"{severity}: {exception_type}",
            )
            conn.commit()
        return _exception_row_to_record(row)

    def correct(
        self,
        original_exception_id: str,
        exception_type: str,
        severity: str,
        status: str,
        *,
        actor_id: str,
        reason: str,
    ) -> ExceptionRecord:
        """Inserts a new exception row correcting `original_exception_id`. The original is read
        to confirm it exists and to carry its `run_id`/`owner_id` forward, and is never written to.
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            original = conn.execute(
                "select run_id, owner_id from exceptions where id = %s", (original_exception_id,)
            ).fetchone()
            if original is None:
                raise KeyError(f"no exception {original_exception_id!r}")

            row = conn.execute(
                "insert into exceptions (run_id, exception_type, severity, owner_id, status, "
                "original_preserved, correction_ref) values (%s, %s, %s, %s, %s, true, %s) "
                f"returning {_EXCEPTION_COLUMNS}",
                (
                    original["run_id"], exception_type, severity, original["owner_id"],
                    status, original_exception_id,
                ),
            ).fetchone()
            record_audit(
                conn,
                user_id=actor_id,
                action="exception.correct",
                record_type="exceptions",
                record_id=str(row["id"]),
                old_value=original_exception_id,
                new_value=exception_type,
                reason=reason,
            )
            conn.commit()
        return _exception_row_to_record(row)

    def get(self, exception_id: str) -> ExceptionRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                f"select {_EXCEPTION_COLUMNS} from exceptions where id = %s", (exception_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"no exception {exception_id!r}")
        return _exception_row_to_record(row)

    def list_for_run(self, run_id: str) -> list[ExceptionRecord]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            rows = conn.execute(
                f"select {_EXCEPTION_COLUMNS} from exceptions where run_id = %s order by created_at",
                (run_id,),
            ).fetchall()
        return [_exception_row_to_record(row) for row in rows]

    def list_all(self) -> list[ExceptionRecord]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            rows = conn.execute(
                f"select {_EXCEPTION_COLUMNS} from exceptions order by created_at desc"
            ).fetchall()
        return [_exception_row_to_record(row) for row in rows]


def get_action_register_repository() -> ActionRegisterRepository:
    return ActionRegisterRepository()


def get_watch_list_repository() -> WatchListRepository:
    return WatchListRepository()


def get_exception_repository() -> ExceptionRepository:
    return ExceptionRepository()
