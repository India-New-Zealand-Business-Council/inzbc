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

from .verification import VERIFIED_STATES, enforce_verification_gate


class MissingCurrentSignalError(RuntimeError):
    """Raised when a patch sets verification to a non-verified state without also setting
    signal, and the candidate's existing signal wasn't supplied either.

    Without `current_signal`, `effective_signal` would silently resolve to `None`, and
    `enforce_verification_gate` treats `None` as "not High/Critical" - so a verification
    downgrade on a candidate that actually is High/Critical would fail open instead of closed.
    Refusing outright forces the caller to state what they know, rather than this module
    assuming a downgrade is safe just because this particular PATCH didn't mention signal.
    """


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
    client: SipPipelineClient,
    candidate_id: str,
    assessment: CandidateAssessment,
    current_verification: VerificationState | None = None,
    current_signal: SignalStrength | None = None,
) -> dict:
    """PATCHes `candidate_id` with whichever fields of `assessment` were actually set.

    The effective signal/verification for the gate is whatever this assessment sets, falling
    back to `current_signal`/`current_verification` (e.g. from a prior GET of the candidate) for
    whichever side it leaves unset. This catches a PATCH that downgrades verification on a
    candidate that's already High/Critical, not only a PATCH that sets both at once - pass
    `current_signal` whenever the candidate's existing signal is known. See
    `verification.enforce_verification_gate` for why an unknown verification state is treated as
    unverified.

    Raises `MissingCurrentSignalError` if this assessment sets `verification` to a non-verified
    state without also setting `signal`, and `current_signal` wasn't supplied - an unknown
    signal must not be treated as "safe to downgrade" (see that error's docstring).
    """
    verification_downgrading = (
        assessment.verification is not None and assessment.verification not in VERIFIED_STATES
    )
    if verification_downgrading and assessment.signal is None and current_signal is None:
        raise MissingCurrentSignalError(
            f"patch sets verification={assessment.verification.value!r} without setting signal, "
            "and current_signal was not supplied - cannot tell whether this candidate is "
            "High/Critical, so the downgrade is refused rather than assumed safe"
        )

    effective_signal = assessment.signal or current_signal
    effective_verification = assessment.verification or current_verification
    enforce_verification_gate(effective_signal, effective_verification)

    fields = assessment.model_dump(mode="json", exclude_none=True)
    return client.patch_candidate(candidate_id, fields)
