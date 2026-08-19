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

**The decision-writing endpoints are deliberately absent.** `/approval`, `/ruling` and
`/distribution` are specified in `schemas/api-contract.md` and are not mounted, because
`decision_role_permissions` is unseeded: no row means nobody may act, so `DecisionRepository.record`
refuses every decision by design. Mounting them now would ship three endpoints that answer 403
until INZBC decides who may approve what, which is a client decision (ADR-0005 required follow-up
4, client answers B8) rather than an engineering one. Recorded in the issue rather than hidden
behind an endpoint that looks built.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.api.auth import ANALYST, SIP_OWNER, STAFF_READ, Principal
from services.api.decisions import (
    CurrentDecisions,
    DecisionNotPermittedError,
    DecisionRepository,
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
