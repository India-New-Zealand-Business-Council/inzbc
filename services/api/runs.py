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

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from apps.sip.core.orchestrator import IllegalTransition
from apps.sip.pipeline.models import RunState
from services.api.auth import ANALYST, SIP_OWNER, STAFF_READ, Principal
from services.api.persistence import (
    ConcurrentModificationError,
    HumanGateNotSatisfied,
    RunRecord,
    RunRepository,
)
from services.api.session import read_access, write_access

router = APIRouter(prefix="/api/runs", tags=["Runs"])


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


@router.post("/{run_id}/complete", response_model=RunOut)
def complete_run(
    run_id: str,
    body: TransitionIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: RunRepository = Depends(get_run_repository),
) -> RunOut:
    """Distributed -> Closed. Mechanical closeout; not human gated."""
    return _apply(run_id, RunState.CLOSED, body, repo, principal)
