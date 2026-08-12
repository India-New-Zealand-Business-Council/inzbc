"""INZBC API — FastAPI application.

Implements `schemas/api-contract.md` over the domain modules: the FTA Explainer read path, the SIP
run lifecycle endpoints (#120, `services/api/runs.py`), the candidate command endpoints
(#121, `services/api/candidates.py`), and the Comms Assistant draft endpoint (#53,
`services/api/comms.py`).

The response envelope is deliberately status-tagged rather than "a list that might be empty".
`apps/fta/explainer` keeps `ExplainerAnswer` and `NoMatch` structurally distinct so escalation
guidance can never be rendered as a sourced finding; this module carries that guarantee across the
wire, and `_check_envelope` enforces it rather than trusting callers to construct it correctly.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, model_validator

from apps.fta.explainer import ExplainerAnswer, NoMatch, answer_query, no_match
from services.api.candidates import router as candidates_router
from services.api.comms import router as comms_router
from services.api.hardening import install as install_hardening
from services.api.runs import router as runs_router
from services.api.session import router as session_router

app = FastAPI(
    title="INZBC API",
    version="0.1.0",
    summary="Trade intelligence and FTA services for the India New Zealand Business Council.",
)
app.include_router(runs_router)

# Rate limiting, one error shape, security headers, and CORS only when configured (#98). Applied
# here rather than per endpoint so a route added later is covered by default instead of by
# somebody remembering.
install_hardening(app)
app.include_router(candidates_router)
app.include_router(comms_router)
app.include_router(session_router)


class AnswerOut(BaseModel):
    """A sourced FTA finding. Every field is evidence or the presentation it must carry."""

    model_config = ConfigDict(extra="forbid")

    # Stable corpus identifier. Clients key lists and DOM ids off this, never off `topic`.
    id: str
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
        id=answer.id,
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


# Serve the built UI from this same origin when the image contains it (see Dockerfile). Mounted
# last so it can never shadow an /api or /health route. Absent in development and in tests, where
# the Vite dev server proxies to this app instead, so the mount is conditional rather than assumed.
_STATIC = Path(__file__).resolve().parents[2] / "static"
if _STATIC.is_dir():
    # html=True makes unknown paths fall back to index.html, which a client-side router needs.
    app.mount("/", StaticFiles(directory=_STATIC, html=True), name="ui")


def _require_both_schemes(spec: dict) -> dict:
    """Rewrites write routes to require the session cookie *and* the CSRF token, not either.

    FastAPI emits one entry per security dependency, and a list of entries is OR in OpenAPI:
    `[{"SessionCookie": []}, {"CsrfToken": []}]` reads as "whichever you have". The server
    requires both, so the published contract was describing something more permissive than the
    API actually is, and a generated client had grounds to send only the cookie and then be
    surprised by a 403.

    Merging them into a single object makes it AND. Done here, over the generated document,
    rather than by hand-editing `schemas/openapi.json`: the spec is regenerated on every change,
    so anything written into the file directly is lost the next time codegen runs.
    """
    for operations in spec.get("paths", {}).values():
        for operation in operations.values():
            if not isinstance(operation, dict):
                continue
            security = operation.get("security")
            if not security or len(security) < 2:
                continue
            merged: dict[str, list] = {}
            for requirement in security:
                merged.update(requirement)
            operation["security"] = [merged]
    return spec


def custom_openapi() -> dict:
    if app.openapi_schema is None:
        app.openapi_schema = _require_both_schemes(get_openapi(
            title=app.title,
            version=app.version,
            summary=app.summary,
            routes=app.routes,
        ))
    return app.openapi_schema


app.openapi = custom_openapi
