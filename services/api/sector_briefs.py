"""`/api/sector-briefs` endpoints (#194): on-demand Sector Opportunity Briefs.

Thin HTTP wrapper over `apps/sip/core/sector_briefs.py`, reusing the existing SIP-050 scorer
and SIP-185 source register. Every generated brief is strictly advisory (`advisory_only=True`,
`approved=False`, `distribution_permitted=False`).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from apps.sip.core.scoring import ScoringParseError
from apps.sip.core.sector_briefs import (
    SectorCandidateInput,
    build_sector_opportunity_brief,
    list_priority_corridors,
)
from services.api.auth import ANALYST, REVIEWER, SIP_OWNER, STAFF_READ, Principal
from services.api.model_gateway import (
    GatewayCallError,
    GatewayNotConfiguredError,
    ModelGateway,
)
from services.api.session import AUTH_RESPONSES, read_access, write_access

router = APIRouter(
    prefix="/api/sector-briefs",
    tags=["Sector opportunity briefs"],
    responses=AUTH_RESPONSES,
)


def get_sector_model_gateway() -> ModelGateway:
    """FastAPI dependency, overridden in tests."""
    return ModelGateway()


class PriorityCorridorOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str
    focus: str
    register_source_count: int
    mandatory_source_count: int


class SectorCandidateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    headline: str = Field(min_length=1)
    published: str = Field(min_length=1)
    url: str = Field(min_length=1)
    summary: str | None = None


class GenerateSectorBriefIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    corridor_slug: str = Field(min_length=1)
    candidates: list[SectorCandidateIn] = Field(min_length=1)
    min_signal: str = "Medium"


class SectorOpportunityItemOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    source_id: str
    source_name: str
    source_layer: int
    headline: str
    url: str
    published: str
    nz_relevance: int
    india_relevance: int
    member_relevance: int
    signal: str
    confidence: str
    reason: str
    requires_verification: bool


class SectorOpportunityBriefOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    corridor_slug: str
    corridor_name: str
    corridor_focus: str
    evaluated_count: int
    included_count: int
    advisory_only: bool
    requires_human_review: bool
    approved: bool
    distribution_permitted: bool
    notice: str
    items: list[SectorOpportunityItemOut]


@router.get("/corridors", response_model=list[PriorityCorridorOut])
def get_corridors(
    principal: Principal = Depends(read_access(*STAFF_READ)),
) -> list[PriorityCorridorOut]:
    _ = principal
    return [PriorityCorridorOut(**row) for row in list_priority_corridors()]


@router.post("/generate", response_model=SectorOpportunityBriefOut)
def generate_sector_brief(
    body: GenerateSectorBriefIn,
    principal: Principal = Depends(write_access(ANALYST, REVIEWER, SIP_OWNER)),
    gateway: ModelGateway = Depends(get_sector_model_gateway),
) -> SectorOpportunityBriefOut:
    _ = principal
    candidate_inputs = [
        SectorCandidateInput(
            id=c.id,
            source_id=c.source_id,
            headline=c.headline,
            published=c.published,
            url=c.url,
            summary=c.summary,
        )
        for c in body.candidates
    ]
    try:
        brief = build_sector_opportunity_brief(
            gateway,
            corridor_slug=body.corridor_slug,
            candidates=candidate_inputs,
            min_signal=body.min_signal,
        )
    except ValueError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except GatewayNotConfiguredError as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scoring model provider is not configured.",
        ) from error
    except (GatewayCallError, ScoringParseError) as error:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"Sector brief scoring failed closed: {error}",
        ) from error

    return SectorOpportunityBriefOut(
        corridor_slug=brief.corridor_slug,
        corridor_name=brief.corridor_name,
        corridor_focus=brief.corridor_focus,
        evaluated_count=brief.evaluated_count,
        included_count=brief.included_count,
        advisory_only=brief.advisory_only,
        requires_human_review=brief.requires_human_review,
        approved=brief.approved,
        distribution_permitted=brief.distribution_permitted,
        notice=brief.notice,
        items=[
            SectorOpportunityItemOut(
                candidate_id=item.candidate_id,
                source_id=item.source_id,
                source_name=item.source_name,
                source_layer=item.source_layer,
                headline=item.headline,
                url=item.url,
                published=item.published,
                nz_relevance=item.nz_relevance,
                india_relevance=item.india_relevance,
                member_relevance=item.member_relevance,
                signal=item.signal,
                confidence=item.confidence,
                reason=item.reason,
                requires_verification=item.requires_verification,
            )
            for item in brief.items
        ],
    )
