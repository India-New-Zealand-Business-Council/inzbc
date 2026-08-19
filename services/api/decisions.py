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

**Separation of duties, and what is and is not enforced.** `record` refuses when the actor created
the report version being decided on, unless they cite an approved, unexpired `sod_exceptions` row
that covers exactly this act and was approved by someone else. That is the case needing no client
input, and it is enforced inside the transaction.

`decision_sod_role_pairs` remains unconsulted, so conflicts expressed as role pairs rather than
authorship are not caught. The table is deliberately unseeded pending client-answers B8, and
enforcing an empty rule set would refuse every decision. That part of ADR-0005 required follow-up 4
is still open, and this docstring is the warning that it is.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime

import psycopg
from psycopg.rows import dict_row

from services.api.audit import record_audit
from services.api.auth import canonical_actor

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

    @staticmethod
    def _require_valid_exception(
        conn: psycopg.Connection,
        *,
        sod_exception_id: str | None,
        report_version_id: str,
        kind: str,
        actor_id: str,
        actor_role_id: int,
    ) -> None:
        """Refuses a self-approval unless a recorded, still-valid exception permits this one.

        `sod_exceptions` existed and `decision_records.sod_exception_id` was written, but nothing
        ever read either: the self-approval check refused unconditionally, so the exception could
        never be exercised, and no other path required one. The column was recording a citation
        nobody had checked.

        The composite foreign key already binds a cited exception to this exact report version,
        kind, actor and role, and `unique (sod_exception_id)` stops one being reused. Both fire at
        insert time as constraint violations. Checking here instead means the refusal is the
        control saying no, with a reason, rather than the database rejecting a malformed row.

        Two things the schema does not express and this does:

        - **An expired exception does not authorise.** `review_date` is the date the exception was
          to be revisited; past it, it is a lapsed approval rather than a current one.
        - **Nobody approves their own exception.** `approved_by` is a plain FK to `users`, so
          without this an actor could record an exception permitting themselves and then cite it.
          That is self-approval with an extra step, and it would have looked like a control.
        """
        if sod_exception_id is None:
            raise DecisionNotPermittedError(
                f"{actor_id!r} created report version {report_version_id!r} and may not also "
                f"record a {kind!r} decision on it. Separation of duties is the control this "
                "record exists to evidence; a decision one person can take end to end does not "
                "evidence anything. Cite an approved sod_exceptions row if this is deliberate."
            )

        # The approver is joined through `users` rather than merely read, so an exception
        # naming a deactivated account cannot authorise anything. `approved_by` is a plain
        # foreign key to `users`, so nothing in the schema stops an inactive or roleless account
        # being named; an approval from someone who no longer works here is not an approval.
        exception = conn.execute(
            "select e.approved_by, e.review_date, "
            "       e.review_date < current_date as lapsed, "
            "       u.active as approver_active "
            "from sod_exceptions e join users u on u.id = e.approved_by "
            "where e.id = %s and e.report_version_id = %s and e.kind = %s "
            "  and e.actor_id = %s and e.actor_role_id = %s",
            (sod_exception_id, report_version_id, kind, actor_id, actor_role_id),
        ).fetchone()
        if exception is None:
            raise DecisionNotPermittedError(
                f"exception {sod_exception_id!r} does not cover {actor_id!r} recording a "
                f"{kind!r} decision as role {actor_role_id} on report version "
                f"{report_version_id!r}. An exception authorises one act, not a category."
            )

        if canonical_actor(exception["approved_by"]) == canonical_actor(actor_id):
            raise DecisionNotPermittedError(
                f"exception {sod_exception_id!r} was approved by the same person it exempts. "
                "A self-approved exception is self-approval with an extra step."
            )

        # Compared against the database's clock, not the application server's: expiry is a
        # property of the record, and two app instances in different timezones must not disagree
        # about whether an approval has lapsed.
        if not exception["approver_active"]:
            raise DecisionNotPermittedError(
                f"exception {sod_exception_id!r} was approved by an account that is no longer "
                "active. An approval from someone who has left is not a current approval."
            )

        if exception["lapsed"]:
            raise DecisionNotPermittedError(
                f"exception {sod_exception_id!r} was to be reviewed by "
                f"{exception['review_date'].isoformat()} and has lapsed. A lapsed approval is "
                "not a current one."
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
        with (
            psycopg.connect(self._database_url, row_factory=dict_row) as conn,
            conn.transaction(),
        ):
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
                # Canonicalised, not compared as raw strings. Postgres accepts an uppercase or
                # unhyphenated UUID for the foreign key, so the permission check above passes
                # while a raw string comparison here does not match - and the author approves
                # their own version. `canonical_actor` was written in `auth.py` for exactly this
                # and then not used here, which is the bug this line fixes.
                author_id = canonical_actor(author["created_by"]) if author else None
                if author_id is not None and author_id == canonical_actor(actor_id):
                    self._require_valid_exception(
                        conn,
                        sod_exception_id=sod_exception_id,
                        report_version_id=report_version_id,
                        kind=kind,
                        actor_id=actor_id,
                        actor_role_id=actor_role_id,
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


class QaSelfReviewError(RuntimeError):
    """The actor recording a QA result is the analyst on the run being checked.

    Its own type, like `SelfVerificationError`, so a caller can say which control refused. This is
    SIP-188's reviewer requirement, not a permissions problem, and answering "forbidden" would
    send an operator to ask for a role they already hold.
    """


class ReportVersionConflict(RuntimeError):
    """Two submissions raced for the same version number on one run.

    Its own type because the caller's move is to retry, not to change anything. `unique (run_id,
    version_number)` is what catches it: the next number is computed in the insert, and under
    `READ COMMITTED` two concurrent submissions can both read the same maximum.
    """


@dataclass(frozen=True)
class ReportVersion:
    """One submitted report version. Immutable, like the row: `report_versions` is append-only."""

    id: str
    run_id: str
    version_number: int
    created_by: str
    content_sha256: str
    created_at: str
    submitted_at: str


class ReportRepository:
    """Submitting and reading report versions (#124).

    Kept beside `DecisionRepository` rather than in `persistence.py` because the two are one
    subject: submitting a version is what opens its three decision streams, and reading a version
    without its current decisions tells a reviewer nothing they can act on.

    **Submitting is the act that makes a report decidable.** A trigger on insert opens the CEO
    Ruling, Report Approval and Distribution Authority streams, so a decision can never arrive for
    a stream nobody created. That is why there is no separate "open the streams" call to forget.
    """

    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or os.environ["DATABASE_URL"]

    def submit(
        self,
        *,
        run_id: str,
        content_sha256: str,
        actor_id: str,
        role_names: tuple[str, ...],
        created_at: datetime,
    ) -> ReportVersion:
        """Appends the next version of a run's report, and returns it.

        **The version number is computed in the insert**, not read and then written, so the value
        and the row that uses it come from one statement. That still races: two concurrent
        submissions can read the same maximum under `READ COMMITTED`. `unique (run_id,
        version_number)` is what actually prevents the duplicate, and this raises
        `ReportVersionConflict` so the caller retries rather than seeing an opaque database error.

        **`created_at` is supplied by the caller, `submitted_at` by the database.** They are
        different facts: when the content was produced, and when it was handed over for decision.
        The schema requires `submitted_at >= created_at`, so a `created_at` in the future is
        refused rather than quietly accepted.
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn, conn.transaction():
            # Resolved inside the same transaction as the insert, not before it. Two connections
            # left a window: the composite foreign key proves the `user_roles` row exists, not that
            # it is still enabled, so a role disabled between the lookup and the write would be
            # recorded as the role the act was performed in.
            actor_role_id = _role_id_for(conn, actor_id, role_names)
            try:
                row = conn.execute(
                    "insert into report_versions "
                    "(run_id, version_number, created_by, created_by_role_id, content_sha256, "
                    " created_at) "
                    "values (%s, (select coalesce(max(version_number), 0) + 1 from report_versions "
                    "             where run_id = %s), %s, %s, %s, %s) "
                    "returning id, run_id, version_number, created_by, content_sha256, "
                    "          created_at, submitted_at",
                    (run_id, run_id, actor_id, actor_role_id, content_sha256, created_at),
                ).fetchone()
            except psycopg.errors.UniqueViolation as error:
                raise ReportVersionConflict(
                    f"another version of run {run_id!r} was submitted at the same moment; "
                    "re-read and submit again"
                ) from error
        return _to_report_version(row)

    def get(self, report_version_id: str) -> ReportVersion:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                "select id, run_id, version_number, created_by, content_sha256, created_at, "
                "       submitted_at from report_versions where id = %s",
                (report_version_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"no report version {report_version_id!r}")
        return _to_report_version(row)

    def record_qa(
        self,
        report_version_id: str,
        *,
        result: str,
        critical_failures: int,
        actor_id: str,
        notes: str,
    ) -> str:
        """Records a SIP-188 QA result against the report version's run (#124).

        Writes `runs.qa_status`, which is the field `GET /api/dashboard` already reads, so the
        gate a reviewer sees is the one this wrote rather than a second copy of it.

        **The reviewer may not be the run's analyst.** SIP-188 says so in its own first paragraph,
        and it is the same separation the candidate commands enforce: QA is the check on the work,
        so the person who did the work cannot be the check on it. Enforced against
        `runs.analyst_id` rather than against whoever happens to hold the Analyst role, because
        the question is who did *this* run, not who could have.

        **A Pass cannot carry a Critical failure.** SIP-188 makes any Critical failure block
        release, so the two together are a contradiction rather than a judgement call, and
        recording it would leave `qa_status` saying the run is releasable while the checklist says
        it is not. A Fail with no Critical failures is allowed: that is the ordinary case of
        non-critical findings.
        """
        if result not in ("Pass", "Fail"):
            raise ValueError(f"QA result must be 'Pass' or 'Fail', not {result!r}")
        if critical_failures < 0:
            raise ValueError("critical_failures cannot be negative")
        if result == "Pass" and critical_failures > 0:
            raise ValueError(
                "a Pass cannot record Critical failures: SIP-188 blocks release on any Critical, "
                "so record it as a Fail"
            )

        with psycopg.connect(self._database_url, row_factory=dict_row) as conn, conn.transaction():
            row = conn.execute(
                "select rv.run_id, r.analyst_id, r.qa_status from report_versions rv "
                "join runs r on r.id = rv.run_id where rv.id = %s for update of r",
                (report_version_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"no report version {report_version_id!r}")

            analyst = canonical_actor(row["analyst_id"])
            if analyst is not None and analyst == canonical_actor(actor_id):
                raise QaSelfReviewError(
                    f"{actor_id!r} is the analyst on this run and may not also record its QA "
                    "result. SIP-188 requires the reviewer to be someone other than the analyst."
                )

            # `Failed` rather than `Fail` because `runs.qa_status` feeds the dashboard's gate
            # display, and the run-state vocabulary in schema.sql already says 'QA Failed'.
            qa_status = "Passed" if result == "Pass" else "Failed"
            conn.execute("update runs set qa_status = %s where id = %s", (qa_status, row["run_id"]))
            record_audit(
                conn,
                user_id=actor_id,
                action="report.qa",
                record_type="runs",
                record_id=str(row["run_id"]),
                old_value=row["qa_status"],
                new_value=qa_status,
                reason=notes,
            )
        return qa_status

    def role_id_for(self, actor_id: str, role_names: tuple[str, ...]) -> int:
        """The actor's enabled role id for the first of `role_names` they actually hold.

        Standalone form of the resolution `submit` performs inside its own transaction. Both go
        through `_role_id_for`, so there is one answer to "which role was this act performed in"
        rather than two that can disagree.
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            return _role_id_for(conn, actor_id, role_names)


def _to_report_version(row: dict) -> ReportVersion:
    return ReportVersion(
        id=str(row["id"]),
        run_id=str(row["run_id"]),
        version_number=row["version_number"],
        created_by=str(row["created_by"]),
        content_sha256=row["content_sha256"],
        created_at=row["created_at"].isoformat(),
        submitted_at=row["submitted_at"].isoformat(),
    )


def _role_id_for(conn: psycopg.Connection, actor_id: str, role_names: tuple[str, ...]) -> int:
    """The actor's enabled role id for the first of `role_names` they hold, on the caller's
    connection.

    `report_versions.created_by_role_id` records the role an act was performed in, and `Principal`
    carries role *names* while the column takes an id. Resolving here rather than in the router
    keeps the database's vocabulary out of the HTTP layer.

    **Ordered, not arbitrary.** The caller passes the roles in precedence order, so a principal
    holding several gets a deterministic answer rather than whichever the database returned first.
    That matters for the steady state after this placement, where one person holds every role and
    an arbitrary pick would make the recorded role meaningless.

    **Takes a connection so the caller can resolve and write in one transaction.** The foreign key
    proves the `user_roles` row exists, not that it is still enabled, so resolving on a separate
    connection leaves a window where a role disabled in between is still recorded as the one the
    act was performed in.
    """
    rows = conn.execute(
        "select r.name, ur.role_id from user_roles ur join roles r on r.id = ur.role_id "
        "where ur.user_id = %s and ur.enabled",
        (actor_id,),
    ).fetchall()
    held = {row["name"]: row["role_id"] for row in rows}
    for name in role_names:
        if name in held:
            return held[name]
    raise DecisionNotPermittedError(f"actor {actor_id!r} holds none of {', '.join(role_names)}")
