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

**The decision-writing endpoints now mount, per client answers B8 (#348).** `/approval`, `/ruling`
and `/distribution` were specified in `schemas/api-contract.md` and deliberately left absent while
`decision_role_permissions` was unseeded, because a route that only answers 403 looks built when it
is not. The client's account model (one account per role, one person holding every role during the
placement) is enough to seed the table, so the route now exists; whether any given call succeeds
still depends entirely on that seed data, which lives in the database, not in this file. An
unseeded environment gets 403 on every call here, correctly, same as before this commit.

**Each endpoint records exactly one decision stream, never two.** ADR-0005 keeps CEO Ruling, Report
Approval and Distribution Authority independent so approving a report is never mistaken for
authorising its distribution. `owner_id` names who owns the follow-up on a decision, not who typed
it, and is a real `users.id` — this router has no user-directory to pick one from yet, so a caller
that wants someone other than themselves recorded as owner has to already know that person's id.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.api.auth import ANALYST, REVIEWER, SIP_OWNER, STAFF_READ, Principal
from services.api.decisions import (
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

# Coarse gate for the three decision endpoints: broad enough that nobody eligible under any
# plausible decision_role_permissions row is refused before reaching it, narrow enough to exclude
# the purely-oversight roles (Board Viewer, Auditor) that were never going to record a decision.
# The real, fine-grained authority is decision_role_permissions itself, checked per (kind, role)
# inside DecisionRepository.record — this only stops an obviously wrong role from attempting at
# all, the same relationship record_qa's coarse Reviewer/SIP Owner gate has to its own narrower
# self-review check.
#
# Precedence order for which role gets *recorded* when a principal holds more than one: SIP Owner
# first, since these acts are specified as the CEO's (docs/sip-ui-spec.md Screen 3) and SIP Owner
# is the role that represents that authority while the client's account model has one person
# holding several roles. Ties resolve the same deterministic way ReportRepository.submit's own
# role resolution does.
_DECISION_ROLES = (SIP_OWNER, REVIEWER, ANALYST)

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


class DecisionIn(BaseModel):
    """Fields every decision stream needs, shared by all three endpoints below. `value` is not
    here: each endpoint fixes its own `Literal` set, because `decision_value` is one enum shared
    across three streams and the schema does not stop a caller sending a ruling word to `/approval`
    — the endpoint boundary is what does.
    """

    model_config = ConfigDict(extra="forbid")

    # The revision this decision responds to, read from GET /api/reports/:id's `decisions.revisions`
    # first. Passing the wrong one is exactly the race DecisionRepository.record's compare-and-swap
    # exists to catch, not a formality this router could relax.
    expected_head_revision: int = Field(ge=0)
    reason: str = Field(min_length=1)
    conditions: list[str] = Field(default_factory=list)
    owner_id: str
    evidence_ref: str = Field(min_length=1)
    next_review: date
    decided_at: datetime
    sod_exception_id: str | None = None

    @field_validator("decided_at")
    @classmethod
    def _decided_at_has_a_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("decided_at must carry a timezone")
        return value


class RulingIn(DecisionIn):
    value: Literal["Continue", "Continue With Correction", "Pause", "Stop"]


class ApprovalIn(DecisionIn):
    value: Literal["Approved", "Rejected", "Returned for Correction"]


class DistributionIn(DecisionIn):
    value: Literal["Authorised", "Not Authorised"]
    # Only this stream carries a recipient — a ruling or an approval names no one to send to.
    distribution_recipient: str | None = None


class DecisionRecordOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    stream_id: str
    report_version_id: str
    kind: str
    stream_revision: int
    value: str
    actor_id: str
    decided_at: str
    reason: str


def _decision_out(record: DecisionRecord) -> DecisionRecordOut:
    return DecisionRecordOut(**vars(record))


def _record_decision(
    report_version_id: str,
    kind: str,
    value: str,
    body: DecisionIn,
    principal: Principal,
    reports: ReportRepository,
    decisions: DecisionRepository,
) -> DecisionRecordOut:
    """Shared by `/ruling`, `/approval` and `/distribution` — same repository call, same exception
    mapping, different `kind`/`value` and (for distribution only) `distribution_recipient`.

    **Not an idempotency key a caller controls.** `decision_records.idempotency_key` is `unique`,
    which is what turns two racing identical-looking inserts into one detectable conflict rather
    than two silent decisions — but nothing here yet lets a caller retry a timed-out request under
    the same key and get its original result back instead of a second row. Generated fresh per call
    until that's asked for.
    """
    try:
        role_id = reports.role_id_for(principal.user_id, _DECISION_ROLES)
    except DecisionNotPermittedError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error

    try:
        record = decisions.record(
            report_version_id=report_version_id,
            kind=kind,
            value=value,
            actor_id=principal.user_id,
            actor_role_id=role_id,
            reason=body.reason,
            evidence_ref=body.evidence_ref,
            owner_id=body.owner_id,
            next_review=body.next_review,
            decided_at=body.decided_at,
            idempotency_key=uuid.uuid4(),
            expected_head_revision=body.expected_head_revision,
            distribution_recipient=getattr(body, "distribution_recipient", None),
            sod_exception_id=body.sod_exception_id,
            conditions=body.conditions,
        )
    except KeyError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"no report version {report_version_id!r}"
        ) from error
    except DecisionNotPermittedError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except DecisionConflictError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(error)) from error
    except DecisionRejected as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return _decision_out(record)


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


@router.post("/{report_version_id}/ruling", response_model=DecisionRecordOut)
def record_ruling(
    report_version_id: str,
    body: RulingIn,
    principal: Principal = Depends(write_access(*_DECISION_ROLES)),
    reports: ReportRepository = Depends(get_report_repository),
    decisions: DecisionRepository = Depends(get_decision_repository),
) -> DecisionRecordOut:
    """Records the CEO's ruling on a report version: Continue, Continue With Correction, Pause or
    Stop. Independent of report approval and distribution authority — see the module docstring.
    """
    return _record_decision(
        report_version_id, "CEO Ruling", body.value, body, principal, reports, decisions
    )


@router.post("/{report_version_id}/approval", response_model=DecisionRecordOut)
def record_approval(
    report_version_id: str,
    body: ApprovalIn,
    principal: Principal = Depends(write_access(*_DECISION_ROLES)),
    reports: ReportRepository = Depends(get_report_repository),
    decisions: DecisionRepository = Depends(get_decision_repository),
) -> DecisionRecordOut:
    """Records the report-approval decision: Approved, Rejected or Returned for Correction."""
    return _record_decision(
        report_version_id, "Report Approval", body.value, body, principal, reports, decisions
    )


@router.post("/{report_version_id}/distribution", response_model=DecisionRecordOut)
def record_distribution(
    report_version_id: str,
    body: DistributionIn,
    principal: Principal = Depends(write_access(*_DECISION_ROLES)),
    reports: ReportRepository = Depends(get_report_repository),
    decisions: DecisionRepository = Depends(get_decision_repository),
) -> DecisionRecordOut:
    """Records distribution authority: Authorised or Not Authorised.

    **Not Authorised does not stop the run.** It is a complete, valid outcome — the send is
    skipped and the run reaches close-out as approved but not distributed
    (`docs/sip/operator-guide.md`) — not a refusal that blocks progress.
    """
    return _record_decision(
        report_version_id, "Distribution Authority", body.value, body, principal, reports, decisions
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
