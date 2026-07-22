"""Candidate assessment: SIP-184 steps 6-7 (relevance, signal, confidence, verification,
duplicate status, routing) applied on top of an already-captured candidate.

This module only carries values through to the API with the same validation Candidate itself
enforces (see apps/sip/pipeline/models.py) - it does not compute nz/india/member_relevance,
signal or confidence itself. SIP-050 (the approved scoring/prompt framework referenced in
docs/sip/README.md) isn't in this repo yet, and per docs/sip/README.md's non-negotiables all
scoring/model calls are server-side; the values here come from an analyst or a server-side
recommendation, this module just applies them.
"""

from __future__ import annotations

from pydantic import Field

from apps.sip.pipeline.client import SipPipelineClient
from apps.sip.pipeline.models import (
    SignalStrength,
    SipModel,
    SourceConfidence,
    VerificationState,
)


class CandidateAssessment(SipModel):
    """A partial update to a Candidate's assessment fields. Every field is optional so a caller
    can patch just the ones being set right now (e.g. verify separately from score).
    """

    nz_relevance: int | None = Field(default=None, ge=0, le=5)
    india_relevance: int | None = Field(default=None, ge=0, le=5)
    member_relevance: int | None = Field(default=None, ge=0, le=5)
    signal: SignalStrength | None = None
    confidence: SourceConfidence | None = None
    verification: VerificationState | None = None
    duplicate_of: str | None = None
    included: bool | None = None
    reason: str | None = None
    proposed_routing: str | None = None


def apply_candidate_assessment(
    client: SipPipelineClient, candidate_id: str, assessment: CandidateAssessment
) -> dict:
    """PATCHes `candidate_id` with whichever fields of `assessment` were actually set."""
    fields = assessment.model_dump(mode="json", exclude_none=True)
    return client.patch_candidate(candidate_id, fields)
