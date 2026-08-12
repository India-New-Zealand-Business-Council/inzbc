"""`/api/candidates` endpoints (#121): capture, list, get, and the four decision commands.

Thin HTTP wrapper over `services/api/candidate_persistence.py`'s `CandidateRepository` - see that
module's docstring for why these are explicit commands rather than a blanket PATCH, and for the
verification-gate contract each of `verify`/`score` enforces.

**Wire shapes for `verify`/`score`/`route`/`merge` are not specified anywhere** -
`schemas/api-contract.md` names the four routes but not their bodies. Designed here as the
smallest request each command needs, built from fields `Candidate`/`CandidateAssessment`
(`apps/sip/pipeline/models.py`) already settled - not new business rules, just which existing,
already-decided fields each command carries. Flagged rather than assumed final; `SipPipelineClient`
(`apps/sip/pipeline/client.py`) already has methods for all four (`verify_candidate`,
`score_candidate`, `route_candidate`, `merge_candidate`) that were unused until now, so this is the
first place their payload shape gets decided.

Same `actor_id`-in-body caveat as `services/api/runs.py` (#120): no session auth exists yet:
caller-supplied, not authenticated by this endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from apps.sip.collector.verification import UnverifiedHighSignalError
from apps.sip.pipeline.models import SignalStrength, SourceConfidence, VerificationState
from services.api.auth import ANALYST, REVIEWER, SIP_OWNER, STAFF_READ, Principal
from services.api.candidate_persistence import (
    CandidateRecord,
    CandidateRepository,
    SelfVerificationError,
)
from services.api.session import AUTH_RESPONSES, read_access, write_access

router = APIRouter(prefix="/api/candidates", tags=["Candidates"], responses=AUTH_RESPONSES)


def get_candidate_repository() -> CandidateRepository:
    """FastAPI dependency, overridden in tests - same reasoning as `services/api/runs.py`'s
    `get_run_repository`.
    """
    return CandidateRepository()


class CandidateOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    run_id: str
    headline: str
    source_id: str | None
    url: str | None
    summary: str | None
    published_at: str | None
    captured_at: str
    in_coverage_window: bool | None
    nz_relevance: int | None
    india_relevance: int | None
    member_relevance: int | None
    signal: str | None
    confidence: str | None
    verification: str
    duplicate_of: str | None
    included: bool | None
    reason: str | None
    proposed_routing: str | None


def _candidate_out(candidate: CandidateRecord) -> CandidateOut:
    return CandidateOut(
        id=candidate.id,
        run_id=candidate.run_id,
        headline=candidate.headline,
        source_id=candidate.source_id,
        url=candidate.url,
        summary=candidate.summary,
        published_at=candidate.published_at,
        captured_at=candidate.captured_at,
        in_coverage_window=candidate.in_coverage_window,
        nz_relevance=candidate.nz_relevance,
        india_relevance=candidate.india_relevance,
        member_relevance=candidate.member_relevance,
        signal=candidate.signal.value if candidate.signal else None,
        confidence=candidate.confidence.value if candidate.confidence else None,
        verification=candidate.verification.value,
        duplicate_of=candidate.duplicate_of,
        included=candidate.included,
        reason=candidate.reason,
        proposed_routing=candidate.proposed_routing,
    )


class CaptureCandidateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    headline: str
    source_id: str | None = None
    url: str | None = None
    summary: str | None = None
    published_at: str | None = None
    in_coverage_window: bool | None = None


class VerifyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verification: VerificationState
    reason: str
    # Cited only when the verifier captured or assessed this candidate. INZBC is one person
    # holding every role, so that is the normal case rather than the exceptional one, and the
    # exception is recorded rather than the control being disabled.
    sod_exception_id: str | None = None


class ScoreIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nz_relevance: int | None = None
    india_relevance: int | None = None
    member_relevance: int | None = None
    signal: SignalStrength | None = None
    confidence: SourceConfidence | None = None
    reason: str


class RouteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposed_routing: str | None = None
    included: bool | None = None
    reason: str


class MergeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    duplicate_of: str
    reason: str


def _not_found(candidate_id: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"no candidate {candidate_id!r}")


@router.post("", response_model=CandidateOut, status_code=status.HTTP_201_CREATED)
def capture_candidate(
    body: CaptureCandidateIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: CandidateRepository = Depends(get_candidate_repository),
) -> CandidateOut:
    candidate = repo.capture(
        run_id=body.run_id,
        headline=body.headline,
        source_id=body.source_id,
        url=body.url,
        summary=body.summary,
        published_at=body.published_at,
        in_coverage_window=body.in_coverage_window,
        actor_id=principal.user_id,
    )
    return _candidate_out(candidate)


@router.get("", response_model=list[CandidateOut])
def list_candidates(
    run: str = Query(..., description="Run id to list candidates for."),
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: CandidateRepository = Depends(get_candidate_repository),
) -> list[CandidateOut]:
    return [_candidate_out(c) for c in repo.list_for_run(run)]


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(
    candidate_id: str,
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: CandidateRepository = Depends(get_candidate_repository),
) -> CandidateOut:
    try:
        return _candidate_out(repo.get(candidate_id))
    except KeyError as error:
        raise _not_found(candidate_id) from error


@router.post("/{candidate_id}/verify", response_model=CandidateOut)
def verify_candidate(
    candidate_id: str,
    body: VerifyIn,
    principal: Principal = Depends(write_access(REVIEWER, SIP_OWNER)),
    repo: CandidateRepository = Depends(get_candidate_repository),
) -> CandidateOut:
    try:
        candidate = repo.record_verification(
            candidate_id,
            body.verification,
            actor_id=principal.user_id,
            reason=body.reason,
            sod_exception_id=body.sod_exception_id,
        )
    except KeyError as error:
        raise _not_found(candidate_id) from error
    except SelfVerificationError as error:
        # 403 like the other refusals, but a distinct message: the caller is permitted to verify
        # in general and refused for this candidate specifically.
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except UnverifiedHighSignalError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    return _candidate_out(candidate)


@router.post("/{candidate_id}/score", response_model=CandidateOut)
def score_candidate(
    candidate_id: str,
    body: ScoreIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: CandidateRepository = Depends(get_candidate_repository),
) -> CandidateOut:
    try:
        candidate = repo.record_score(
            candidate_id,
            nz_relevance=body.nz_relevance,
            india_relevance=body.india_relevance,
            member_relevance=body.member_relevance,
            signal=body.signal,
            confidence=body.confidence,
            actor_id=principal.user_id,
            reason=body.reason,
        )
    except KeyError as error:
        raise _not_found(candidate_id) from error
    except UnverifiedHighSignalError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    return _candidate_out(candidate)


@router.post("/{candidate_id}/route", response_model=CandidateOut)
def route_candidate(
    candidate_id: str,
    body: RouteIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: CandidateRepository = Depends(get_candidate_repository),
) -> CandidateOut:
    try:
        candidate = repo.record_routing(
            candidate_id,
            proposed_routing=body.proposed_routing,
            included=body.included,
            actor_id=principal.user_id,
            reason=body.reason,
        )
    except KeyError as error:
        raise _not_found(candidate_id) from error
    return _candidate_out(candidate)


@router.post("/{candidate_id}/merge", response_model=CandidateOut)
def merge_candidate(
    candidate_id: str,
    body: MergeIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: CandidateRepository = Depends(get_candidate_repository),
) -> CandidateOut:
    try:
        candidate = repo.merge(
            candidate_id, body.duplicate_of, actor_id=principal.user_id, reason=body.reason
        )
    except KeyError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return _candidate_out(candidate)
