"""SIP-050 scoring engine: candidate content -> scored recommendation via the model gateway.

Fills the gap assessment.py deliberately left open: `CandidateAssessment` validates and carries
relevance/signal/confidence values but does not compute them. This module computes them against
the SIP-050 Master Prompt v1.1 framework (docs/sip/launch/SIP-050_master_prompt_v1.1.md) using
the model gateway (services/api/model_gateway.py).

Boundaries, per SIP-050 and docs/sip/README.md:
- The model RECOMMENDS; a human decides. Output here is a `ScoringRecommendation`, applied via
  the existing `apply_candidate_assessment` PATCH path only after analyst review.
- Verification is never model-assigned - it is an evidence question (claim vs. official
  source), so `to_assessment` always leaves `verification` unset and the existing
  fail-closed verification gate continues to govern High/Critical.
- Fail closed on model output: anything that is not the exact JSON contract raises
  `ScoringParseError` - no defaults, no partial acceptance, no retrying into a guess.
"""

from __future__ import annotations

import json

from pydantic import Field, ValidationError

from apps.sip.collector.assessment import CandidateAssessment
from apps.sip.pipeline.models import SignalStrength, SipModel, SourceConfidence
from services.api.model_gateway import ModelGateway
from services.api.prompt_boundary import PromptSource


class ScoringParseError(RuntimeError):
    """Model output did not match the JSON contract. The candidate stays unscored; it must
    never be given assumed values (SIP-050: accuracy over providing an answer at any cost).
    """


class ScoringRecommendation(SipModel):
    """The model's recommended assessment, validated at the trust boundary (ADR-0001)."""

    # strict=True: pydantic v2 lax mode would otherwise coerce "5", True, or 5.0 into a valid
    # int, so a model returning a string/bool/float would slip a wrong-typed score past the gate
    # (True -> 1 is the dangerous one). A scoring contract must accept only a JSON integer.
    nz_relevance: int = Field(strict=True, ge=0, le=5)
    india_relevance: int = Field(strict=True, ge=0, le=5)
    member_relevance: int = Field(strict=True, ge=0, le=5)
    signal: SignalStrength
    confidence: SourceConfidence
    reason: str


_PROMPT_TEMPLATE = """You are the assessment step of INZBC's Strategic Intelligence Platform,
operating under the SIP-050 Master Prompt v1.1 framework.

Rules (non-negotiable):
- Do not invent facts. Assess only what the article itself supports.
- New Zealand relevance first; do not invent an India-New Zealand angle where none clearly exists.
- Signal strength must not be inferred from source prestige alone.
- If the material is thin, old, syndicated or unclear, score it low rather than guessing high.

Score this candidate:
- nz_relevance, india_relevance, member_relevance: integers 0-5.
- signal: one of "Low", "Medium", "High", "Critical". High means material commercial, policy,
  regulatory or member consequence; Critical is reserved for immediate, major consequence.
- confidence: one of "High", "Medium", "Low", "Unverified" - this is source confidence in the
  claim as presented, not your confidence in the scoring.
- reason: one or two sentences, plain language, grounded in the article content.

Respond with ONLY a JSON object with exactly the keys nz_relevance, india_relevance,
member_relevance, signal, confidence, reason. No markdown, no commentary.

Candidate:
Headline: {headline}
Source: {source}
Published: {published}
URL: {url}
Summary: {summary}
"""


def build_scoring_prompt(
    headline: str, source: str, published: str, url: str, summary: str
) -> str:
    return _PROMPT_TEMPLATE.format(
        headline=headline, source=source, published=published, url=url, summary=summary
    )


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    """`json.loads` object_pairs_hook: fail closed on a duplicate key rather than silently
    keeping the last value (which could hide an out-of-range score behind an in-range one).
    """
    seen: dict = {}
    for key, value in pairs:
        if key in seen:
            raise ScoringParseError(f"model output had a duplicate key: {key!r}")
        seen[key] = value
    return seen


def score_candidate(
    gateway: ModelGateway,
    *,
    headline: str,
    source: str,
    published: str,
    url: str,
    summary: str,
) -> ScoringRecommendation:
    """One gateway call, strict parse. Raises `ScoringParseError` on any deviation from the
    contract; raises the gateway's own errors unchanged when the call itself fails.
    """
    # PUBLIC_SOURCE: every field here comes from a published article - its headline, summary, URL,
    # publication date and the outlet that ran it. Nothing member-derived reaches this prompt, and
    # if that ever changes the declaration has to change with it.
    result = gateway.complete(
        build_scoring_prompt(headline, source, published, url, summary),
        source=PromptSource.PUBLIC_SOURCE,
    )
    try:
        # object_pairs_hook rejects duplicate keys, which json.loads would otherwise collapse to
        # the last value - a way to smuggle an in-range score past an out-of-range one. Its
        # ScoringParseError propagates out of json.loads directly (not wrapped as JSONDecodeError).
        payload = json.loads(result.text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as error:
        raise ScoringParseError("model output was not valid JSON") from error
    if not isinstance(payload, dict):
        raise ScoringParseError("model output was not a JSON object")
    try:
        return ScoringRecommendation(**payload)
    except (ValidationError, TypeError) as error:
        raise ScoringParseError("model output did not match the scoring contract") from error


def to_assessment(recommendation: ScoringRecommendation) -> CandidateAssessment:
    """Maps a recommendation onto the existing PATCH model. `verification` is deliberately
    left unset - verification is evidence-driven and human-owned, and leaving it out keeps
    `apply_candidate_assessment`'s fail-closed gate in charge of High/Critical.
    """
    return CandidateAssessment(
        nz_relevance=recommendation.nz_relevance,
        india_relevance=recommendation.india_relevance,
        member_relevance=recommendation.member_relevance,
        signal=recommendation.signal,
        confidence=recommendation.confidence,
        reason=recommendation.reason,
    )
