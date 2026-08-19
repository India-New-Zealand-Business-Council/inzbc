"""`/api/facts` (#188).

Thin HTTP wrapper over `services/api/facts_persistence.py` - see that module's docstring for the
draft/approve/archive lifecycle and the supersedes-chain versioning.

Drafting a fact is capture (Analyst), the same reasoning PR #264's authority table applied to
`source-checks` writes. Approving is verification, so it needs Reviewer or SIP Owner - never
Analyst alone, since the repository already refuses an actor approving their own draft and the
route-level role split is the second, independent layer of that same rule. Archiving retires a
fact rather than asserting a new claim, so any writer role may do it.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from services.api.auth import ANALYST, REVIEWER, SIP_OWNER, STAFF_READ, Principal
from services.api.facts_persistence import (
    FactRecord,
    FactRepository,
    SelfApprovalError,
    get_fact_repository,
)
from services.api.session import AUTH_RESPONSES, read_access, write_access

facts_router = APIRouter(
    prefix="/api/facts", tags=["Approved facts"], responses=AUTH_RESPONSES
)


class DraftFactIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_key: str
    content: str
    source: str
    owner_id: str | None = None
    owner_text: str | None = None
    verified_at: str | None = None
    review_due_at: str | None = None
    supersedes_id: str | None = None


class FactOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    fact_key: str
    content: str
    owner_id: str | None
    owner_text: str | None
    status: str
    source: str
    verified_at: str | None
    review_due_at: str | None
    version: int
    supersedes_id: str | None
    created_by: str
    created_at: str
    approved_by: str | None
    approved_at: str | None
    archived_at: str | None


def _fact_out(record: FactRecord) -> FactOut:
    return FactOut(
        id=record.id,
        fact_key=record.fact_key,
        content=record.content,
        owner_id=record.owner_id,
        owner_text=record.owner_text,
        status=record.status,
        source=record.source,
        verified_at=record.verified_at,
        review_due_at=record.review_due_at,
        version=record.version,
        supersedes_id=record.supersedes_id,
        created_by=record.created_by,
        created_at=record.created_at,
        approved_by=record.approved_by,
        approved_at=record.approved_at,
        archived_at=record.archived_at,
    )


def _not_found(fact_id: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"no fact {fact_id!r}")


@facts_router.post("", response_model=FactOut, status_code=201)
def draft_fact(
    body: DraftFactIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: FactRepository = Depends(get_fact_repository),
) -> FactOut:
    try:
        return _fact_out(
            repo.draft(
                body.fact_key,
                body.content,
                body.source,
                actor_id=principal.user_id,
                owner_id=body.owner_id,
                owner_text=body.owner_text,
                verified_at=body.verified_at,
                review_due_at=body.review_due_at,
                supersedes_id=body.supersedes_id,
            )
        )
    except KeyError as error:
        raise _not_found(body.supersedes_id or "") from error


@facts_router.post("/{fact_id}/approve", response_model=FactOut)
def approve_fact(
    fact_id: str,
    principal: Principal = Depends(write_access(REVIEWER, SIP_OWNER)),
    repo: FactRepository = Depends(get_fact_repository),
) -> FactOut:
    try:
        return _fact_out(repo.approve(fact_id, actor_id=principal.user_id))
    except KeyError as error:
        raise _not_found(fact_id) from error
    except SelfApprovalError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(error)) from error


@facts_router.post("/{fact_id}/archive", response_model=FactOut)
def archive_fact(
    fact_id: str,
    principal: Principal = Depends(write_access(ANALYST, REVIEWER, SIP_OWNER)),
    repo: FactRepository = Depends(get_fact_repository),
) -> FactOut:
    try:
        return _fact_out(repo.archive(fact_id, actor_id=principal.user_id))
    except KeyError as error:
        raise _not_found(fact_id) from error


@facts_router.get("/{fact_id}", response_model=FactOut)
def get_fact(
    fact_id: str,
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: FactRepository = Depends(get_fact_repository),
) -> FactOut:
    try:
        return _fact_out(repo.get(fact_id))
    except KeyError as error:
        raise _not_found(fact_id) from error


@facts_router.get("/by-key/{fact_key}/latest", response_model=FactOut)
def get_latest_approved_fact(
    fact_key: str,
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: FactRepository = Depends(get_fact_repository),
) -> FactOut:
    record = repo.get_latest_approved(fact_key)
    if record is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"no approved fact for {fact_key!r}"
        )
    return _fact_out(record)


@facts_router.get("/by-key/{fact_key}/history", response_model=list[FactOut])
def get_fact_history(
    fact_key: str,
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: FactRepository = Depends(get_fact_repository),
) -> list[FactOut]:
    return [_fact_out(f) for f in repo.history(fact_key)]
