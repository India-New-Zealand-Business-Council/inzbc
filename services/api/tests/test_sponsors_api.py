"""API unit tests for `/api/sponsors` and `/api/trade-services` (#200)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from services.api.main import app
from services.api.sponsors import get_sponsor_repository, get_trade_service_repository
from services.api.sponsors_persistence import (
    SPONSOR_STAGES,
    BenefitDeliveryRecord,
    ConsentRequiredError,
    IntroductionRecord,
    SponsorRecord,
    TradeServiceRequestRecord,
)


class _FakeSponsorRepo:
    def __init__(self) -> None:
        self._sponsors: dict[str, SponsorRecord] = {}
        self._benefits: dict[str, list[BenefitDeliveryRecord]] = {}

    def create(self, name, tier, stage, *, actor_id, **kwargs) -> SponsorRecord:
        _ = actor_id
        if stage not in SPONSOR_STAGES:
            raise ValueError(f"invalid stage {stage!r}")
        if not kwargs.get("owner_id") and not (kwargs.get("owner_text") or "").strip():
            raise ValueError("owner required")
        record = SponsorRecord(
            id=str(uuid.uuid4()),
            name=name,
            tier=tier,
            stage=stage,
            owner_id=kwargs.get("owner_id"),
            owner_text=kwargs.get("owner_text"),
            annual_value_nzd=kwargs.get("annual_value_nzd"),
            renewal_date=kwargs.get("renewal_date"),
            notes=kwargs.get("notes"),
            created_at="2026-11-20T00:00:00+00:00",
            updated_at="2026-11-20T00:00:00+00:00",
        )
        self._sponsors[record.id] = record
        self._benefits[record.id] = []
        return record

    def update_stage(self, sponsor_id, stage, *, actor_id, notes=None) -> SponsorRecord:
        _ = actor_id
        if stage not in SPONSOR_STAGES:
            raise ValueError(f"invalid stage {stage!r}")
        cur = self._sponsors[sponsor_id]
        updated = SponsorRecord(
            id=cur.id,
            name=cur.name,
            tier=cur.tier,
            stage=stage,
            owner_id=cur.owner_id,
            owner_text=cur.owner_text,
            annual_value_nzd=cur.annual_value_nzd,
            renewal_date=cur.renewal_date,
            notes=notes if notes is not None else cur.notes,
            created_at=cur.created_at,
            updated_at="2026-11-20T01:00:00+00:00",
        )
        self._sponsors[sponsor_id] = updated
        return updated

    def get(self, sponsor_id) -> SponsorRecord:
        return self._sponsors[sponsor_id]

    def list_all(self) -> list[SponsorRecord]:
        return list(self._sponsors.values())

    def record_benefit_delivery(
        self,
        sponsor_id,
        *,
        benefit_title,
        promised_summary,
        evidence_ref,
        delivered_at,
        actor_id,
    ) -> BenefitDeliveryRecord:
        if sponsor_id not in self._sponsors:
            raise KeyError(sponsor_id)
        if not evidence_ref.strip():
            raise ValueError("evidence_ref is required")
        rec = BenefitDeliveryRecord(
            id=str(uuid.uuid4()),
            sponsor_id=sponsor_id,
            benefit_title=benefit_title,
            promised_summary=promised_summary,
            evidence_ref=evidence_ref,
            delivered_at=delivered_at,
            recorded_by=actor_id,
            created_at="2026-11-20T02:00:00+00:00",
        )
        self._benefits[sponsor_id].append(rec)
        return rec

    def list_benefits(self, sponsor_id) -> list[BenefitDeliveryRecord]:
        if sponsor_id not in self._sponsors:
            raise KeyError(sponsor_id)
        return list(self._benefits[sponsor_id])


class _FakeTradeServiceRepo:
    def __init__(self) -> None:
        self._requests: dict[str, TradeServiceRequestRecord] = {}
        self._intros: dict[str, IntroductionRecord] = {}

    def create_request(
        self, requester_org, corridor, service_type, summary, *, actor_id, **kwargs
    ) -> TradeServiceRequestRecord:
        _ = actor_id
        rec = TradeServiceRequestRecord(
            id=str(uuid.uuid4()),
            requester_org=requester_org,
            corridor=corridor,
            service_type=service_type,
            summary=summary,
            status="open",
            confidentiality=kwargs.get("confidentiality", "internal"),
            owner_text=kwargs.get("owner_text"),
            created_at="2026-11-20T00:00:00+00:00",
            updated_at="2026-11-20T00:00:00+00:00",
        )
        self._requests[rec.id] = rec
        return rec

    def update_request_status(self, request_id, status, *, actor_id) -> TradeServiceRequestRecord:
        _ = actor_id
        cur = self._requests[request_id]
        updated = TradeServiceRequestRecord(
            id=cur.id,
            requester_org=cur.requester_org,
            corridor=cur.corridor,
            service_type=cur.service_type,
            summary=cur.summary,
            status=status,
            confidentiality=cur.confidentiality,
            owner_text=cur.owner_text,
            created_at=cur.created_at,
            updated_at="2026-11-20T01:00:00+00:00",
        )
        self._requests[request_id] = updated
        return updated

    def list_requests(self) -> list[TradeServiceRequestRecord]:
        return list(self._requests.values())

    def create_introduction(
        self, party_a_org, party_b_org, purpose, *, actor_id, **kwargs
    ) -> IntroductionRecord:
        _ = actor_id
        ca = bool(kwargs.get("consent_party_a", False))
        cb = bool(kwargs.get("consent_party_b", False))
        rec = IntroductionRecord(
            id=str(uuid.uuid4()),
            sponsor_id=kwargs.get("sponsor_id"),
            request_id=kwargs.get("request_id"),
            party_a_org=party_a_org,
            party_b_org=party_b_org,
            purpose=purpose,
            consent_party_a=ca,
            consent_party_b=cb,
            confidentiality=kwargs.get("confidentiality", "restricted"),
            status="consented" if (ca and cb) else "proposed",
            created_at="2026-11-20T00:00:00+00:00",
            updated_at="2026-11-20T00:00:00+00:00",
        )
        self._intros[rec.id] = rec
        return rec

    def update_introduction_status(
        self,
        introduction_id,
        status,
        *,
        actor_id,
        consent_party_a=None,
        consent_party_b=None,
    ) -> IntroductionRecord:
        _ = actor_id
        cur = self._intros[introduction_id]
        next_a = cur.consent_party_a if consent_party_a is None else consent_party_a
        next_b = cur.consent_party_b if consent_party_b is None else consent_party_b
        if status == "introduced" and not (next_a and next_b):
            raise ConsentRequiredError("dual consent required")
        updated = IntroductionRecord(
            id=cur.id,
            sponsor_id=cur.sponsor_id,
            request_id=cur.request_id,
            party_a_org=cur.party_a_org,
            party_b_org=cur.party_b_org,
            purpose=cur.purpose,
            consent_party_a=next_a,
            consent_party_b=next_b,
            confidentiality=cur.confidentiality,
            status=status,
            created_at=cur.created_at,
            updated_at="2026-11-20T01:00:00+00:00",
        )
        self._intros[introduction_id] = updated
        return updated

    def list_introductions(self) -> list[IntroductionRecord]:
        return list(self._intros.values())


@pytest.fixture
def client():
    sponsor_repo = _FakeSponsorRepo()
    trade_repo = _FakeTradeServiceRepo()
    app.dependency_overrides[get_sponsor_repository] = lambda: sponsor_repo
    app.dependency_overrides[get_trade_service_repository] = lambda: trade_repo
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.pop(get_sponsor_repository, None)
    app.dependency_overrides.pop(get_trade_service_repository, None)


def test_sponsor_lifecycle_and_benefit_delivery_evidence(client: TestClient) -> None:
    created = client.post(
        "/api/sponsors",
        json={
            "name": "Aotearoa Logistics Ltd",
            "tier": "Gold",
            "stage": "prospect",
            "owner_text": "Sunil Kaushal",
            "annual_value_nzd": 25000,
        },
    )
    assert created.status_code == 201
    sponsor_id = created.json()["id"]

    advanced = client.post(
        f"/api/sponsors/{sponsor_id}/stage",
        json={"stage": "active", "notes": "Signed annual sponsorship"},
    )
    assert advanced.status_code == 200
    assert advanced.json()["stage"] == "active"

    benefit = client.post(
        f"/api/sponsors/{sponsor_id}/benefits",
        json={
            "benefit_title": "Mumbai Delegation Keynote Slot",
            "promised_summary": "10-minute keynote at Q4 bilateral summit",
            "evidence_ref": "docs/events/2026-q4-summit-programme.pdf",
            "delivered_at": "2026-11-18T05:00:00Z",
        },
    )
    assert benefit.status_code == 201

    listed = client.get(f"/api/sponsors/{sponsor_id}/benefits")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["evidence_ref"] == "docs/events/2026-q4-summit-programme.pdf"


def test_sponsor_missing_owner_rejected_with_422(client: TestClient) -> None:
    res = client.post(
        "/api/sponsors",
        json={"name": "No Owner Corp", "tier": "Silver", "stage": "prospect"},
    )
    assert res.status_code == 422


def test_trade_introduction_requires_dual_consent_before_introduced(client: TestClient) -> None:
    req = client.post(
        "/api/trade-services/requests",
        json={
            "requester_org": "NZ KiwiTech",
            "corridor": "tech-and-digital",
            "service_type": "partner-matching",
            "summary": "Seeking regulated Indian fintech distribution partner",
            "confidentiality": "restricted",
        },
    )
    assert req.status_code == 201
    req_id = req.json()["id"]

    intro = client.post(
        "/api/trade-services/introductions",
        json={
            "request_id": req_id,
            "party_a_org": "NZ KiwiTech",
            "party_b_org": "Bengaluru PayCorp",
            "purpose": "Bilateral distribution partnership",
            "consent_party_a": True,
            "consent_party_b": False,
        },
    )
    assert intro.status_code == 201
    intro_id = intro.json()["id"]
    assert intro.json()["status"] == "proposed"

    # Attempting to mark introduced without party B consent fails closed with 403
    refused = client.post(
        f"/api/trade-services/introductions/{intro_id}/status",
        json={"status": "introduced"},
    )
    assert refused.status_code == 403

    # Recording party B consent allows advancing to introduced
    allowed = client.post(
        f"/api/trade-services/introductions/{intro_id}/status",
        json={"status": "introduced", "consent_party_b": True},
    )
    assert allowed.status_code == 200
    assert allowed.json()["status"] == "introduced"
    assert allowed.json()["consent_party_b"] is True
