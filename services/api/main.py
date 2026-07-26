"""INZBC API — FastAPI application.

Implements `schemas/api-contract.md` over the domain modules. This first slice exposes the FTA
Explainer read path only; the SIP run and candidate endpoints land once the database and the
orchestrator's persistence exist (ADR-0004 graduated the platform to make that possible).

The response envelope is deliberately status-tagged rather than "a list that might be empty".
`apps/fta/explainer` keeps `ExplainerAnswer` and `NoMatch` structurally distinct so escalation
guidance can never be rendered as a sourced finding; this module carries that guarantee across the
wire, and `_check_envelope` enforces it rather than trusting callers to construct it correctly.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import FastAPI, Query
from pydantic import BaseModel, ConfigDict, model_validator

from apps.fta.explainer import ExplainerAnswer, NoMatch, answer_query, no_match

app = FastAPI(
    title="INZBC API",
    version="0.1.0",
    summary="Trade intelligence and FTA services for the India New Zealand Business Council.",
)


class AnswerOut(BaseModel):
    """A sourced FTA finding. Every field is evidence or the presentation it must carry."""

    model_config = ConfigDict(extra="forbid")

    topic: str
    sector: str
    treatment: str
    # Always true today — answer_query filters to confirmed entries. Serialised anyway so a
    # client can never infer confirmation from the field's absence if that ever changes.
    confirmed: bool
    citation: str
    verified_at: date
    status_line: str
    jurisdiction: str
    next_step: str
    disclaimer: str
    confidence: str
    confidence_meaning: str
    notes: str | None = None


class ActionRequiredOut(BaseModel):
    """The escalation state. Carries no topic, treatment or citation, by design."""

    model_config = ConfigDict(extra="forbid")

    message: str
    next_step: str
    escalation_path: str
    status_line: str
    jurisdiction: str
    disclaimer: str
    confidence: str
    confidence_meaning: str


class FtaQueryResponse(BaseModel):
    """`status` is the field a client branches on — not the length of `answers`.

    A client that only checked `answers` would render an empty results list for a no-match and
    silently drop the escalation path, which is the outcome docs/modules/fta-centre.md exists to
    prevent.
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["matched", "no_match"]
    query: str
    answers: list[AnswerOut]
    action_required: ActionRequiredOut | None = None

    @model_validator(mode="after")
    def _check_envelope(self) -> FtaQueryResponse:
        if self.status == "matched":
            if not self.answers:
                raise ValueError("status 'matched' requires at least one answer")
            if self.action_required is not None:
                raise ValueError("status 'matched' must not carry action_required")
        else:
            if self.answers:
                raise ValueError("status 'no_match' must not carry answers")
            if self.action_required is None:
                raise ValueError("status 'no_match' requires action_required")
        return self


def _answer_out(answer: ExplainerAnswer) -> AnswerOut:
    return AnswerOut(
        topic=answer.topic,
        sector=answer.sector,
        treatment=answer.treatment,
        confirmed=answer.confirmed,
        citation=answer.citation,
        verified_at=answer.verified_at,
        status_line=answer.status_line,
        jurisdiction=answer.jurisdiction,
        next_step=answer.next_step,
        disclaimer=answer.disclaimer,
        confidence=answer.confidence.value,
        confidence_meaning=answer.confidence_meaning,
        notes=answer.notes,
    )


def _action_required_out(result: NoMatch) -> ActionRequiredOut:
    return ActionRequiredOut(
        message=result.message,
        next_step=result.next_step,
        escalation_path=result.escalation_path,
        status_line=result.status_line,
        jurisdiction=result.jurisdiction,
        disclaimer=result.disclaimer,
        confidence=result.confidence.value,
        confidence_meaning=result.confidence_meaning,
    )


@app.get("/api/fta/query", response_model=FtaQueryResponse, tags=["FTA Explainer"])
def fta_query(
    q: str = Query(
        ...,
        max_length=500,
        description="A sector or product question, e.g. 'dairy' or 'manuka honey'.",
    ),
) -> FtaQueryResponse:
    """Answers an FTA question from the sourced corpus, or escalates.

    A query with no confirmed corpus match is **not** an error: it returns HTTP 200 with
    `status: "no_match"` and the Action Required escalation path. Returning 404 would push
    callers toward an error branch that discards the guidance.
    """
    answers = answer_query(q)
    if not answers:
        return FtaQueryResponse(
            status="no_match",
            query=q,
            answers=[],
            action_required=_action_required_out(no_match(q)),
        )
    return FtaQueryResponse(
        status="matched",
        query=q,
        answers=[_answer_out(a) for a in answers],
        action_required=None,
    )


@app.get("/health", tags=["Operations"])
def health() -> dict[str, str]:
    """Liveness probe for the host's health check (ADR-0004)."""
    return {"status": "ok"}
