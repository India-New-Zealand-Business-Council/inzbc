"""Comms Assistant draft generation (#53): content type + staff brief -> a rendered draft.

Drafts only. Nothing in this module sends, publishes, or persists anything - it returns text a
named human reviewer edits and approves before any of that happens (`docs/modules/comms-
assistant.md`'s definition of done). There is no publish path anywhere in this codebase yet
(`docs/api-integration-spec.md` Open item #4), so the "cannot reach a publish state without a
recorded reviewer" acceptance criterion holds by construction: there is nothing here that could
publish.

**Redaction is not implemented in this module because it must not be.** Per ADR-0006, every
external model call goes through `services/api/model_gateway.py`'s `ModelGateway.complete()`,
which redacts the *entire* prompt (this module's instructions plus the staff-supplied brief)
against `REDACTION_POLICY_PATH` before any provider call, and refuses outright with no configured
policy. A second, module-local redaction pass here would be a second place to get the policy
wrong - the platform has exactly one redaction control, in the gateway, and this module calls
through it rather than duplicating it.

**What still gates real use, per ADR-0006 §7:** the policy itself is approved and committed at
`config/redaction-policy.json`, so the INZBC decision is made. What is left is deployment -
`REDACTION_POLICY_PATH` points at nothing in any real deployment today, and until it does the
gateway refuses every call. Building this module against the real `ModelGateway` interface (tested
with a fake) is exactly what the ADR's "service-side development may begin now against a fake
gateway; it is deployment that waits" describes.
"""

from __future__ import annotations

from typing import Literal

from services.api.model_gateway import GatewayResult, ModelGateway
from services.api.prompt_boundary import PromptSource

ContentType = Literal["newsletter", "linkedin_post", "event_announcement", "member_spotlight"]

_CONTENT_TYPE_LABELS: dict[ContentType, str] = {
    "newsletter": "email newsletter section",
    "linkedin_post": "LinkedIn post",
    "event_announcement": "event announcement",
    "member_spotlight": "member spotlight",
}


class BlankBriefError(ValueError):
    """Raised for a brief that is empty or whitespace-only - nothing for the model to draft
    from, and a blank prompt is not a case `ModelGateway` should have to reject on our behalf.
    """


def build_prompt(content_type: ContentType, brief: str) -> str:
    """Builds the prompt sent to `ModelGateway.complete()`.

    Deliberately generic. `docs/modules/comms-assistant.md` lists "INZBC voice guide + approved
    templates" as a dependency that has not landed - this prompt does not invent a house style to
    fill that gap, since a fabricated voice would be harder to notice and correct than an
    obviously generic draft. Wire the real voice guide in here once it exists, rather than
    guessing at INZBC's tone now.
    """
    label = _CONTENT_TYPE_LABELS[content_type]
    return (
        f"Draft a {label} for the India New Zealand Business Council (INZBC), a member "
        "organisation connecting New Zealand and Indian businesses.\n\n"
        "This is an internal draft only - it will be reviewed and edited by a named staff "
        "member before anything is sent or published, so do not present it as final copy.\n\n"
        "Do not invent statistics, member names, board names, dates, or FTA details not present "
        "in the brief below. Where a fact is needed but not given, use a "
        "[[placeholder]] rather than inventing one.\n\n"
        f"Brief:\n{brief.strip()}"
    )


def generate_draft(gateway: ModelGateway, content_type: ContentType, brief: str) -> GatewayResult:
    """Generates a draft via `gateway.complete()`. Raises `BlankBriefError` for an empty brief;
    propagates `GatewayNotConfiguredError`, `RedactionNotConfiguredError` and `GatewayCallError`
    unchanged - this module has no more information about those failures than the gateway does,
    so it does not wrap or reinterpret them.
    """
    if not brief.strip():
        raise BlankBriefError("brief must not be blank")
    prompt = build_prompt(content_type, brief)
    # STAFF_AUTHORED, and the residual risk is worth naming rather than leaving implied: the brief
    # is free text a staff member typed, so nothing here can stop them pasting member details into
    # it. The declaration records where the text came from, not that it is clean.
    #
    # This is the one call site with no structural control available, because there is no record to
    # minimise - a human wrote prose. What bounds it is that the operator is told not to paste
    # member details and told why (`docs/operator-guide.md` §3), with redaction as defence in depth
    # for the identifiers it can match. A prompt assembled from member records must go through
    # `minimise()` and be declared MINIMISED_RECORD instead.
    return gateway.complete(prompt, source=PromptSource.STAFF_AUTHORED)
