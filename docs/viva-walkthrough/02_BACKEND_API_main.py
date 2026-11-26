# ==============================================================================
# FILE 2 OF 5: BACKEND API ENTRYPOINT (from services/api/main.py)
# HOW IT WORKS:
#   - Single FastAPI server exposing 82 versioned OpenAPI operations.
#   - Global security hardening middleware wraps EVERY route automatically.
#   - Mounts all domain routers: SIP runs, candidates, QA/CEO decisions, FTA, Comms,
#     Dashboard, Sponsors & Trade Services (#200), Sector Briefs (#194), Assistant.
# ==============================================================================

from __future__ import annotations

from datetime import date                                      # Typed date validation for tariff verification dates
from fastapi import FastAPI                                    # Core ASGI web framework
from pydantic import BaseModel, ConfigDict                     # Strict runtime schema validation (Pydantic v2)

# --- Domain Routers (each file owns one bounded business domain) ---
from services.api.agent_rehearsals import router as agent_rehearsals_router   # Safe dry-run coordinator rehearsals (PR #449)
from services.api.assistant import router as assistant_router                 # Read-only Platform Assistant (no write tools, PR #583)
from services.api.auth import STAFF_READ                                      # Centralised RBAC role sets
from services.api.candidates import router as candidates_router               # News candidate capture, scoring & verification (SoD 403)
from services.api.comms import router as comms_router                         # SSE streaming Comms drafting behind named-reviewer gate (#65)
from services.api.dashboard import router as dashboard_router                 # Executive Dashboard KPIs & control status
from services.api.facts import facts_router                                   # Verified bilateral trade facts
from services.api.hardening import install as install_hardening               # Global rate limit, security headers, CORS, uniform errors
from services.api.oauth import router as oauth_router                         # OAuth login flow
from services.api.registers import (                                          # Governance registers:
    action_register_router,                                                   #   - Open follow-up actions
    exceptions_router,                                                        #   - Recorded policy exceptions
    watch_list_router,                                                        #   - Ongoing trade watch items
)
from services.api.reports import router as reports_router                     # Brief assembly, QA sign-off, CEO ruling & distribution gate
from services.api.run_authorisations import router as run_authorisations_router  # Explicit human launch authority for daily runs
from services.api.runs import router as runs_router                           # SIP daily run lifecycle CRUD & state queries
from services.api.sector_briefs import router as sector_briefs_router         # Sector Opportunity Briefs (#194, PR #582)
from services.api.session import router as session_router                     # HTTP-only session cookie auth
from services.api.site_forms import site_forms_router, webhook_router         # Public website form receiver (#40/#45, PR #433)
from services.api.source_checks import router as source_checks_router         # SIP-185 112-source verification checklist (PR #446)
from services.api.source_library import router as source_library_router       # Curated mandatory source register
from services.api.sponsors import sponsors_router, trade_services_router      # Sponsors & dual-consent Trade Services (#200, PR #582/#588)

# --- RBAC Depth Tiers for FTA Explainer (/api/fta/query) ---
# Public = unauthenticated summary; Member = any signed-in staff; Internal = editorial/audit evidence
FTA_MEMBER_ROLES: frozenset[str] = STAFF_READ
FTA_INTERNAL_ROLES: frozenset[str] = frozenset({"Analyst", "Reviewer", "SIP Owner", "Auditor"})

# --- 1. Create FastAPI Application ---
app = FastAPI(
    title="INZBC API",
    version="0.1.0",
    summary="Trade intelligence and FTA services for the India New Zealand Business Council.",
)

# --- 2. Mount Core Orchestration & Assistant Routers ---
app.include_router(runs_router)                # /api/runs/* (daily SIP run lifecycle)
app.include_router(run_authorisations_router)  # /api/runs/{id}/authorise (human launch gate)
app.include_router(agent_rehearsals_router)    # /api/agent/rehearsals (deterministic dry-run UI)
app.include_router(assistant_router)           # /api/assistant/* (read-only Postgres Q&A, refuses writes)

# --- 3. Install Global Security Hardening Middleware ---
# Applied globally to `app` so any future route gets rate limiting, security headers,
# strict CORS, and uniform JSON errors automatically by default.
install_hardening(app)

# --- 4. Mount All Remaining Domain Routers (Total = 82 OpenAPI Operations) ---
app.include_router(candidates_router)          # News candidate verification + Segregation of Duties (HTTP 403)
app.include_router(comms_router)               # Comms Assistant SSE stream + mandatory deletion-reason dialog
app.include_router(dashboard_router)           # Platform Overview & Executive Dashboard metrics
app.include_router(reports_router)             # Brief Builder, QA Review, CEO Ruling, Distribution Release Gate
app.include_router(session_router)             # Login / logout / current principal session
app.include_router(oauth_router)               # OAuth callback & token exchange
app.include_router(source_library_router)      # 112 mandatory SIP-185 source catalog
app.include_router(source_checks_router)       # Per-run source check outcomes
app.include_router(action_register_router)     # Governance action register
app.include_router(watch_list_router)          # Bilateral trade watch list
app.include_router(exceptions_router)          # Logged exceptions
app.include_router(facts_router)               # Grounded bilateral facts
app.include_router(webhook_router)             # Inbound Wix/public-site form webhook
app.include_router(site_forms_router)          # Staff review queue for inbound site forms
app.include_router(sector_briefs_router)       # Sector Opportunity Briefs (#194)
app.include_router(sponsors_router)            # Sponsors directory (#200)
app.include_router(trade_services_router)      # Trade Services & dual-consent introductions (#200)


# --- 5. Example Strict Pydantic Response Contract (FTA Explainer) ---
class AnswerOut(BaseModel):
    """A sourced FTA finding. Every field is verified evidence—never free-form LLM invention."""

    model_config = ConfigDict(extra="forbid")  # Rejects any unexpected/unvalidated fields at runtime

    id: str                                    # Stable corpus ID (UI keys off this, never topic text)
    topic: str                                 # Matched tariff/trade topic
    sector: str                                # Sector classification (e.g., Dairy, Horticulture)
    treatment: str                             # Human-readable tariff treatment summary
    confirmed: bool                            # Always True for confirmed entries (explicit on wire)
    citation: str                              # Exact legal/FTA clause citation
    verified_at: date                          # Last human verification date
    status_line: str                           # Current agreement status banner
    jurisdiction: str                          # NZ / India / Bilateral
    next_step: str                             # Actionable member guidance
    disclaimer: str                            # Mandatory legal disclaimer
    confidence: str                            # Retrieval confidence tier
    confidence_meaning: str                    # Plain-English explanation of confidence tier

    # Internal-only editorial fields (populated ONLY when role is in FTA_INTERNAL_ROLES)
    source_tier: int | None = None
    notes: str | None = None
    coverage_warning: str | None = None

    # Structured tariff schedule fields (prevents frontend from having to regex-parse prose)
    direction: str | None = None               # NZ -> India or India -> NZ
    current_tariff: str | None = None          # Baseline duty before FTA
    fta_commencement_tariff: str | None = None # Day-1 FTA duty
    staged_reductions: str | None = None       # Phase-down schedule
    final_tariff: str | None = None            # End-state duty
    implementation_period_years: int | None = None
