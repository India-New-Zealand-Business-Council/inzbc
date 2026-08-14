"""`/api/comms` (#53, and the persistence/approval gap #60 and #65 both depend on).

`POST /draft` is the endpoint `apps/comms/ui/src/api/client.ts` already targets - `{content_type,
brief}` in, `{draft}` out, synchronous (matching what `ModelGateway.complete()` offers today; the
streaming SSE variant is separate, unbuilt work, issue #65). This router is the first
implementation of that contract, not a new one - see `apps/comms/ui/src/api/client.ts`'s own
docstring, which was calling this URL and shape before it existed. `DraftOut` now also carries
`id`/`status`: additive, not a breaking change - the UI's `isCommsDraftResult` guard checks only
that `draft` is a non-empty string, by its own docstring's stated design.

Every write here requires a session (ADR-0004): reads declare `read_access`, writes declare
`write_access`, both via `services/api/session.py`, same as every other business router.

The other three routes (`approve`, `get`, `list`) close the gap #60 (Paras's review UI) and #65
(Bhanu's streaming API) both name as a dependency: "Comms Assistant service side (Roshan)".
Neither existed until now - draft generation returned text and persisted nothing, so there was no
row for a review UI to show or an approval to attach to.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from apps.comms.draft import BlankBriefError, ContentType, generate_draft
from services.api.auth import REVIEWER, SECRETARIAT, SIP_OWNER, STAFF_READ, Principal, SelfApprovalError
from services.api.comms_persistence import (
    CommsDraftRecord,
    CommsDraftRepository,
    get_comms_draft_repository,
)
from services.api.model_gateway import (
    GatewayCallError,
    GatewayNotConfiguredError,
    ModelGateway,
)
from services.api.redaction import RedactionNotConfiguredError
from services.api.session import AUTH_RESPONSES, read_access, write_access

router = APIRouter(prefix="/api/comms", tags=["Comms Assistant"], responses=AUTH_RESPONSES)


def get_model_gateway() -> ModelGateway:
    """FastAPI dependency, overridden in tests with a fake - same pattern as
    `services/api/runs.py`'s `get_run_repository`. Production gets a real `ModelGateway`, which
    builds its own OpenAI client lazily from the environment on first use.
    """
    return ModelGateway()


class DraftIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_type: ContentType
    brief: str = Field(min_length=1, max_length=4000)


class DraftOut(BaseModel):
    """`draft` is what `apps/comms/ui/src/api/client.ts`'s `isCommsDraftResult` guard checks -
    a non-empty string, nothing more required. `id`/`status` are additive: present for a client
    that wants to fetch or approve the persisted row, ignored by a client that does not.
    """

    model_config = ConfigDict(extra="forbid")

    draft: str
    id: str
    status: str


class ApproveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


class CommsDraftOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    content_type: str
    brief: str
    draft: str
    status: str
    authored_by: str
    approved_by: str | None
    approved_at: str | None
    approval_reason: str | None
    created_at: str


def _draft_record_out(record: CommsDraftRecord) -> CommsDraftOut:
    return CommsDraftOut(
        id=record.id,
        content_type=record.content_type,
        brief=record.brief,
        draft=record.draft_text,
        status=record.status,
        authored_by=record.authored_by,
        approved_by=record.approved_by,
        approved_at=record.approved_at,
        approval_reason=record.approval_reason,
        created_at=record.created_at,
    )


def _not_found(draft_id: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"no comms draft {draft_id!r}")


@router.post("/draft", response_model=DraftOut)
def draft(
    body: DraftIn,
    principal: Principal = Depends(write_access(SECRETARIAT, SIP_OWNER)),
    gateway: ModelGateway = Depends(get_model_gateway),
    repo: CommsDraftRepository = Depends(get_comms_draft_repository),
) -> DraftOut:
    """Generates a draft and persists it. Never sends or publishes anything - see
    `apps/comms/draft.py`'s module docstring for why "nothing publishable without a recorded
    reviewer" holds by construction.

    Failure mapping is deliberately specific, not a blanket 500:
    - `GatewayNotConfiguredError` / `RedactionNotConfiguredError` -> 503. Deployment configuration
      is missing (no API key, or - per ADR-0006 - no approved `REDACTION_POLICY_PATH`). Expected,
      correct refusal in any environment that hasn't been configured yet, not a bug to alert on
      the same way as a real failure.
    - `GatewayCallError` -> 502. The provider call itself failed after a retry - genuinely down,
      distinct from "not configured".
    """
    try:
        result = generate_draft(gateway, body.content_type, body.brief)
    except BlankBriefError as error:
        # Pydantic's min_length=1 already rejects a request body with no characters at all; this
        # catches a whitespace-only brief, which min_length lets through.
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except (GatewayNotConfiguredError, RedactionNotConfiguredError) as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except GatewayCallError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    record = repo.create(
        body.content_type, body.brief, result.text, authored_by=principal.user_id
    )
    return DraftOut(draft=result.text, id=record.id, status=record.status)


@router.post("/drafts/{draft_id}/approve", response_model=CommsDraftOut)
def approve_draft(
    draft_id: str,
    body: ApproveIn,
    principal: Principal = Depends(write_access(REVIEWER, SIP_OWNER)),
    repo: CommsDraftRepository = Depends(get_comms_draft_repository),
) -> CommsDraftOut:
    """The named-reviewer approval gate #60 depends on. BR8: the author of a draft may not also
    approve it, enforced by `refuse_self_review` inside `CommsDraftRepository.approve`.
    """
    try:
        record = repo.approve(draft_id, principal=principal, reason=body.reason)
    except KeyError as error:
        raise _not_found(draft_id) from error
    except SelfApprovalError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    return _draft_record_out(record)


@router.get("/drafts/{draft_id}", response_model=CommsDraftOut)
def get_draft(
    draft_id: str,
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: CommsDraftRepository = Depends(get_comms_draft_repository),
) -> CommsDraftOut:
    try:
        return _draft_record_out(repo.get(draft_id))
    except KeyError as error:
        raise _not_found(draft_id) from error


@router.get("/drafts", response_model=list[CommsDraftOut])
def list_drafts(
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: CommsDraftRepository = Depends(get_comms_draft_repository),
) -> list[CommsDraftOut]:
    return [_draft_record_out(record) for record in repo.list_all()]
