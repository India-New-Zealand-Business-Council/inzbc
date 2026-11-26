"""Postgres persistence for Sponsors and Trade Services (#200).

Implements three operational domain areas from Module 4 of the AIOS programme brief:
- **Sponsor pipeline** (`sponsors`) — tracks prospect-to-renewal lifecycle with a named owner.
- **Benefit delivery with evidence** (`sponsor_benefit_deliveries`) — append-only log of delivered
  benefits tied to an explicit `evidence_ref` so renewal conversations show what was actually
  delivered against what was promised.
- **Trade-service requests & confidentiality-gated introductions** (`trade_service_requests`,
  `trade_introductions`) — enforces fail-closed dual-party consent before any introduction may
  transition to `introduced`.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

from services.api.audit import record_audit


def _audit_actor(actor_id: str) -> tuple[str | None, str | None]:
    """Return `(user_id, reason)` compatible with `audit_log.user_id` UUID FK."""
    try:
        return str(uuid.UUID(actor_id)), None
    except (TypeError, ValueError):
        return None, f"actor={actor_id}"

SPONSOR_STAGES: frozenset[str] = frozenset({"prospect", "proposal", "active", "renewal", "lapsed"})
REQUEST_STATUSES: frozenset[str] = frozenset({"open", "in_progress", "fulfilled", "declined"})
CONFIDENTIALITY_LEVELS: frozenset[str] = frozenset({"internal", "restricted", "board_only"})
INTRODUCTION_STATUSES: frozenset[str] = frozenset({"proposed", "consented", "introduced", "declined"})


class ConsentRequiredError(ValueError):
    """Raised when an introduction attempts to advance to `introduced` without dual consent."""


def _iso(value):
    return value.isoformat() if value is not None else None


@dataclass(frozen=True)
class SponsorRecord:
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


@dataclass(frozen=True)
class BenefitDeliveryRecord:
    id: str
    sponsor_id: str
    benefit_title: str
    promised_summary: str
    evidence_ref: str
    delivered_at: str
    recorded_by: str
    created_at: str


@dataclass(frozen=True)
class TradeServiceRequestRecord:
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


@dataclass(frozen=True)
class IntroductionRecord:
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


def _sponsor_row(row: dict) -> SponsorRecord:
    return SponsorRecord(
        id=str(row["id"]),
        name=row["name"],
        tier=row["tier"],
        stage=row["stage"],
        owner_id=str(row["owner_id"]) if row["owner_id"] else None,
        owner_text=row["owner_text"],
        annual_value_nzd=row["annual_value_nzd"],
        renewal_date=_iso(row["renewal_date"]),
        notes=row["notes"],
        created_at=_iso(row["created_at"]),
        updated_at=_iso(row["updated_at"]),
    )


def _benefit_row(row: dict) -> BenefitDeliveryRecord:
    return BenefitDeliveryRecord(
        id=str(row["id"]),
        sponsor_id=str(row["sponsor_id"]),
        benefit_title=row["benefit_title"],
        promised_summary=row["promised_summary"],
        evidence_ref=row["evidence_ref"],
        delivered_at=_iso(row["delivered_at"]),
        recorded_by=str(row["recorded_by"]),
        created_at=_iso(row["created_at"]),
    )


def _request_row(row: dict) -> TradeServiceRequestRecord:
    return TradeServiceRequestRecord(
        id=str(row["id"]),
        requester_org=row["requester_org"],
        corridor=row["corridor"],
        service_type=row["service_type"],
        summary=row["summary"],
        status=row["status"],
        confidentiality=row["confidentiality"],
        owner_text=row["owner_text"],
        created_at=_iso(row["created_at"]),
        updated_at=_iso(row["updated_at"]),
    )


def _intro_row(row: dict) -> IntroductionRecord:
    return IntroductionRecord(
        id=str(row["id"]),
        sponsor_id=str(row["sponsor_id"]) if row["sponsor_id"] else None,
        request_id=str(row["request_id"]) if row["request_id"] else None,
        party_a_org=row["party_a_org"],
        party_b_org=row["party_b_org"],
        purpose=row["purpose"],
        consent_party_a=bool(row["consent_party_a"]),
        consent_party_b=bool(row["consent_party_b"]),
        confidentiality=row["confidentiality"],
        status=row["status"],
        created_at=_iso(row["created_at"]),
        updated_at=_iso(row["updated_at"]),
    )


def _require_db_url(database_url: str | None) -> str:
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url


class SponsorRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(_require_db_url(self._database_url), row_factory=dict_row)

    def create(
        self,
        name: str,
        tier: str,
        stage: str,
        *,
        actor_id: str,
        owner_id: str | None = None,
        owner_text: str | None = None,
        annual_value_nzd: int | None = None,
        renewal_date: str | None = None,
        notes: str | None = None,
    ) -> SponsorRecord:
        if stage not in SPONSOR_STAGES:
            raise ValueError(f"invalid sponsor stage {stage!r}")
        if not owner_id and not (owner_text and owner_text.strip()):
            raise ValueError("a sponsor must name an owner (owner_id or owner_text)")
        with self._connect() as conn, conn.transaction():
            row = conn.execute(
                """
                insert into sponsors (
                    name, tier, stage, owner_id, owner_text,
                    annual_value_nzd, renewal_date, notes
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s)
                returning id, name, tier, stage, owner_id, owner_text,
                          annual_value_nzd, renewal_date, notes, created_at, updated_at
                """,
                (
                    name.strip(),
                    tier.strip(),
                    stage,
                    owner_id,
                    owner_text.strip() if owner_text else None,
                    annual_value_nzd,
                    renewal_date,
                    notes,
                ),
            ).fetchone()
            record = _sponsor_row(row)
            audit_user_id, audit_reason = _audit_actor(actor_id)
            record_audit(
                conn,
                action="sponsor.create",
                user_id=audit_user_id,
                record_type="sponsor",
                record_id=record.id,
                new_value=json.dumps(
                    {"name": record.name, "tier": record.tier, "stage": record.stage},
                    sort_keys=True,
                ),
                reason=audit_reason,
            )
            return record

    def update_stage(
        self,
        sponsor_id: str,
        stage: str,
        *,
        actor_id: str,
        notes: str | None = None,
    ) -> SponsorRecord:
        if stage not in SPONSOR_STAGES:
            raise ValueError(f"invalid sponsor stage {stage!r}")
        with self._connect() as conn, conn.transaction():
            before = conn.execute(
                "select id, stage from sponsors where id = %s for update", (sponsor_id,)
            ).fetchone()
            if before is None:
                raise KeyError(sponsor_id)
            row = conn.execute(
                """
                update sponsors
                set stage = %s,
                    notes = coalesce(%s, notes),
                    updated_at = now()
                where id = %s
                returning id, name, tier, stage, owner_id, owner_text,
                          annual_value_nzd, renewal_date, notes, created_at, updated_at
                """,
                (stage, notes, sponsor_id),
            ).fetchone()
            record = _sponsor_row(row)
            audit_user_id, audit_reason = _audit_actor(actor_id)
            record_audit(
                conn,
                action="sponsor.stage_update",
                user_id=audit_user_id,
                record_type="sponsor",
                record_id=record.id,
                old_value=json.dumps({"stage": before["stage"]}, sort_keys=True),
                new_value=json.dumps({"stage": record.stage}, sort_keys=True),
                reason=audit_reason,
            )
            return record

    def get(self, sponsor_id: str) -> SponsorRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                select id, name, tier, stage, owner_id, owner_text,
                       annual_value_nzd, renewal_date, notes, created_at, updated_at
                from sponsors where id = %s
                """,
                (sponsor_id,),
            ).fetchone()
            if row is None:
                raise KeyError(sponsor_id)
            return _sponsor_row(row)

    def list_all(self) -> list[SponsorRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select id, name, tier, stage, owner_id, owner_text,
                       annual_value_nzd, renewal_date, notes, created_at, updated_at
                from sponsors order by created_at desc
                """
            ).fetchall()
            return [_sponsor_row(r) for r in rows]

    def record_benefit_delivery(
        self,
        sponsor_id: str,
        *,
        benefit_title: str,
        promised_summary: str,
        evidence_ref: str,
        delivered_at: str,
        actor_id: str,
    ) -> BenefitDeliveryRecord:
        if not evidence_ref.strip():
            raise ValueError("evidence_ref is required to record sponsor benefit delivery")
        with self._connect() as conn, conn.transaction():
            exists = conn.execute("select 1 from sponsors where id = %s", (sponsor_id,)).fetchone()
            if exists is None:
                raise KeyError(sponsor_id)
            row = conn.execute(
                """
                insert into sponsor_benefit_deliveries (
                    sponsor_id, benefit_title, promised_summary,
                    evidence_ref, delivered_at, recorded_by
                )
                values (%s, %s, %s, %s, %s, %s)
                returning id, sponsor_id, benefit_title, promised_summary,
                          evidence_ref, delivered_at, recorded_by, created_at
                """,
                (
                    sponsor_id,
                    benefit_title.strip(),
                    promised_summary.strip(),
                    evidence_ref.strip(),
                    delivered_at,
                    actor_id,
                ),
            ).fetchone()
            record = _benefit_row(row)
            audit_user_id, audit_reason = _audit_actor(actor_id)
            record_audit(
                conn,
                action="sponsor.benefit_delivered",
                user_id=audit_user_id,
                record_type="sponsor_benefit_delivery",
                record_id=record.id,
                new_value=json.dumps(
                    {
                        "sponsor_id": record.sponsor_id,
                        "benefit_title": record.benefit_title,
                        "evidence_ref": record.evidence_ref,
                    },
                    sort_keys=True,
                ),
                reason=audit_reason,
            )
            return record

    def list_benefits(self, sponsor_id: str) -> list[BenefitDeliveryRecord]:
        with self._connect() as conn:
            exists = conn.execute("select 1 from sponsors where id = %s", (sponsor_id,)).fetchone()
            if exists is None:
                raise KeyError(sponsor_id)
            rows = conn.execute(
                """
                select id, sponsor_id, benefit_title, promised_summary,
                       evidence_ref, delivered_at, recorded_by, created_at
                from sponsor_benefit_deliveries
                where sponsor_id = %s
                order by delivered_at desc, created_at desc
                """,
                (sponsor_id,),
            ).fetchall()
            return [_benefit_row(r) for r in rows]


class TradeServiceRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(_require_db_url(self._database_url), row_factory=dict_row)

    def create_request(
        self,
        requester_org: str,
        corridor: str,
        service_type: str,
        summary: str,
        *,
        actor_id: str,
        confidentiality: str = "internal",
        owner_text: str | None = None,
    ) -> TradeServiceRequestRecord:
        if confidentiality not in CONFIDENTIALITY_LEVELS:
            raise ValueError(f"invalid confidentiality level {confidentiality!r}")
        with self._connect() as conn, conn.transaction():
            row = conn.execute(
                """
                insert into trade_service_requests (
                    requester_org, corridor, service_type, summary,
                    status, confidentiality, owner_text
                )
                values (%s, %s, %s, %s, 'open', %s, %s)
                returning id, requester_org, corridor, service_type, summary,
                          status, confidentiality, owner_text, created_at, updated_at
                """,
                (
                    requester_org.strip(),
                    corridor.strip(),
                    service_type.strip(),
                    summary.strip(),
                    confidentiality,
                    owner_text.strip() if owner_text else None,
                ),
            ).fetchone()
            record = _request_row(row)
            audit_user_id, audit_reason = _audit_actor(actor_id)
            record_audit(
                conn,
                action="trade_service.request_create",
                user_id=audit_user_id,
                record_type="trade_service_request",
                record_id=record.id,
                new_value=json.dumps(
                    {
                        "corridor": record.corridor,
                        "service_type": record.service_type,
                        "confidentiality": record.confidentiality,
                    },
                    sort_keys=True,
                ),
                reason=audit_reason,
            )
            return record

    def update_request_status(
        self, request_id: str, status: str, *, actor_id: str
    ) -> TradeServiceRequestRecord:
        if status not in REQUEST_STATUSES:
            raise ValueError(f"invalid request status {status!r}")
        with self._connect() as conn, conn.transaction():
            before = conn.execute(
                "select id, status from trade_service_requests where id = %s for update",
                (request_id,),
            ).fetchone()
            if before is None:
                raise KeyError(request_id)
            row = conn.execute(
                """
                update trade_service_requests
                set status = %s, updated_at = now()
                where id = %s
                returning id, requester_org, corridor, service_type, summary,
                          status, confidentiality, owner_text, created_at, updated_at
                """,
                (status, request_id),
            ).fetchone()
            record = _request_row(row)
            audit_user_id, audit_reason = _audit_actor(actor_id)
            record_audit(
                conn,
                action="trade_service.request_status",
                user_id=audit_user_id,
                record_type="trade_service_request",
                record_id=record.id,
                old_value=json.dumps({"status": before["status"]}, sort_keys=True),
                new_value=json.dumps({"status": record.status}, sort_keys=True),
                reason=audit_reason,
            )
            return record

    def list_requests(self) -> list[TradeServiceRequestRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select id, requester_org, corridor, service_type, summary,
                       status, confidentiality, owner_text, created_at, updated_at
                from trade_service_requests
                order by created_at desc
                """
            ).fetchall()
            return [_request_row(r) for r in rows]

    def create_introduction(
        self,
        party_a_org: str,
        party_b_org: str,
        purpose: str,
        *,
        actor_id: str,
        sponsor_id: str | None = None,
        request_id: str | None = None,
        consent_party_a: bool = False,
        consent_party_b: bool = False,
        confidentiality: str = "restricted",
    ) -> IntroductionRecord:
        if confidentiality not in CONFIDENTIALITY_LEVELS:
            raise ValueError(f"invalid confidentiality level {confidentiality!r}")
        initial_status = "consented" if (consent_party_a and consent_party_b) else "proposed"
        with self._connect() as conn, conn.transaction():
            row = conn.execute(
                """
                insert into trade_introductions (
                    sponsor_id, request_id, party_a_org, party_b_org, purpose,
                    consent_party_a, consent_party_b, confidentiality, status
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning id, sponsor_id, request_id, party_a_org, party_b_org, purpose,
                          consent_party_a, consent_party_b, confidentiality, status,
                          created_at, updated_at
                """,
                (
                    sponsor_id,
                    request_id,
                    party_a_org.strip(),
                    party_b_org.strip(),
                    purpose.strip(),
                    consent_party_a,
                    consent_party_b,
                    confidentiality,
                    initial_status,
                ),
            ).fetchone()
            record = _intro_row(row)
            audit_user_id, audit_reason = _audit_actor(actor_id)
            record_audit(
                conn,
                action="trade_service.introduction_create",
                user_id=audit_user_id,
                record_type="trade_introduction",
                record_id=record.id,
                new_value=json.dumps(
                    {
                        "status": record.status,
                        "confidentiality": record.confidentiality,
                        "dual_consent": record.consent_party_a and record.consent_party_b,
                    },
                    sort_keys=True,
                ),
                reason=audit_reason,
            )
            return record

    def update_introduction_status(
        self,
        introduction_id: str,
        status: str,
        *,
        actor_id: str,
        consent_party_a: bool | None = None,
        consent_party_b: bool | None = None,
    ) -> IntroductionRecord:
        if status not in INTRODUCTION_STATUSES:
            raise ValueError(f"invalid introduction status {status!r}")
        with self._connect() as conn, conn.transaction():
            before = conn.execute(
                """
                select id, status, consent_party_a, consent_party_b
                from trade_introductions
                where id = %s for update
                """,
                (introduction_id,),
            ).fetchone()
            if before is None:
                raise KeyError(introduction_id)
            next_a = before["consent_party_a"] if consent_party_a is None else consent_party_a
            next_b = before["consent_party_b"] if consent_party_b is None else consent_party_b
            if status == "introduced" and not (next_a and next_b):
                raise ConsentRequiredError(
                    "both party_a and party_b consent must be recorded before marking an "
                    "introduction as introduced"
                )
            row = conn.execute(
                """
                update trade_introductions
                set status = %s,
                    consent_party_a = %s,
                    consent_party_b = %s,
                    updated_at = now()
                where id = %s
                returning id, sponsor_id, request_id, party_a_org, party_b_org, purpose,
                          consent_party_a, consent_party_b, confidentiality, status,
                          created_at, updated_at
                """,
                (status, next_a, next_b, introduction_id),
            ).fetchone()
            record = _intro_row(row)
            audit_user_id, audit_reason = _audit_actor(actor_id)
            record_audit(
                conn,
                action="trade_service.introduction_status",
                user_id=audit_user_id,
                record_type="trade_introduction",
                record_id=record.id,
                old_value=json.dumps({"status": before["status"]}, sort_keys=True),
                new_value=json.dumps(
                    {
                        "status": record.status,
                        "dual_consent": record.consent_party_a and record.consent_party_b,
                    },
                    sort_keys=True,
                ),
                reason=audit_reason,
            )
            return record

    def list_introductions(self) -> list[IntroductionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select id, sponsor_id, request_id, party_a_org, party_b_org, purpose,
                       consent_party_a, consent_party_b, confidentiality, status,
                       created_at, updated_at
                from trade_introductions
                order by created_at desc
                """
            ).fetchall()
            return [_intro_row(r) for r in rows]


def get_sponsor_repository() -> SponsorRepository:
    return SponsorRepository()


def get_trade_service_repository() -> TradeServiceRepository:
    return TradeServiceRepository()
