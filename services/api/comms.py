"""`/api/comms/draft` (#53): the endpoint `apps/comms/ui/src/api/client.ts` already targets.

The UI client was written first, against the shape `docs/api-integration-spec.md`'s Comms
Assistant section describes - `{content_type, brief}` in, `{draft}` out, synchronous (matching
what `ModelGateway.complete()` offers today; the streaming SSE variant is separate, unbuilt work,
issue #65). This router is the first implementation of that contract, not a new one - see
`apps/comms/ui/src/api/client.ts`'s own docstring, which was calling this URL and shape before it
existed.

No auth dependency here yet, same documented gap as `services/api/runs.py`/`candidates.py`: this
repository has no session-cookie implementation despite ADR-0004 specifying one. Unlike those two,
this endpoint's downstream call is expensive (an external model call) and its failure modes are
distinct enough (not-yet-configured vs. genuinely down) to be worth mapping precisely rather than
folding into a generic 500 - see `_draft` below.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from apps.comms.draft import BlankBriefError, ContentType, generate_draft
from services.api.model_gateway import (
    GatewayCallError,
    GatewayNotConfiguredError,
    ModelGateway,
)
from services.api.redaction import RedactionNotConfiguredError

router = APIRouter(prefix="/api/comms", tags=["Comms Assistant"])


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
    """Matches `apps/comms/ui/src/api/client.ts`'s `isCommsDraftResult` guard exactly: one
    required non-empty `draft` string, nothing else the UI reads today.
    """

    model_config = ConfigDict(extra="forbid")

    draft: str


@router.post("/draft", response_model=DraftOut)
def draft(body: DraftIn, gateway: ModelGateway = Depends(get_model_gateway)) -> DraftOut:
    """Generates a draft. Never sends or publishes anything - see `apps/comms/draft.py`'s module
    docstring for why "nothing publishable without a recorded reviewer" holds by construction.

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
    return DraftOut(draft=result.text)
