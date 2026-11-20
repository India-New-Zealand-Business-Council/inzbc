"""`/api/sponsors` and `/api/trade-services` endpoints (#200).

Thin HTTP wrappers over `services/api/sponsors_persistence.py`:
- Sponsor pipeline & append-only benefit delivery evidence (`/api/sponsors`)
- Trade-service requests & confidentiality/dual-consent gated introductions (`/api/trade-services`)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from services.api.auth import ANALYST, REVIEWER, SIP_OWNER, STAFF_READ, Principal
from services.api.session import AUTH_RESPONSES, read_access, write_access
from services.api.sponsors_persistence import (
    BenefitDeliveryRecord,
    ConsentRequiredError,
    IntroductionRecord,
    SponsorRecord,
    SponsorRepository,
    TradeServiceRepository,
    TradeServiceRequestRecord,
    get_sponsor_repository,
    get_trade_service_repository,
)

sponsors_router = APIRouter(
    prefix="/api/sponsors",
    tags=["Sponsors"],
    responses=AUTH_RESPONSES,
)

trade_services_router = APIRouter(
    prefix="/api/trade-services",
    tags=["Trade services"],
    responses=AUTH_RESPONSES,
)


def _not_found(kind: str, item_id: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"no {kind} {item_id!r}")


class CreateSponsorIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    tier: str = Field(min_length=1)
    stage: str = "prospect"
    owner_id: str | None = None
    owner_text: str | None = None
    annual_value_nzd: int | None = Field(default=None, ge=0)
    renewal_date: str | None = None
    notes: str | None = None


class UpdateSponsorStageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str = Field(min_length=1)
    notes: str | None = None


class SponsorOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    tier: str
    stage: str
    owner_id: str | None
    owner_text: str | None
    annual_value_nzd: int | None
    renewal_date: str | None
    notes: str | None
    created_at: str
    updated_at: str


class RecordBenefitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    benefit_title: str = Field(min_length=1)
    promised_summary: str = Field(min_length=1)
    evidence_ref: str = Field(min_length=1)
    delivered_at: str = Field(min_length=1)


class BenefitDeliveryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    sponsor_id: str
    benefit_title: str
    promised_summary: str
    evidence_ref: str
    delivered_at: str
    recorded_by: str
    created_at: str


class CreateTradeRequestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requester_org: str = Field(min_length=1)
    corridor: str = Field(min_length=1)
    service_type: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    confidentiality: str = "internal"
    owner_text: str | None = None


class UpdateTradeRequestStatusIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(min_length=1)


class TradeServiceRequestOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    requester_org: str
    corridor: str
    service_type: str
    summary: str
    status: str
    confidentiality: str
    owner_text: str | None
    created_at: str
    updated_at: str


class CreateIntroductionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    party_a_org: str = Field(min_length=1)
    party_b_org: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    sponsor_id: str | None = None
    request_id: str | None = None
    consent_party_a: bool = False
    consent_party_b: bool = False
    confidentiality: str = "restricted"


class UpdateIntroductionStatusIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(min_length=1)
    consent_party_a: bool | None = None
    consent_party_b: bool | None = None


class IntroductionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    sponsor_id: str | None
    request_id: str | None
    party_a_org: str
    party_b_org: str
    purpose: str
    consent_party_a: bool
    consent_party_b: bool
    confidentiality: str
    status: str
    created_at: str
    updated_at: str


def _sponsor_out(record: SponsorRecord) -> SponsorOut:
    return SponsorOut(
        id=record.id,
        name=record.name,
        tier=record.tier,
        stage=record.stage,
        owner_id=record.owner_id,
        owner_text=record.owner_text,
        annual_value_nzd=record.annual_value_nzd,
        renewal_date=record.renewal_date,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _benefit_out(record: BenefitDeliveryRecord) -> BenefitDeliveryOut:
    return BenefitDeliveryOut(
        id=record.id,
        sponsor_id=record.sponsor_id,
        benefit_title=record.benefit_title,
        promised_summary=record.promised_summary,
        evidence_ref=record.evidence_ref,
        delivered_at=record.delivered_at,
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )


def _request_out(record: TradeServiceRequestRecord) -> TradeServiceRequestOut:
    return TradeServiceRequestOut(
        id=record.id,
        requester_org=record.requester_org,
        corridor=record.corridor,
        service_type=record.service_type,
        summary=record.summary,
        status=record.status,
        confidentiality=record.confidentiality,
        owner_text=record.owner_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _intro_out(record: IntroductionRecord) -> IntroductionOut:
    return IntroductionOut(
        id=record.id,
        sponsor_id=record.sponsor_id,
        request_id=record.request_id,
        party_a_org=record.party_a_org,
        party_b_org=record.party_b_org,
        purpose=record.purpose,
        consent_party_a=record.consent_party_a,
        consent_party_b=record.consent_party_b,
        confidentiality=record.confidentiality,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@sponsors_router.post("", response_model=SponsorOut, status_code=201)
def create_sponsor(
    body: CreateSponsorIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: SponsorRepository = Depends(get_sponsor_repository),
) -> SponsorOut:
    try:
        record = repo.create(
            body.name,
            body.tier,
            body.stage,
            actor_id=principal.user_id,
            owner_id=body.owner_id,
            owner_text=body.owner_text,
            annual_value_nzd=body.annual_value_nzd,
            renewal_date=body.renewal_date,
            notes=body.notes,
        )
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return _sponsor_out(record)


@sponsors_router.get("", response_model=list[SponsorOut])
def list_sponsors(
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: SponsorRepository = Depends(get_sponsor_repository),
) -> list[SponsorOut]:
    _ = principal
    return [_sponsor_out(r) for r in repo.list_all()]


@sponsors_router.get("/{sponsor_id}", response_model=SponsorOut)
def get_sponsor(
    sponsor_id: str,
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: SponsorRepository = Depends(get_sponsor_repository),
) -> SponsorOut:
    _ = principal
    try:
        return _sponsor_out(repo.get(sponsor_id))
    except KeyError as error:
        raise _not_found("sponsor", sponsor_id) from error


@sponsors_router.post("/{sponsor_id}/stage", response_model=SponsorOut)
def update_sponsor_stage(
    sponsor_id: str,
    body: UpdateSponsorStageIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: SponsorRepository = Depends(get_sponsor_repository),
) -> SponsorOut:
    try:
        return _sponsor_out(
            repo.update_stage(
                sponsor_id, body.stage, actor_id=principal.user_id, notes=body.notes
            )
        )
    except KeyError as error:
        raise _not_found("sponsor", sponsor_id) from error
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@sponsors_router.post(
    "/{sponsor_id}/benefits", response_model=BenefitDeliveryOut, status_code=201
)
def record_sponsor_benefit(
    sponsor_id: str,
    body: RecordBenefitIn,
    principal: Principal = Depends(write_access(ANALYST, REVIEWER, SIP_OWNER)),
    repo: SponsorRepository = Depends(get_sponsor_repository),
) -> BenefitDeliveryOut:
    try:
        return _benefit_out(
            repo.record_benefit_delivery(
                sponsor_id,
                benefit_title=body.benefit_title,
                promised_summary=body.promised_summary,
                evidence_ref=body.evidence_ref,
                delivered_at=body.delivered_at,
                actor_id=principal.user_id,
            )
        )
    except KeyError as error:
        raise _not_found("sponsor", sponsor_id) from error
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@sponsors_router.get("/{sponsor_id}/benefits", response_model=list[BenefitDeliveryOut])
def list_sponsor_benefits(
    sponsor_id: str,
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: SponsorRepository = Depends(get_sponsor_repository),
) -> list[BenefitDeliveryOut]:
    _ = principal
    try:
        return [_benefit_out(r) for r in repo.list_benefits(sponsor_id)]
    except KeyError as error:
        raise _not_found("sponsor", sponsor_id) from error


@trade_services_router.post("/requests", response_model=TradeServiceRequestOut, status_code=201)
def create_trade_request(
    body: CreateTradeRequestIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: TradeServiceRepository = Depends(get_trade_service_repository),
) -> TradeServiceRequestOut:
    try:
        return _request_out(
            repo.create_request(
                body.requester_org,
                body.corridor,
                body.service_type,
                body.summary,
                actor_id=principal.user_id,
                confidentiality=body.confidentiality,
                owner_text=body.owner_text,
            )
        )
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@trade_services_router.get("/requests", response_model=list[TradeServiceRequestOut])
def list_trade_requests(
    principal: Principal = Depends(read_access(*STAFF_READ)),
    repo: TradeServiceRepository = Depends(get_trade_service_repository),
) -> list[TradeServiceRequestOut]:
    _ = principal
    return [_request_out(r) for r in repo.list_requests()]


@trade_services_router.post(
    "/requests/{request_id}/status", response_model=TradeServiceRequestOut
)
def update_trade_request_status(
    request_id: str,
    body: UpdateTradeRequestStatusIn,
    principal: Principal = Depends(write_access(ANALYST, SIP_OWNER)),
    repo: TradeServiceRepository = Depends(get_trade_service_repository),
) -> TradeServiceRequestOut:
    try:
        return _request_out(
            repo.update_request_status(request_id, body.status, actor_id=principal.user_id)
        )
    except KeyError as error:
        raise _not_found("trade service request", request_id) from error
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@trade_services_router.post(
    "/introductions", response_model=IntroductionOut, status_code=201
)
def create_introduction(
    body: CreateIntroductionIn,
    principal: Principal = Depends(write_access(REVIEWER, SIP_OWNER)),
    repo: TradeServiceRepository = Depends(get_trade_service_repository),
) -> IntroductionOut:
    try:
        return _intro_out(
            repo.create_introduction(
                body.party_a_org,
                body.party_b_org,
                body.purpose,
                actor_id=principal.user_id,
                sponsor_id=body.sponsor_id,
                request_id=body.request_id,
                consent_party_a=body.consent_party_a,
                consent_party_b=body.consent_party_b,
                confidentiality=body.confidentiality,
            )
        )
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@trade_services_router.get("/introductions", response_model=list[IntroductionOut])
def list_introductions(
    principal: Principal = Depends(read_access(REVIEWER, SIP_OWNER)),
    repo: TradeServiceRepository = Depends(get_trade_service_repository),
) -> list[IntroductionOut]:
    _ = principal
    return [_intro_out(r) for r in repo.list_introductions()]


@trade_services_router.post(
    "/introductions/{introduction_id}/status", response_model=IntroductionOut
)
def update_introduction_status(
    introduction_id: str,
    body: UpdateIntroductionStatusIn,
    principal: Principal = Depends(write_access(REVIEWER, SIP_OWNER)),
    repo: TradeServiceRepository = Depends(get_trade_service_repository),
) -> IntroductionOut:
    try:
        return _intro_out(
            repo.update_introduction_status(
                introduction_id,
                body.status,
                actor_id=principal.user_id,
                consent_party_a=body.consent_party_a,
                consent_party_b=body.consent_party_b,
            )
        )
    except KeyError as error:
        raise _not_found("introduction", introduction_id) from error
    except ConsentRequiredError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
