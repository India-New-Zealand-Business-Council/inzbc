"""INZBC API — FastAPI application.

Implements `schemas/api-contract.md` over the domain modules: the FTA Explainer read path, the SIP
run lifecycle endpoints (#120, `services/api/runs.py`), the candidate command endpoints
(#121, `services/api/candidates.py`), the Comms Assistant draft endpoint (#53,
`services/api/comms.py`), and the source library + source check endpoints (#55,
`services/api/source_library.py`, `services/api/source_checks.py`).

The response envelope is deliberately status-tagged rather than "a list that might be empty".
`apps/fta/explainer` keeps `ExplainerAnswer` and `NoMatch` structurally distinct so escalation
guidance can never be rendered as a sourced finding; this module carries that guarantee across the
wire, and `_check_envelope` enforces it rather than trusting callers to construct it correctly.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, model_validator

from apps.fta.explainer import (
    Depth,
    ExplainerAnswer,
    InternalAnswer,
    MemberAnswer,
    NoMatch,
    PublicAnswer,
    answer_query,
    answer_query_at_depth,
    no_match,
)
from services.api.agent_rehearsals import router as agent_rehearsals_router
from services.api.auth import (
    STAFF_READ,
    NotAuthorisedError,
    Principal,
    SessionRepository,
    require_roles,
)
from services.api.candidates import router as candidates_router
from services.api.comms import router as comms_router
from services.api.dashboard import router as dashboard_router
from services.api.facts import facts_router
from services.api.hardening import install as install_hardening
from services.api.oauth import router as oauth_router
from services.api.registers import (
    action_register_router,
    exceptions_router,
    watch_list_router,
)
from services.api.reports import router as reports_router
from services.api.run_authorisations import router as run_authorisations_router
from services.api.runs import router as runs_router
from services.api.session import (
    get_session_repository,
    require_principal,
    session_cookie_scheme,
)
from services.api.session import router as session_router
from services.api.site_forms import (
    SiteFormWebhookIn,
    site_forms_router,
    webhook_router,
)
from services.api.source_checks import router as source_checks_router
from services.api.source_library import router as source_library_router

# Roles permitted to request `depth=member` and `depth=internal` on `/api/fta/query` (#392).
# Public is unauthenticated; member requires any recognised signed-in role; internal is restricted
# to the roles that draft, review, own, or audit intelligence evidence.
FTA_MEMBER_ROLES: frozenset[str] = STAFF_READ
FTA_INTERNAL_ROLES: frozenset[str] = frozenset(
    {"Analyst", "Reviewer", "SIP Owner", "Auditor"}
)

app = FastAPI(
    title="INZBC API",
    version="0.1.0",
    summary="Trade intelligence and FTA services for the India New Zealand Business Council.",
)
app.include_router(runs_router)
app.include_router(run_authorisations_router)
app.include_router(agent_rehearsals_router)

# Rate limiting, one error shape, security headers, and CORS only when configured (#98). Applied
# here rather than per endpoint so a route added later is covered by default instead of by
# somebody remembering.
install_hardening(app)
app.include_router(candidates_router)
app.include_router(comms_router)
app.include_router(dashboard_router)
app.include_router(reports_router)
app.include_router(session_router)
app.include_router(oauth_router)
app.include_router(source_library_router)
app.include_router(source_checks_router)
app.include_router(action_register_router)
app.include_router(watch_list_router)
app.include_router(exceptions_router)
app.include_router(facts_router)
app.include_router(webhook_router)
app.include_router(site_forms_router)


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
    # Internal-tier evidence fields (#187 / #392): populated only when `depth=internal` is
    # requested by an authorised reviewer/analyst/owner/auditor; `None` at `public` and `member`
    # depths so internal editorial notes and raw tier numbers are withheld from non-internal
    # responses.
    source_tier: int | None = None
    notes: str | None = None
    coverage_warning: str | None = None
    # The structured tariff fields (#185). They reached `ExplainerAnswer` in #273 but stopped
    # there, so every HTTP caller still got `treatment` prose and had to re-parse it, which is the
    # thing #185 exists to stop. `extra="forbid"` meant they could not arrive by accident.
    #
    # Free text, not parsed percentages, because the source states some as ranges ("5.5%-11%") and
    # others as within-quota figures that lose meaning as one number. `None` means "not sourced
    # for this entry", never "zero" or "unchanged" - see `TariffOutcome` in apps/fta/corpus.py.
    direction: str | None = None
    current_tariff: str | None = None
    fta_commencement_tariff: str | None = None
    staged_reductions: str | None = None
    final_tariff: str | None = None
    implementation_period_years: int | None = None


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
    depth: Depth = Depth.PUBLIC
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


def _answer_out(
    answer: PublicAnswer | MemberAnswer | InternalAnswer | ExplainerAnswer,
    *,
    entry_id: str,
    confirmed: bool,
) -> AnswerOut:
    source_tier = answer.source_tier if isinstance(answer, InternalAnswer) else None
    notes = answer.notes if isinstance(answer, InternalAnswer) else None
    return AnswerOut(
        id=entry_id,
        topic=answer.topic,
        sector=answer.sector,
        treatment=answer.treatment,
        confirmed=confirmed,
        citation=answer.citation,
        verified_at=answer.verified_at,
        status_line=answer.status_line,
        jurisdiction=answer.jurisdiction,
        next_step=answer.next_step,
        disclaimer=answer.disclaimer,
        confidence=answer.confidence.value,
        confidence_meaning=answer.confidence_meaning,
        source_tier=source_tier,
        notes=notes,
        coverage_warning=answer.coverage_warning,
        # `.value` on the enum, so the wire carries "NZ exports to India" rather than a Python
        # member name. The direction is not decoration: "NZ removes all tariffs on Indian imports"
        # and "India phases out its tariff on NZ wool" are both true and are not the same fact.
        direction=answer.direction.value if answer.direction else None,
        current_tariff=answer.current_tariff,
        fta_commencement_tariff=answer.fta_commencement_tariff,
        staged_reductions=answer.staged_reductions,
        final_tariff=answer.final_tariff,
        implementation_period_years=answer.implementation_period_years,
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


def resolve_fta_principal(
    request: Request,
    depth: Depth = Query(default=Depth.PUBLIC),
    repository: SessionRepository | None = Depends(get_session_repository),
) -> Principal | None:
    """The session for `member`/`internal` depth; `None` for public, which never reads the cookie.

    Public is resolved without the cookie so an expired session in the browser cannot turn the
    unauthenticated answer into a 401.
    """
    if depth is Depth.PUBLIC:
        return None
    session_id = request.cookies.get(session_cookie_scheme.model.name)
    if not session_id:
        return None
    return require_principal(session_id=session_id, repository=repository)


@app.get(
    "/api/fta/query",
    response_model=FtaQueryResponse,
    tags=["FTA Explainer"],
    responses={
        401: {"description": "Authentication required for `member` or `internal` depth."},
        403: {"description": "Authenticated caller lacks the role required for the requested depth."},
    },
)
def fta_query(
    q: str = Query(
        ...,
        max_length=500,
        description="A sector or product question, e.g. 'dairy' or 'manuka honey'.",
    ),
    depth: Depth = Query(
        default=Depth.PUBLIC,
        description=(
            "Audience depth level (#187 / #392): 'public' (default, unauthenticated), "
            "'member' (requires an authenticated member/staff session), or "
            "'internal' (requires Reviewer, Analyst, SIP Owner, or Auditor role and includes "
            "source_tier and editorial notes)."
        ),
    ),
    principal: Principal | None = Depends(resolve_fta_principal),
) -> FtaQueryResponse:
    """Answers an FTA question from the sourced corpus at the requested `depth`, or escalates.

    A query with no confirmed corpus match is **not** an error: it returns HTTP 200 with
    `status: "no_match"` and the Action Required escalation path. Returning 404 would push
    callers toward an error branch that discards the guidance.
    """
    if depth is not Depth.PUBLIC:
        if principal is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                detail=f"depth '{depth.value}' requires an authenticated session",
            )
        allowed_roles = FTA_INTERNAL_ROLES if depth is Depth.INTERNAL else FTA_MEMBER_ROLES
        try:
            require_roles(principal, *allowed_roles)
        except NotAuthorisedError as error:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error

    base_answers = answer_query(q)
    depth_answers = answer_query_at_depth(q, depth=depth)
    if not depth_answers:
        return FtaQueryResponse(
            status="no_match",
            query=q,
            depth=depth,
            answers=[],
            action_required=_action_required_out(no_match(q)),
        )
    return FtaQueryResponse(
        status="matched",
        query=q,
        depth=depth,
        answers=[
            _answer_out(
                depth_ans,
                entry_id=base_ans.id,
                confirmed=base_ans.confirmed,
            )
            for base_ans, depth_ans in zip(base_answers, depth_answers, strict=True)
        ],
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

    # Publish the Wix site-form webhook payload schema (#45). The route reads raw bytes first so
    # HMAC-SHA256 verification runs before JSON parsing; attaching the Pydantic model schema here
    # keeps `schemas/openapi.json` complete for contract consumers.
    webhook_post = (
        spec.get("paths", {})
        .get("/api/webhooks/wix/site-forms", {})
        .get("post")
    )
    if isinstance(webhook_post, dict):
        components = spec.setdefault("components", {}).setdefault("schemas", {})
        json_schema = SiteFormWebhookIn.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
        for def_name, def_schema in json_schema.pop("$defs", {}).items():
            components.setdefault(def_name, def_schema)
        components["SiteFormWebhookIn"] = json_schema
        webhook_post["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/SiteFormWebhookIn"}
                }
            },
        }
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
