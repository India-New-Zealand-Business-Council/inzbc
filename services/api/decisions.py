"""Recording CEO rulings, report approvals and distribution authority (ADR-0005, #125).

Three facts, three immutable streams, one head each. `decision_records` is append-only: a
correction is a new record superseding its predecessor, never an edit. The only mutable part of the
model is `decision_streams.current_record_id`, and moving it is a compare-and-swap.

Why the CAS rather than a lock: `Awaiting CEO Decision` can sit for hours, so holding a transaction
open across a human decision is not an option. The pattern matches `RunRepository.apply_transition`
deliberately, so there is one concurrency story on the platform rather than two.

**What this module does not do.** It records a decision. It does not evaluate the release predicate
from ADR-0005 Decision 2, because the schema cannot answer it yet: there is no durable QA-failure
table, so "no open Critical QA failure" is unanswerable, and `distribution_configuration` is a
mutable singleton nothing references, so "the recipient has not changed since authorisation" is
unprovable. `schemas/api-contract.md` records both as follow-up. Anything calling `authorise` must
therefore still enforce that predicate itself, and this docstring is the warning that it must.

Separation of duties is likewise not enforced here. `decision_sod_role_pairs` is configuration that
nothing consults, so an unrecorded self-approval is refused only by the FK to `sod_exceptions` when
one is cited, not by comparing actors across records. That is ADR-0005 required follow-up 4.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime

import psycopg
from psycopg.rows import dict_row

# The three streams a submitted report version carries. Opened by a trigger on insert, so a
# decision can never arrive for a stream nobody created.
CEO_RULING = "CEO Ruling"
REPORT_APPROVAL = "Report Approval"
DISTRIBUTION_AUTHORITY = "Distribution Authority"


class DecisionNotPermittedError(RuntimeError):
    """Raised when the actor may not record this decision kind in this role.

    Fail closed, the same shape as the rest of ADR-0005: a disabled permission, a disabled role
    assignment or an inactive account all refuse. The foreign key alone cannot express this,
    because it matches on `(kind, actor_role_id)` and never looks at `enabled`.
    """


class DecisionConflictError(RuntimeError):
    """Raised when the stream head moved between read and write.

    The caller re-reads the current decision and decides whether its intent still applies. It must
    not retry blindly: the ruling it was responding to may have been superseded, which is exactly
    the case this exists to catch.
    """


class DecisionRejected(ValueError):
    """Raised when the database refuses the record: illegal kind/value pair, an unpermitted role,
    a recipient missing on a distribution decision, or supersession crossing streams. The message
    carries the constraint name so the caller can tell which rule bit.
    """


@dataclass(frozen=True)
class DecisionRecord:
    """One decision act, as stored. Immutable, like the row."""

    id: str
    stream_id: str
    report_version_id: str
    kind: str
    stream_revision: int
    value: str
    actor_id: str
    decided_at: str
    reason: str


@dataclass(frozen=True)
class CurrentDecisions:
    """The `current_report_decisions` view for one report version.

    A `None` value means undecided *after submission*, which is a different fact from an explicit
    refusal. `Not Authorised` is a decision; `None` is the absence of one. Keeping them distinct is
    the whole reason the old mutable `approvals` row was replaced.

    `revisions` carries each stream's head revision. A caller passes the one it read back to
    `record()`, which is what makes a decision built on a superseded ruling detectable.
    """

    report_version_id: str
    ceo_ruling: str | None
    report_approval: str | None
    distribution_authority: str | None
    distribution_recipient: str | None
    revisions: dict[str, int]


class DecisionRepository:
    """Append-only decision storage. See the module docstring for what it deliberately omits."""

    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or os.environ["DATABASE_URL"]

    def current(self, report_version_id: str) -> CurrentDecisions:
        """Reads the current decisions and the revision each was read at, in one statement.

        One statement, not two, and that is the whole point. Under `READ COMMITTED` every statement
        takes its own snapshot, so reading the values and then the head revisions let a decision
        commit in between: the caller received a ruling from before the write paired with the head
        revision from after it. Passing that revision back to `record` then satisfied the
        compare-and-swap, and the correction superseded a ruling nobody had seen. The revision is
        supposed to mean "this is the ruling I read", and split across two statements it did not.

        The subquery shares the enclosing statement's snapshot, so values and revisions cannot
        disagree.
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                "select v.report_version_id, v.ceo_ruling, v.report_approval, "
                "       v.distribution_authority, v.distribution_recipient, "
                "       coalesce("
                "         (select jsonb_object_agg(s.kind, s.head_revision) "
                "          from decision_streams s "
                "          where s.report_version_id = v.report_version_id), "
                "         '{}'::jsonb) as revisions "
                "from current_report_decisions v where v.report_version_id = %s",
                (report_version_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"no submitted report version {report_version_id!r}")
        return CurrentDecisions(
            report_version_id=str(row["report_version_id"]),
            ceo_ruling=row["ceo_ruling"],
            report_approval=row["report_approval"],
            distribution_authority=row["distribution_authority"],
            distribution_recipient=row["distribution_recipient"],
            revisions=dict(row["revisions"] or {}),
        )

    def record(
        self,
        *,
        report_version_id: str,
        kind: str,
        value: str,
        actor_id: str,
        actor_role_id: int,
        reason: str,
        evidence_ref: str,
        owner_id: str,
        next_review: date,
        decided_at: datetime,
        idempotency_key: uuid.UUID,
        expected_head_revision: int,
        distribution_recipient: str | None = None,
        sod_exception_id: str | None = None,
        conditions: list[str] | None = None,
    ) -> DecisionRecord:
        """Appends one decision and advances its stream head, in a single transaction.

        The whole operation is one transaction because a record that is not the head is invisible
        to every reader: `current_report_decisions` joins through `current_record_id`. Committing
        the insert without the head advance would leave a decision that happened but that nothing
        can see, which is worse than not recording it.

        `expected_head_revision` is the revision the caller read from `current()`. It is the whole
        concurrency mechanism: `SELECT ... FOR UPDATE` alone only serialises writers, so the second
        one would re-read the head the first just wrote and legitimately supersede a ruling it had
        never seen. Comparing against the revision the caller actually decided on is what turns
        that into a detectable conflict.

        Passing the current revision is therefore an assertion, not a formality: "I read this
        ruling, and I am deciding in response to it."
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                # The foreign key on (kind, actor_role_id) proves a permission row exists. It does
                # not prove the row is enabled, that the actor still holds the role, or that the
                # account is active, because a foreign key cannot look at a column it does not
                # match on. `database/schema.sql` says so and says the writing command must check;
                # this is that check, and without it revoking a permission by setting
                # `enabled = false` did nothing at all.
                allowed = conn.execute(
                    "select 1 from decision_role_permissions p "
                    "join user_roles ur on ur.role_id = p.actor_role_id "
                    "join users u on u.id = ur.user_id "
                    "where p.kind = %s and p.actor_role_id = %s and p.enabled "
                    "  and ur.user_id = %s and ur.enabled and u.active",
                    (kind, actor_role_id, actor_id),
                ).fetchone()
                if allowed is None:
                    raise DecisionNotPermittedError(
                        f"{actor_id!r} may not record a {kind!r} decision as role "
                        f"{actor_role_id}. Either the permission is disabled, the actor does not "
                        "hold that role, the role assignment is disabled, or the account is "
                        "inactive. Absence is a refusal, not a gap to fill."
                    )

                # Separation of duties (#42, BR8, ADR-0005): nobody decides on their own output.
                # Holding the role is necessary and not sufficient, and the steady state after
                # the placement is one person holding every role, so the role check above cannot
                # carry this on its own. Checked inside the transaction against the version being
                # decided, so it cannot be raced.
                #
                # This covers the case that needs no client input. The wider role-pair rule in
                # `decision_sod_role_pairs` stays unenforced because that table is deliberately
                # unseeded pending client-answers B8, and enforcing an empty rule set would
                # refuse everything.
                author = conn.execute(
                    "select created_by from report_versions where id = %s",
                    (report_version_id,),
                ).fetchone()
                if author is not None and str(author["created_by"]) == str(actor_id):
                    raise DecisionNotPermittedError(
                        f"{actor_id!r} created report version {report_version_id!r} and may not "
                        f"also record a {kind!r} decision on it. Separation of duties is the "
                        "control this record exists to evidence; a decision one person can take "
                        "end to end does not evidence anything."
                    )

                stream = conn.execute(
                    "select id, current_record_id, head_revision from decision_streams "
                    "where report_version_id = %s and kind = %s for update",
                    (report_version_id, kind),
                ).fetchone()
                if stream is None:
                    raise KeyError(
                        f"no {kind!r} stream for report version {report_version_id!r}; the version "
                        "must be submitted before it can be decided on"
                    )

                if stream["head_revision"] != expected_head_revision:
                    raise DecisionConflictError(
                        f"{kind!r} stream for {report_version_id!r} is at revision "
                        f"{stream['head_revision']}, not {expected_head_revision}. Another decision "
                        "landed after the one this responds to; re-read it before deciding again."
                    )

                expected_head = stream["current_record_id"]
                next_revision = stream["head_revision"] + 1

                try:
                    inserted = conn.execute(
                        "insert into decision_records ("
                        "  stream_id, report_version_id, kind, stream_revision, value, actor_id,"
                        "  actor_role_id, decided_at, reason, conditions, owner_id, evidence_ref,"
                        "  next_review, distribution_recipient, supersedes_id, sod_exception_id,"
                        "  idempotency_key"
                        ") values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                        "returning id, stream_id, report_version_id, kind, stream_revision, value,"
                        "  actor_id, decided_at, reason",
                        (
                            stream["id"], report_version_id, kind, next_revision, value, actor_id,
                            actor_role_id, decided_at, reason, conditions or [], owner_id,
                            evidence_ref, next_review, distribution_recipient, expected_head,
                            sod_exception_id, str(idempotency_key),
                        ),
                    ).fetchone()
                except psycopg.errors.IntegrityError as error:
                    raise DecisionRejected(str(error).strip()) from error

                advanced = conn.execute(
                    "update decision_streams set current_record_id = %s, head_revision = %s "
                    "where id = %s and head_revision = %s "
                    "  and current_record_id is not distinct from %s "
                    "returning id",
                    (inserted["id"], next_revision, stream["id"], stream["head_revision"],
                     expected_head),
                ).fetchone()
                if advanced is None:
                    raise DecisionConflictError(
                        f"{kind!r} stream for {report_version_id!r} moved while this decision was "
                        "being recorded; re-read the current decision before deciding again"
                    )

        return DecisionRecord(
            id=str(inserted["id"]),
            stream_id=str(inserted["stream_id"]),
            report_version_id=str(inserted["report_version_id"]),
            kind=inserted["kind"],
            stream_revision=inserted["stream_revision"],
            value=inserted["value"],
            actor_id=str(inserted["actor_id"]),
            decided_at=inserted["decided_at"].isoformat(),
            reason=inserted["reason"],
        )
