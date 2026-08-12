"""`/api/runs` endpoints (#120): create, read, and the four lifecycle commands.

Thin HTTP wrapper over `services/api/persistence.py`'s `RunRepository`, which already carries the
concurrency, legality and human-gate guarantees (#117) and writes the transactional audit row
(#118). This module's job is only to map HTTP <-> that layer: parse the request, call
`apply_transition`, translate the layer's exceptions to the right status code. No state-machine or
audit logic is duplicated here.

**`start` / `pause` / `resume` / `complete` are not free-form transitions** - each names exactly
one edge from `schemas/state-machine.md`, chosen because it is the one HTTP-triggered move in that
edge's position in the run lifecycle (the mechanical steps in between - Coverage Locked, Scanning,
Candidate Review, Report Drafted, QA - are driven by the pipeline/agent loop and the `/api/reports/*`
control endpoints, not this router):
- `start`    Draft -> Run Authorised              (launch authority; run-level gate)
- `pause`    Awaiting CEO Decision -> Paused       (CEO decision; must cite a `decision_records` row)
- `resume`   Paused -> Coverage Locked             (resumption authority; run-level gate)
- `complete` Distributed -> Closed                 (mechanical closeout; not gated)

**No session auth yet.** ADR-0004 specifies an opaque server-side session cookie with CSRF
double-submit; nothing in this repository implements that transport today (`services/api/main.py`
has no auth dependency, and `RunRepository`/`record_audit` already take `actor_id` as a plain
caller-supplied argument, not derived from a session - this router follows that same, already-
decided shape rather than inventing session handling here). `actor_id` is therefore taken directly
from the request body and is **not authenticated by this endpoint**. Tracked as a follow-up, not
silently assumed done.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from apps.sip.core.orchestrator import IllegalTransition
from apps.sip.pipeline.models import RunState
from services.api.auth import ANALYST, REVIEWER, SIP_OWNER, STAFF_READ, Principal
from services.api.persistence import (
    AuditRepository,
    ConcurrentModificationError,
    HumanGateNotSatisfied,
    RunRecord,
    RunRepository,
)
from services.api.session import AUTH_RESPONSES, read_access, write_access

router = APIRouter(prefix="/api/runs", tags=["Runs"], responses=AUTH_RESPONSES)


def get_run_repository() -> RunRepository:
    """FastAPI dependency, overridden in tests (`app.dependency_overrides`) to avoid every route
    test needing a real Postgres - `RunRepository` itself is already covered against one in
    `test_persistence.py`.
    """
    return RunRepository()


class RunOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    run_number: str
    state: str
    version: int
    prompt_version: str
    coverage_start_utc: str
    coverage_end_utc: str
    initiated_by: str


def _run_out(run: RunRecord) -> RunOut:
    return RunOut(
        id=run.id,
        run_number=run.run_number,
        state=run.state.value,
        version=run.version,
        prompt_version=run.prompt_version,
        coverage_start_utc=run.coverage_start_utc,
        coverage_end_utc=run.coverage_end_utc,
        initiated_by=run.initiated_by,
    )


class CreateRunIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_number: str
    prompt_version: str
    coverage_start_utc: str
    coverage_end_utc: str


class TransitionIn(BaseModel):
    """Body shared by all four lifecycle commands. `approval_ref` is optional at the schema level
    because only three of the four transitions are human-gated (`complete` is not) - `RunRepository`
    is still the sole enforcer of which ones actually require it; this model does not duplicate
    that rule.
    """

    model_config = ConfigDict(extra="forbid")

    expected_version: int
    reason: str
    approval_ref: str | None = None


def _not_found(run_id: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"no run {run_id!r}")


@router.post("", response_model=RunOut, status_code=status.HTTP_201_CREATED)
def create_run(
    body: CreateRunIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: RunRepository = Depends(get_run_repository),
) -> RunOut:
    run = repo.create_run(
        run_number=body.run_number,
        prompt_version=body.prompt_version,
        coverage_start_utc=body.coverage_start_utc,
        coverage_end_utc=body.coverage_end_utc,
        initiated_by=principal.user_id,
    )
    return _run_out(run)


@router.get("", response_model=list[RunOut])
def list_runs(
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: RunRepository = Depends(get_run_repository),
) -> list[RunOut]:
    return [_run_out(run) for run in repo.list_runs()]


@router.get("/{run_id}", response_model=RunOut)
def get_run(
    run_id: str,
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: RunRepository = Depends(get_run_repository),
) -> RunOut:
    try:
        return _run_out(repo.get_run(run_id))
    except KeyError as error:
        raise _not_found(run_id) from error


def _apply(
    run_id: str,
    new_state: RunState,
    body: TransitionIn,
    repo: RunRepository,
    principal: Principal,
) -> RunOut:
    """Shared by all four lifecycle routes: call `apply_transition`, translate its exceptions to
    HTTP status codes. `RunRepository` already distinguishes each failure precisely (see its
    docstrings) - this only carries that distinction across the wire, in the same order it checks
    them, so a client sees 404 (unknown run) before 409 (stale version) before 400 (illegal target)
    before 403 (missing authority), matching the layer underneath.
    """
    try:
        run = repo.apply_transition(
            run_id,
            expected_version=body.expected_version,
            new_state=new_state,
            actor_id=principal.user_id,
            reason=body.reason,
            approval_ref=body.approval_ref,
        )
    except KeyError as error:
        raise _not_found(run_id) from error
    except ConcurrentModificationError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(error)) from error
    except IllegalTransition as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except HumanGateNotSatisfied as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    return _run_out(run)


@router.post("/{run_id}/start", response_model=RunOut)
def start_run(
    run_id: str,
    body: TransitionIn,
    principal: Principal = Depends(write_access(SIP_OWNER)),
    repo: RunRepository = Depends(get_run_repository),
) -> RunOut:
    """Draft -> Run Authorised. Launch authority; human gated (run-level, #227)."""
    return _apply(run_id, RunState.RUN_AUTHORISED, body, repo, principal)


@router.post("/{run_id}/pause", response_model=RunOut)
def pause_run(
    run_id: str,
    body: TransitionIn,
    principal: Principal = Depends(write_access(SIP_OWNER)),
    repo: RunRepository = Depends(get_run_repository),
) -> RunOut:
    """Awaiting CEO Decision -> Paused. CEO decision; `approval_ref` must name a
    `decision_records` row.
    """
    return _apply(run_id, RunState.PAUSED, body, repo, principal)


@router.post("/{run_id}/resume", response_model=RunOut)
def resume_run(
    run_id: str,
    body: TransitionIn,
    principal: Principal = Depends(write_access(SIP_OWNER)),
    repo: RunRepository = Depends(get_run_repository),
) -> RunOut:
    """Paused -> Coverage Locked. Resumption authority; human gated (run-level, #227)."""
    return _apply(run_id, RunState.COVERAGE_LOCKED, body, repo, principal)


@router.post("/{run_id}/fail-qa", response_model=RunOut)
def fail_qa(
    run_id: str,
    body: TransitionIn,
    principal: Principal = Depends(write_access(REVIEWER, SIP_OWNER)),
    repo: RunRepository = Depends(get_run_repository),
) -> RunOut:
    """QA in Progress -> QA Failed. The Quality Reviewer's stop.

    REQ-U-01: "A Critical failure blocks progression to the CEO decision." This is that block,
    and it is the reviewer's independent authority: it is the one lifecycle move they can make
    without the SIP Owner, and it prevents a brief they consider unsound from reaching the CEO at
    all. Without this route the reviewer could record findings and still had no way to stop the
    run, which made the QA gate advisory.

    Deliberately not `Stopped`. REQ-U-02 reserves Stop for the CEO decision screen, so a reviewer
    who terminates the run outright would be taking a decision the requirements give to the CEO.
    QA Failed routes back to Report Drafted for correction, which is the documented path.
    """
    return _apply(run_id, RunState.QA_FAILED, body, repo, principal)


@router.post("/{run_id}/stop", response_model=RunOut)
def stop_run(
    run_id: str,
    body: TransitionIn,
    principal: Principal = Depends(write_access(SIP_OWNER)),
    repo: RunRepository = Depends(get_run_repository),
) -> RunOut:
    """Awaiting CEO Decision -> Stopped. Terminal, and the CEO's decision alone.

    REQ-U-02 lists the CEO's four options as Continue, Continue with Correction, Pause and Stop.
    Pause was mounted and Stop was not, so the only terminal refusal in the state machine had no
    way to be exercised: a run the CEO wanted stopped could only be paused, which says something
    different and leaves it resumable.

    `Stopped` has no outbound transitions. Human gated, so `approval_ref` must name the
    `decision_records` row carrying the decision.
    """
    return _apply(run_id, RunState.STOPPED, body, repo, principal)


@router.post("/{run_id}/complete", response_model=RunOut)
def complete_run(
    run_id: str,
    body: TransitionIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: RunRepository = Depends(get_run_repository),
) -> RunOut:
    """Distributed -> Closed. Mechanical closeout; not human gated."""
    return _apply(run_id, RunState.CLOSED, body, repo, principal)


class AuditEntryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    at: str
    user_id: str | None
    action: str
    record_type: str | None
    record_id: str | None
    old_value: str | None
    new_value: str | None
    reason: str | None
    approval_ref: str | None


class AuditPageOut(BaseModel):
    """A page of audit entries plus the cursor for the next one.

    `next_before_id` rather than a page number, so a caller pages by passing back what it was
    given instead of computing an offset. `null` means this is the last page.
    """

    model_config = ConfigDict(extra="forbid")

    entries: list[AuditEntryOut]
    next_before_id: int | None


def get_audit_repository() -> AuditRepository:
    """Overridden in tests, same as `get_run_repository`."""
    return AuditRepository()


@router.get("/{run_id}/audit", response_model=AuditPageOut)
def read_run_audit(
    run_id: str,
    limit: int = Query(100, ge=1, le=500),
    before_id: int | None = Query(None, ge=1),
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: RunRepository = Depends(get_run_repository),
    audit: AuditRepository = Depends(get_audit_repository),
) -> AuditPageOut:
    """The run's audit trail, newest first. Every staff role may read it.

    **Readable by all seven roles deliberately.** An audit trail nobody can read is not an audit
    trail, and the Auditor and Board Viewer roles exist precisely to read it. Restricting it to the
    owner would mean the person most likely to be audited controls who sees the record.

    **404 for an unknown run, not an empty page.** A run with no audit rows cannot exist, because
    `create_run` writes one in the same transaction, so an empty result means the run id is wrong
    and saying so is more useful than returning `[]`. The run is looked up first for that reason.

    Ordered by `id`, so rows written in one transaction keep their real order: `at` is transaction
    start time and would tie.
    """
    try:
        repo.get_run(run_id)
    except KeyError as error:
        raise _not_found(run_id) from error

    entries = audit.for_run(run_id, limit=limit, before_id=before_id)
    # Only offer a cursor when the page was full. A short page is the last one, and handing back a
    # cursor there would invite a request that can only return nothing.
    next_before_id = entries[-1].id if len(entries) == limit else None
    return AuditPageOut(
        entries=[AuditEntryOut(**vars(entry)) for entry in entries],
        next_before_id=next_before_id,
    )
