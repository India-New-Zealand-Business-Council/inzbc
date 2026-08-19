"""`/api/action-register`, `/api/watch-lists`, `/api/exceptions` (#209).

Thin HTTP wrappers over `services/api/registers_persistence.py` - see that module's docstring for
the append-only vs update-in-place split, and for the explicit lane note (this is persistence and
API only; `docs/sip/build-plan.md`'s "Registers UI" is Paras's Workstream C).

Three separate `APIRouter`s in one file rather than three files: each is a handful of routes
around one repository, following exactly the shape `services/api/comms.py` already established
for a single entity, and the three belong together because they are one issue (#209) and read
together more easily than split.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from services.api.auth import ANALYST, SIP_OWNER, STAFF_READ, Principal
from services.api.registers_persistence import (
    ActionRegisterRecord,
    ActionRegisterRepository,
    ExceptionRecord,
    ExceptionRepository,
    WatchListRecord,
    WatchListRepository,
    get_action_register_repository,
    get_exception_repository,
    get_watch_list_repository,
)
from services.api.session import AUTH_RESPONSES, read_access, write_access

# ---------------------------------------------------------------------------
# Action register
# ---------------------------------------------------------------------------

action_register_router = APIRouter(
    prefix="/api/action-register", tags=["Action register"], responses=AUTH_RESPONSES
)


class CreateActionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_code: str
    title: str
    status: str
    description: str | None = None
    owner_id: str | None = None
    owner_text: str | None = None
    priority: str | None = None
    due_date: str | None = None
    review_date: str | None = None
    evidence_ref: str | None = None


class UpdateActionStatusIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    evidence_ref: str | None = None


class ActionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


def _action_out(record: ActionRegisterRecord) -> ActionOut:
    return ActionOut(
        id=record.id,
        action_code=record.action_code,
        title=record.title,
        description=record.description,
        owner_id=record.owner_id,
        owner_text=record.owner_text,
        priority=record.priority,
        due_date=record.due_date,
        review_date=record.review_date,
        status=record.status,
        evidence_ref=record.evidence_ref,
        closed_at=record.closed_at,
        created_at=record.created_at,
    )


def _not_found(kind: str, item_id: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"no {kind} {item_id!r}")


@action_register_router.post("", response_model=ActionOut, status_code=201)
def create_action(
    body: CreateActionIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: ActionRegisterRepository = Depends(get_action_register_repository),
) -> ActionOut:
    return _action_out(
        repo.create(
            body.action_code,
            body.title,
            body.status,
            actor_id=principal.user_id,
            description=body.description,
            owner_id=body.owner_id,
            owner_text=body.owner_text,
            priority=body.priority,
            due_date=body.due_date,
            review_date=body.review_date,
            evidence_ref=body.evidence_ref,
        )
    )


@action_register_router.post("/{action_id}/status", response_model=ActionOut)
def update_action_status(
    action_id: str,
    body: UpdateActionStatusIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: ActionRegisterRepository = Depends(get_action_register_repository),
) -> ActionOut:
    try:
        return _action_out(
            repo.update_status(
                action_id, body.status, actor_id=principal.user_id, evidence_ref=body.evidence_ref
            )
        )
    except KeyError as error:
        raise _not_found("action", action_id) from error


@action_register_router.get("/{action_id}", response_model=ActionOut)
def get_action(
    action_id: str,
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: ActionRegisterRepository = Depends(get_action_register_repository),
) -> ActionOut:
    try:
        return _action_out(repo.get(action_id))
    except KeyError as error:
        raise _not_found("action", action_id) from error


@action_register_router.get("", response_model=list[ActionOut])
def list_actions(
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: ActionRegisterRepository = Depends(get_action_register_repository),
) -> list[ActionOut]:
    return [_action_out(a) for a in repo.list_all()]


# ---------------------------------------------------------------------------
# Watch lists
# ---------------------------------------------------------------------------

watch_list_router = APIRouter(
    prefix="/api/watch-lists", tags=["Watch lists"], responses=AUTH_RESPONSES
)


class CreateWatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    watch_code: str
    title: str
    status: str
    category: str | None = None
    frequency: str | None = None
    escalation: str | None = None
    next_review: str | None = None


class UpdateWatchStatusIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    next_review: str | None = None


class WatchOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    watch_code: str
    title: str
    category: str | None
    frequency: str | None
    escalation: str | None
    status: str
    next_review: str | None


def _watch_out(record: WatchListRecord) -> WatchOut:
    return WatchOut(
        id=record.id,
        watch_code=record.watch_code,
        title=record.title,
        category=record.category,
        frequency=record.frequency,
        escalation=record.escalation,
        status=record.status,
        next_review=record.next_review,
    )


@watch_list_router.post("", response_model=WatchOut, status_code=201)
def create_watch(
    body: CreateWatchIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: WatchListRepository = Depends(get_watch_list_repository),
) -> WatchOut:
    return _watch_out(
        repo.create(
            body.watch_code,
            body.title,
            body.status,
            actor_id=principal.user_id,
            category=body.category,
            frequency=body.frequency,
            escalation=body.escalation,
            next_review=body.next_review,
        )
    )


@watch_list_router.post("/{watch_id}/status", response_model=WatchOut)
def update_watch_status(
    watch_id: str,
    body: UpdateWatchStatusIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: WatchListRepository = Depends(get_watch_list_repository),
) -> WatchOut:
    try:
        return _watch_out(
            repo.update_status(
                watch_id, body.status, actor_id=principal.user_id, next_review=body.next_review
            )
        )
    except KeyError as error:
        raise _not_found("watch-list entry", watch_id) from error


@watch_list_router.get("/{watch_id}", response_model=WatchOut)
def get_watch(
    watch_id: str,
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: WatchListRepository = Depends(get_watch_list_repository),
) -> WatchOut:
    try:
        return _watch_out(repo.get(watch_id))
    except KeyError as error:
        raise _not_found("watch-list entry", watch_id) from error


@watch_list_router.get("", response_model=list[WatchOut])
def list_watches(
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: WatchListRepository = Depends(get_watch_list_repository),
) -> list[WatchOut]:
    return [_watch_out(w) for w in repo.list_all()]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

exceptions_router = APIRouter(
    prefix="/api/exceptions", tags=["Exceptions"], responses=AUTH_RESPONSES
)


class RecordExceptionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exception_type: str
    severity: str
    status: str
    run_id: str | None = None
    owner_id: str | None = None
    original_preserved: bool = True


class CorrectExceptionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exception_type: str
    severity: str
    status: str
    reason: str


class ExceptionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    run_id: str | None
    exception_type: str
    severity: str
    owner_id: str | None
    status: str
    original_preserved: bool
    correction_ref: str | None
    created_at: str


def _exception_out(record: ExceptionRecord) -> ExceptionOut:
    return ExceptionOut(
        id=record.id,
        run_id=record.run_id,
        exception_type=record.exception_type,
        severity=record.severity,
        owner_id=record.owner_id,
        status=record.status,
        original_preserved=record.original_preserved,
        correction_ref=record.correction_ref,
        created_at=record.created_at,
    )


@exceptions_router.post("", response_model=ExceptionOut, status_code=201)
def record_exception(
    body: RecordExceptionIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: ExceptionRepository = Depends(get_exception_repository),
) -> ExceptionOut:
    return _exception_out(
        repo.record(
            body.exception_type,
            body.severity,
            body.status,
            actor_id=principal.user_id,
            run_id=body.run_id,
            owner_id=body.owner_id,
            original_preserved=body.original_preserved,
        )
    )


@exceptions_router.post("/{exception_id}/correct", response_model=ExceptionOut, status_code=201)
def correct_exception(
    exception_id: str,
    body: CorrectExceptionIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: ExceptionRepository = Depends(get_exception_repository),
) -> ExceptionOut:
    """201, not 200: this inserts a new row (the correction) rather than modifying the one named
    in the path - the append-only guarantee `registers_persistence.py` documents, visible in the
    HTTP contract too."""
    try:
        return _exception_out(
            repo.correct(
                exception_id,
                body.exception_type,
                body.severity,
                body.status,
                actor_id=principal.user_id,
                reason=body.reason,
            )
        )
    except KeyError as error:
        raise _not_found("exception", exception_id) from error


@exceptions_router.get("/{exception_id}", response_model=ExceptionOut)
def get_exception(
    exception_id: str,
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: ExceptionRepository = Depends(get_exception_repository),
) -> ExceptionOut:
    try:
        return _exception_out(repo.get(exception_id))
    except KeyError as error:
        raise _not_found("exception", exception_id) from error


@exceptions_router.get("", response_model=list[ExceptionOut])
def list_exceptions(
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: ExceptionRepository = Depends(get_exception_repository),
) -> list[ExceptionOut]:
    return [_exception_out(e) for e in repo.list_all()]
