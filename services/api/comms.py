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

Three of the other routes (`approve`, `get`, `list`) close the gap #60 (Paras's review UI) and #65
(Bhanu's streaming API) both name as a dependency: "Comms Assistant service side (Roshan)".
Neither existed until now - draft generation returned text and persisted nothing, so there was no
row for a review UI to show or an approval to attach to.

`delete` (#342) exists because `comms_drafts` had no retention rule and no way to remove a row -
found by the #132 privacy verification pass. A retention *period* is still an INZBC decision
(`docs/client-questions.md` §4); this only gives a person a manual path to remove one row.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    model_validator,
)

from apps.comms.draft import BlankBriefError, Brief, ContentType, Tone, generate_draft
from services.api.auth import (
    REVIEWER,
    SECRETARIAT,
    SIP_OWNER,
    STAFF_READ,
    Principal,
    SelfApprovalError,
)
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

# The old free-text `brief` cap. Kept as the ceiling across all the structured fields together, so
# #303 provably shrank the paste target rather than growing it. See `DraftIn._within_total_budget`.
TOTAL_BRIEF_BUDGET = 4000


def get_model_gateway() -> ModelGateway:
    """FastAPI dependency, overridden in tests with a fake - same pattern as
    `services/api/runs.py`'s `get_run_repository`. Production gets a real `ModelGateway`, which
    builds its own OpenAI client lazily from the environment on first use.
    """
    return ModelGateway()


class DraftIn(BaseModel):
    """Structured brief (#303), replacing the single 4,000-character free-text box.

    **Breaking change to the request shape only.** `DraftOut` and `CommsDraftOut` are unchanged,
    because the brief is rendered to text before it is stored - so the list, read and approve
    paths, and the review UI that uses them, are untouched. Only the submit path moves.

    The limits are the point. A 200-character topic and eight 300-character key points is a much
    smaller target than one 4,000-character box for pasting whatever is on the clipboard, which is
    the disclosure route #303 describes. It is mitigation, not a boundary: a staff member can
    still type a member's name into `topic`, and the source declared to the gateway stays
    `STAFF_AUTHORED` rather than falsely claiming to be minimised. See `apps/comms/draft.Brief`.
    """

    model_config = ConfigDict(extra="forbid")

    content_type: ContentType
    topic: str = Field(min_length=1, max_length=200)
    # Capped in both directions: eight points, 300 characters each. Without a per-item limit the
    # list is a 4,000-character box again, wearing a different name.
    key_points: list[Annotated[str, StringConstraints(max_length=300)]] = Field(
        default_factory=list, max_length=8
    )
    # HttpUrl rather than str so a pasted paragraph cannot arrive dressed as a link.
    links: list[HttpUrl] = Field(default_factory=list, max_length=5)
    tone: Tone = "formal"

    @model_validator(mode="after")
    def _within_total_budget(self) -> DraftIn:
        """Caps the total staff-controlled text, not just each field.

        **This exists because the per-field caps alone made the problem worse.** #303 replaced a
        single 4,000-character box in order to shrink what could be pasted in one action. Summing
        the individual limits showed the opposite: 200 topic + 8x300 key points + 5 URLs, and
        pydantic's HttpUrl accepts roughly 2,000 characters per URL, which totals **12,940** -
        3.2x the box it replaced, with 10,340 of it in the links field.

        Per-field limits do not compose into a total. This one does, and it is set to the old
        4,000 so the change cannot silently grow the surface it was written to shrink.

        Measured, not assumed: the numbers above come from constructing this model with maximal
        values, which is what `test_the_total_budget_is_not_larger_than_the_box_it_replaced` does.
        """
        total = (
            len(self.topic)
            + sum(len(point) for point in self.key_points)
            + sum(len(str(link)) for link in self.links)
        )
        if total > TOTAL_BRIEF_BUDGET:
            raise ValueError(
                f"brief is {total} characters; the limit across topic, key points and links is "
                f"{TOTAL_BRIEF_BUDGET}. Shorten it or use fewer links."
            )
        return self

    def to_brief(self) -> Brief:
        return Brief(
            topic=self.topic,
            key_points=tuple(self.key_points),
            links=tuple(str(link) for link in self.links),
            tone=self.tone,
        )


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


class DeleteDraftIn(BaseModel):
    """Body, not a query parameter — a reason in a URL lands in access logs, which is the same
    leak in a different place. `reason` describes *why* the draft is being removed, not what it
    contained: it is stored in `audit_log`, which is append-only, so naming what was in the draft
    would move the disclosure into the one place it can never be deleted from again.
    """

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)


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
    brief = body.to_brief()
    try:
        result = generate_draft(gateway, body.content_type, brief)
    except BlankBriefError as error:
        # Pydantic's min_length=1 on `topic` already rejects a body with no characters at all;
        # this catches a whitespace-only topic, which min_length lets through.
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except (GatewayNotConfiguredError, RedactionNotConfiguredError) as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except GatewayCallError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    # The rendered brief is what is stored, so `comms_drafts.brief` stays text and every read path
    # keeps working. It is also what was actually sent to the model, which is the thing a reviewer
    # or an incident responder needs to see - not the form that produced it.
    record = repo.create(
        body.content_type, brief.render(), result.text, authored_by=principal.user_id
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


@router.delete("/drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft(
    draft_id: str,
    body: DeleteDraftIn,
    principal: Principal = Depends(write_access(SECRETARIAT, SIP_OWNER)),
    repo: CommsDraftRepository = Depends(get_comms_draft_repository),
) -> None:
    """Removes a draft outright (#342). Same roles as creating one — Secretariat, SIP Owner — not
    the reviewer roles that approve; deleting is an authoring-side act, not a review one.

    Any status is deletable, including `Approved`: the approval's own audit entry survives even
    though the row it approved is gone. See `CommsDraftRepository.delete`'s docstring for why the
    audit row this writes never carries the brief or draft text.
    """
    try:
        repo.delete(draft_id, actor_id=principal.user_id, reason=body.reason)
    except KeyError as error:
        raise _not_found(draft_id) from error


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
