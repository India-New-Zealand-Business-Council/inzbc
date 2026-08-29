"""`/api/reports` endpoints (#124): submit a report version, and read it with its decisions.

Thin HTTP wrapper over `ReportRepository` and `DecisionRepository`, the same split every other
router here uses.

**Submitting is what makes a report decidable.** A trigger on `report_versions` opens the CEO
Ruling, Report Approval and Distribution Authority streams, so the three decisions a report needs
exist from the moment it is submitted and none of them can arrive for a stream nobody opened.

**Reading returns the version and its current decisions together, with the revisions.** A reviewer
cannot act on a version without knowing what has already been decided about it, and a caller that
later records a decision has to pass back the revision it read. Two calls would let a decision
commit in between, which is exactly the race `DecisionRepository.current` exists to close, so
splitting them here would reopen it one layer up.

**The three decision-writing endpoints are now mounted.** `/ruling`, `/approval` and
`/distribution` were specified in `schemas/api-contract.md` and deliberately absent while
`decision_role_permissions` was unseeded, because no row means nobody may act and the repository
refuses every decision by design. Migration `0003` seeds that table (#348), so they answer for
real rather than 403 by construction. Who may record which kind is data, not code: revoking a
grant is `enabled = false`, and `record()` checks it on every call.

**They stay three commands, not one.** REQ-U-02 requires distribution authority to be captured as
a separate act, and ADR-0005 records the three as independent immutable streams each with its own
actor and timestamp. One endpoint writing two of them cannot satisfy that, however many rows it
writes. Do not reintroduce `/decision`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.api.auth import (
    ANALYST,
    REVIEWER,
    SECRETARIAT,
    SIP_OWNER,
    STAFF_READ,
    Principal,
)
from services.api.decisions import (
    CEO_RULING,
    DISTRIBUTION_AUTHORITY,
    REPORT_APPROVAL,
    CurrentDecisions,
    DecisionConflictError,
    DecisionNotPermittedError,
    DecisionRecord,
    DecisionRejected,
    DecisionRepository,
    QaSelfReviewError,
    ReportRepository,
    ReportVersion,
    ReportVersionConflict,
)
from services.api.session import AUTH_RESPONSES, read_access, write_access

router = APIRouter(prefix="/api/reports", tags=["Reports"], responses=AUTH_RESPONSES)

# Precedence for the role a submission is recorded under, highest first. A principal holding both
# is recorded as Analyst, because drafting the report is the analyst's act; owning the run does not
# make the owner its author. Ordered rather than arbitrary so the recorded role still means
# something when one person holds every role.
_SUBMIT_ROLES = (ANALYST, SIP_OWNER)

# Which role each decision kind is recorded under, in precedence order, matching the grants
# migration 0003 seeds. The role check inside `record()` is the authority; these tuples only decide
# which of several held roles the act is *recorded* as, which matters precisely because the steady
# state here is one person holding every role.
_RULING_ROLES = (SIP_OWNER,)
_APPROVAL_ROLES = (REVIEWER, SIP_OWNER)
_DISTRIBUTION_ROLES = (SECRETARIAT, SIP_OWNER)

# Absorbs ordinary clock skew between a caller and this service. Wide enough that a
# correct request is never refused for being a few seconds ahead, narrow enough that a
# genuinely future timestamp still is.
_CLOCK_SKEW_ALLOWANCE = timedelta(minutes=5)


def get_report_repository() -> ReportRepository:
    """Overridden in tests, matching the other routers."""
    return ReportRepository()


def get_decision_repository() -> DecisionRepository:
    return DecisionRepository()


class SubmitReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    # The content hash, not the content. This service records that a version was submitted and
    # what it hashed to; the brief itself lives where it was drafted. A hash is what makes "the
    # thing approved is the thing distributed" checkable without this table holding the report.
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def _not_in_the_future(cls, value: datetime) -> datetime:
        """`submitted_at >= created_at` is a database CHECK, and reaching it costs a 500.

        The database is still the boundary; this is about which answer the caller gets. A
        `created_at` after the submission means the content was produced after it was handed over,
        which did not happen, and a 422 naming the field says that where a constraint violation
        does not.

        Compared against the server's clock, because `submitted_at` defaults to the server's clock
        and comparing the caller's timestamp to the caller's idea of now would check nothing. A
        small tolerance absorbs ordinary clock skew rather than refusing a request that is right.
        """
        if value.tzinfo is None:
            raise ValueError("created_at must carry a timezone")
        if value > datetime.now(UTC) + _CLOCK_SKEW_ALLOWANCE:
            raise ValueError("created_at is in the future; content cannot predate its own creation")
        return value


class ReportVersionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    run_id: str
    version_number: int
    created_by: str
    content_sha256: str
    created_at: str
    submitted_at: str


class DecisionsOut(BaseModel):
    """The current decision on each stream, plus the revision each was read at.

    A `null` value means undecided *after submission*, which is a different fact from an explicit
    refusal: `Not Authorised` is a decision, `null` is the absence of one. Keeping them distinct is
    the whole reason the mutable approvals row was replaced.

    `revisions` is not decoration. A caller recording a decision passes back the revision it read,
    and that is what makes a decision built on a superseded ruling detectable.
    """

    model_config = ConfigDict(extra="forbid")

    ceo_ruling: str | None
    report_approval: str | None
    distribution_authority: str | None
    distribution_recipient: str | None
    revisions: dict[str, int]


class ReportOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report: ReportVersionOut
    decisions: DecisionsOut


def _version_out(version: ReportVersion) -> ReportVersionOut:
    return ReportVersionOut(**vars(version))


def _decisions_out(decisions: CurrentDecisions) -> DecisionsOut:
    return DecisionsOut(
        ceo_ruling=decisions.ceo_ruling,
        report_approval=decisions.report_approval,
        distribution_authority=decisions.distribution_authority,
        distribution_recipient=decisions.distribution_recipient,
        revisions=decisions.revisions,
    )


class RecordQaIn(BaseModel):
    """A SIP-188 QA result. `Pass`/`Fail` and a Critical count is exactly what the checklist's own
    result block collects, so the request carries that and not a richer shape nobody fills in.
    """

    model_config = ConfigDict(extra="forbid")

    result: Literal["Pass", "Fail"]
    # Counted rather than listed: SIP-188 records "Critical failures found" as a number, and a
    # list here would invite a per-finding table that does not exist yet.
    critical_failures: int = Field(default=0, ge=0)
    notes: str = Field(min_length=1, max_length=2000)


class QaResultOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_version_id: str
    # `Passed`/`Failed`, matching `runs.qa_status` and the run-state vocabulary, rather than
    # echoing the request's `Pass`/`Fail` back and leaving two spellings in circulation.
    qa_status: str
    critical_failures: int


@router.post("", response_model=ReportVersionOut, status_code=status.HTTP_201_CREATED)
def submit_report(
    body: SubmitReportIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: ReportRepository = Depends(get_report_repository),
) -> ReportVersionOut:
    """Submits the next version of a run's report.

    The version number is assigned by the database, not by the caller. A caller-supplied number
    would be a second opinion about the sequence, and the one that disagreed would win.

    **409 on a concurrent submission**, not 500. Two submissions racing for the same version number
    is a retry, and saying so is the difference between a caller that recovers and one that gives
    up.
    """
    # One call, so the role is resolved in the same transaction as the insert. Resolving first and
    # writing after left a window where a role disabled in between was still recorded as the one
    # the act was performed in, because the foreign key proves the assignment exists rather than
    # that it is still enabled.
    try:
        version = repo.submit(
            run_id=body.run_id,
            content_sha256=body.content_sha256,
            actor_id=principal.user_id,
            role_names=_SUBMIT_ROLES,
            created_at=body.created_at,
        )
    except DecisionNotPermittedError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except ReportVersionConflict as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(error)) from error
    return _version_out(version)


@router.post("/{report_version_id}/qa", response_model=QaResultOut)
def record_qa(
    report_version_id: str,
    body: RecordQaIn,
    principal: Principal = Depends(write_access(REVIEWER, SIP_OWNER)),
    repo: ReportRepository = Depends(get_report_repository),
) -> QaResultOut:
    """Records the SIP-188 QA result for the run this report version belongs to.

    Writes `runs.qa_status`, the field `GET /api/dashboard` already reports, so the gate a
    reviewer sees is the one this wrote. There is deliberately no second QA table: ADR-0005's
    release predicate wants "no open Critical QA failure" and a durable per-finding table is the
    follow-up recorded in `schemas/api-contract.md`. This endpoint records the checklist's own
    output, which is a Pass or a Fail with a count, and does not pretend to more granularity than
    SIP-188 collects.

    **Reviewer or SIP Owner only, and never the run's analyst.** The role check says the actor may
    record a QA result at all; `record_qa` separately refuses the analyst on that particular run.
    Two gates, same split as `/api/candidates/{id}/verify`, because holding Reviewer does not make
    checking your own run someone else's check.

    **This is not `POST /api/runs/{run_id}/fail-qa`, and neither replaces the other.** That route
    moves the run's lifecycle state to `QA Failed`; this one records what the checklist found.
    Recording a Fail here deliberately does not move the run, because the transition carries its
    own guards and an optimistic-concurrency version the caller has to pass, and firing it as a
    side effect would take a lifecycle decision out of the reviewer's hands and skip that check.
    The reviewer records the result, then stops the run. Two acts, because they are two acts.
    """
    try:
        qa_status = repo.record_qa(
            report_version_id,
            result=body.result,
            critical_failures=body.critical_failures,
            actor_id=principal.user_id,
            notes=body.notes,
        )
    except KeyError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"no report version {report_version_id!r}"
        ) from error
    except QaSelfReviewError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return QaResultOut(
        report_version_id=report_version_id,
        qa_status=qa_status,
        critical_failures=body.critical_failures,
    )


@router.get("/{report_version_id}", response_model=ReportOut)
def read_report(
    report_version_id: str,
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: ReportRepository = Depends(get_report_repository),
    decisions: DecisionRepository = Depends(get_decision_repository),
) -> ReportOut:
    """A report version and everything currently decided about it.

    Every staff role may read it, for the same reason every staff role may read the audit trail: a
    record only the decider can see is not evidence anyone else can rely on.
    """
    try:
        version = repo.get(report_version_id)
    except KeyError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"no report version {report_version_id!r}"
        ) from error

    # Caught separately, because the two `KeyError`s mean different things and one 404 for both
    # would send a reader looking for a typo. `current_report_decisions` inner-joins all three
    # streams, so a version missing any of them drops out of the view entirely while still
    # existing in `report_versions`. The trigger opens all three on insert, so this should be
    # unreachable; if it ever happens the trigger is gone, and saying that is more useful than
    # claiming the version does not exist.
    try:
        current = decisions.current(report_version_id)
    except KeyError as error:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"report version {report_version_id!r} exists but has no decision streams. "
                "They are opened by a trigger on insert, so this means the trigger is missing."
            ),
        ) from error

    return ReportOut(report=_version_out(version), decisions=_decisions_out(current))


class _DecisionIn(BaseModel):
    """Fields every decision carries, whichever stream it lands on.

    `expected_head_revision` is the revision the caller read from `GET /api/reports/{id}`. It is
    not bookkeeping: it is the caller asserting "I read this stream at this point and I am deciding
    in response to what it said". Without it a correction can supersede a ruling nobody ever saw.

    `idempotency_key` is caller-supplied because only the caller knows whether a retry is the same
    act or a second one. A server-generated key would make every retry a new decision.
    """

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=2000)
    evidence_ref: str = Field(min_length=1, max_length=500)
    owner_id: str
    next_review: date
    decided_at: datetime
    idempotency_key: UUID
    expected_head_revision: int = Field(ge=0)
    # Empty list rather than None: a decision recorded with no conditions has zero conditions,
    # which is a fact, not an absence of information. Defaulting to None made every reader do a
    # null check to express the same thing, and left "conditions were not supplied" and "there
    # were no conditions" indistinguishable in the stored record.
    conditions: list[str] = Field(default_factory=list)
    # Only ever set when one person legitimately holds both sides of the act. Absent means no
    # exception is claimed, and `record()` refuses a self-decision without one.
    sod_exception_id: str | None = None

    @field_validator("decided_at")
    @classmethod
    def _not_in_the_future(cls, value: datetime) -> datetime:
        """A decision cannot have been taken later than now, for the same reason `created_at`
        cannot: the record would say something that has not happened.
        """
        if value.tzinfo is None:
            raise ValueError("decided_at must carry a timezone")
        if value > datetime.now(UTC) + _CLOCK_SKEW_ALLOWANCE:
            raise ValueError("decided_at is in the future")
        return value


class RulingIn(_DecisionIn):
    value: Literal["Continue", "Continue With Correction", "Pause", "Stop"]


class ApprovalIn(_DecisionIn):
    # Three values, not two. `Returned for Correction` is a distinct outcome from `Rejected`, and
    # `schemas/api-contract.md` notes that a two-value endpoint could not express it.
    value: Literal["Approved", "Rejected", "Returned for Correction"]


class DistributionIn(_DecisionIn):
    value: Literal["Authorised", "Not Authorised"]
    # Required on an Authorised decision and refused on a refusal, checked below rather than by
    # type: a recipient recorded against `Not Authorised` would read as though a send was intended.
    distribution_recipient: str | None = Field(default=None, max_length=500)


class DecisionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Mirrors DecisionRecord's own field names rather than renaming them at the boundary. The
    # earlier shape dropped `actor_id` and `stream_id` and renamed `stream_revision` to
    # `head_revision`, which cost a client the two things a decision record is for: who decided,
    # and which stream and revision it belongs to. A caller reading a decision back to display or
    # audit it needs the decider's identity; omitting it makes the response a receipt rather than
    # a record. Renaming the revision also meant a client could not use the value it read as the
    # `expected_head_revision` of its next write without knowing about the rename.
    id: str
    stream_id: str
    report_version_id: str
    kind: str
    stream_revision: int
    value: str
    actor_id: str
    decided_at: str
    reason: str


def _decision_out(record: DecisionRecord) -> DecisionOut:
    return DecisionOut(
        id=record.id,
        stream_id=record.stream_id,
        report_version_id=record.report_version_id,
        kind=record.kind,
        stream_revision=record.stream_revision,
        value=record.value,
        actor_id=record.actor_id,
        # `decided_at` is already a string on the record. Calling `.isoformat()` on it raised
        # AttributeError, and the old `head_revision=record.head_revision` named a field that does
        # not exist — so every *successful* decision failed on the way out and only the refusal
        # paths had ever been exercised.
        decided_at=record.decided_at,
        reason=record.reason,
    )


def _record_decision(
    *,
    report_version_id: str,
    kind: str,
    body: _DecisionIn,
    value: str,
    role_names: tuple[str, ...],
    principal: Principal,
    reports: ReportRepository,
    decisions: DecisionRepository,
    distribution_recipient: str | None = None,
) -> DecisionOut:
    """Shared body for the three decision endpoints.

    They differ only in which stream they write and which roles may write it, so the error mapping
    lives once. Three copies of this would be three places for the 403/409/422 split to drift.

    **The role is resolved before the write, on a separate connection.** `record()` takes an
    `actor_role_id` rather than resolving it, so there is a window where a role disabled between
    resolution and write is still recorded as the one the act was performed in. `record()` re-checks
    the grant, the assignment and the account inside its own transaction, so a revoked permission
    still refuses; what can go stale is only *which* of several held roles gets recorded. Narrowing
    that further means moving resolution inside `record()`, which is a change to that method rather
    than to this router.
    """
    try:
        actor_role_id = reports.role_id_for(principal.user_id, role_names)
    except (LookupError, DecisionNotPermittedError) as error:
        # Both, because role resolution refuses in two different ways and only one of them was
        # caught. `_role_id_for` raises DecisionNotPermittedError - a RuntimeError, not a
        # LookupError - when the actor holds none of the required roles, so that case escaped as
        # a 500 rather than the 403 it is. That is the ordinary refusal this endpoint exists to
        # make, and it is the most likely path while role accounts are still being set up.
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error

    try:
        record = decisions.record(
            report_version_id=report_version_id,
            kind=kind,
            value=value,
            actor_id=principal.user_id,
            actor_role_id=actor_role_id,
            reason=body.reason,
            evidence_ref=body.evidence_ref,
            owner_id=body.owner_id,
            next_review=body.next_review,
            decided_at=body.decided_at,
            idempotency_key=body.idempotency_key,
            expected_head_revision=body.expected_head_revision,
            distribution_recipient=distribution_recipient,
            sod_exception_id=body.sod_exception_id,
            conditions=body.conditions,
        )
    except KeyError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"no report version {report_version_id!r}"
        ) from error
    except DecisionNotPermittedError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    # 409, not 422: the caller's request was well formed and lost a race, which is a retry after
    # re-reading rather than a request to correct.
    except DecisionConflictError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(error)) from error
    except DecisionRejected as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return _decision_out(record)


@router.post("/{report_version_id}/ruling", response_model=DecisionOut, status_code=201)
def record_ruling(
    report_version_id: str,
    body: RulingIn,
    principal: Principal = Depends(write_access(SIP_OWNER)),
    reports: ReportRepository = Depends(get_report_repository),
    decisions: DecisionRepository = Depends(get_decision_repository),
) -> DecisionOut:
    """Records the CEO ruling on a report version.

    SIP Owner only. This is the run-level ruling SIP-050 section 26 puts with the CEO, and it is
    separate from approving the report: a `Continue` here does not approve anything, and an
    `Approved` there does not authorise a send.
    """
    return _record_decision(
        report_version_id=report_version_id, kind=CEO_RULING, body=body, value=body.value,
        role_names=_RULING_ROLES, principal=principal, reports=reports, decisions=decisions,
    )


@router.post("/{report_version_id}/approval", response_model=DecisionOut, status_code=201)
def record_approval(
    report_version_id: str,
    body: ApprovalIn,
    principal: Principal = Depends(write_access(REVIEWER, SIP_OWNER)),
    reports: ReportRepository = Depends(get_report_repository),
    decisions: DecisionRepository = Depends(get_decision_repository),
) -> DecisionOut:
    """Records the report-approval decision.

    Reviewer or SIP Owner. `record()` separately refuses whoever authored the version being decided
    on, so holding the role is necessary and not sufficient. That refusal is the control this
    record exists to evidence.
    """
    return _record_decision(
        report_version_id=report_version_id, kind=REPORT_APPROVAL, body=body, value=body.value,
        role_names=_APPROVAL_ROLES, principal=principal, reports=reports, decisions=decisions,
    )


@router.post("/{report_version_id}/distribution", response_model=DecisionOut, status_code=201)
def record_distribution(
    report_version_id: str,
    body: DistributionIn,
    principal: Principal = Depends(write_access(SECRETARIAT, SIP_OWNER)),
    reports: ReportRepository = Depends(get_report_repository),
    decisions: DecisionRepository = Depends(get_decision_repository),
) -> DecisionOut:
    """Records distribution authority, separately from report approval.

    **`Not Authorised` is a decision, not a failure.** It does not stop the run: the send is
    skipped and the run reaches close-out as approved but not distributed. That is why an absent
    decision and an explicit refusal have to stay distinguishable, and why this endpoint exists
    rather than a boolean on the approval.
    """
    if body.value == "Authorised" and not body.distribution_recipient:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="an Authorised distribution must name its recipient; authorising a send to "
                   "nobody in particular is not an authorisation anyone can audit",
        )
    if body.value == "Not Authorised" and not body.distribution_recipient:
        # This rule was inverted, and the inversion made an explicit refusal impossible to record
        # at all: with a recipient the route refused it, without one the database check constraint
        # refused it, so both request shapes returned 422 and `Not Authorised` could never be
        # written. An unrecordable refusal is indistinguishable from an undecided stream, which
        # defeats the distinction the whole append-only decision model exists to preserve.
        #
        # The schema is the side that was right (`database/schema.sql`, the Distribution Authority
        # check): "Both Yes and No are decisions about a concrete requested recipient." Refusing to
        # send to a named recipient is a more useful record than refusing in the abstract — it says
        # what was proposed as well as what was decided. Found by adversarial review.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="a Not Authorised decision must still name the recipient it refuses; "
                   "'we did not authorise sending to X' is the record, and a refusal naming "
                   "nobody does not say what was declined",
        )
    return _record_decision(
        report_version_id=report_version_id, kind=DISTRIBUTION_AUTHORITY, body=body,
        value=body.value, role_names=_DISTRIBUTION_ROLES, principal=principal, reports=reports,
        decisions=decisions, distribution_recipient=body.distribution_recipient,
    )
