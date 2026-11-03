"""Disabled-by-construction SIP atomic candidate importer (#528).

This is an internal repository method, NOT an HTTP route or a capture staging
facility. It ONLY accepts an immutable, independently staged server-held batch.
The upstream capture evidence/authorisation must be verified before staging;
inserting a row manually is not SIP-191 permission or a live SIP run.

Legacy per-item capture must use the same runs FOR UPDATE lock and refuse
production writes (#526) before this code can be considered for activation.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from apps.sip.collector.capture_manifest import _source_url
from apps.sip.collector.import_capture import _require_confirmed_source_note
from apps.sip.collector.source_register import MANDATORY_SOURCES
from services.api.audit import record_audit
from services.api.import_contract import (
    ImportBatchIn,
    ImportOutcome,
    require_consistent_batch,
)
from services.api.source_checks import RecordSourceCheckIn


class ImportBlockedError(ValueError):
    """The requested import cannot pass immutable evidence or authority checks."""


class CapturedArticleEvidence(BaseModel):
    """Original URL, source and publication time independent of the candidate batch."""

    model_config = ConfigDict(extra="forbid")
    url: str = Field(min_length=1, max_length=2048)
    source_id: uuid.UUID
    published_at: datetime

    @field_validator("url")
    @classmethod
    def require_public_url(cls, value: str) -> str:
        _source_url(value)
        return value

    @field_validator("published_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("original capture publication time requires a timezone")
        return value


class ImportRepository:
    def __init__(self, database_url: str | None = None):
        self._database_url = database_url or os.environ["DATABASE_URL"]

    def import_reviewed(self, batch: ImportBatchIn, *, actor_id: str) -> ImportOutcome:
        """Commit all candidates, audits and a deterministic claim atomically.

        Deliberately not wired into FastAPI. The import must be authorised by
        deployment/owner review after the separate trusted capture-staging path
        and the legacy-write exclusion have been implemented and tested.
        """
        run_id = str(batch.run_id)
        try:
            actor = uuid.UUID(actor_id)
        except (ValueError, TypeError) as exc:
            raise ImportBlockedError("actor identity must be a UUID") from exc
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            # Single serialisation point for both batch imports and legacy
            # candidate capture. An independent second writer waits here.
            run = conn.execute(
                "select id, version, state, production_enabled, "
                "coverage_start_utc, coverage_end_utc "
                "from runs where id = %s for update",
                (run_id,),
            ).fetchone()
            if run is None:
                raise KeyError(f"no run {run_id!r}")

            authorised_actor = conn.execute(
                "select 1 from users u "
                "join user_roles ur on ur.user_id = u.id "
                "join roles r on r.id = ur.role_id "
                "where u.id = %s and u.active = true and ur.enabled = true "
                "and r.name in ('Analyst', 'SIP Owner') limit 1",
                (actor,),
            ).fetchone()
            if authorised_actor is None:
                raise PermissionError("import actor has no active SIP analyst/owner role")

            if run["production_enabled"] is not True:
                raise ImportBlockedError("production SIP import is not enabled on this run")

            committed = conn.execute(
                "select claim_key, articles_sha256, candidate_count "
                "from sip_import_claims where run_id = %s",
                (run_id,),
            ).fetchone()
            if committed is not None:
                stored = conn.execute(
                    "select batch_payload, articles_sha256 from sip_import_evidence "
                    "where run_id = %s", (run_id,),
                ).fetchone()
                if (stored is None or stored["articles_sha256"] != batch.articles_sha256
                        or ImportBatchIn.model_validate(stored["batch_payload"]) != batch):
                    raise ImportBlockedError("replayed request differs from immutable capture")
                count = conn.execute(
                    "select count(*) as n from candidates where run_id = %s",
                    (run_id,),
                ).fetchone()["n"]
                if (committed["claim_key"] != batch.claim_key
                        or committed["articles_sha256"] != batch.articles_sha256
                        or committed["candidate_count"] != count):
                    raise ImportBlockedError("conflicting or inconsistent committed SIP import")
                return ImportOutcome(
                    run_id=batch.run_id,
                    articles_sha256=batch.articles_sha256,
                    claim_key=batch.claim_key,
                    candidate_count=count,
                    replay=True,
                )

            launch = conn.execute(
                "select 1 from run_authorisations "
                "where run_id = %s and kind = 'Launch' limit 1",
                (run_id,),
            ).fetchone()
            if launch is None:
                raise ImportBlockedError("recorded run launch authority is missing")

            evidence = conn.execute(
                "select articles_sha256, batch_payload, captured_articles, "
                "source_count, evidence_ref "
                "from sip_import_evidence where run_id = %s",
                (run_id,),
            ).fetchone()
            if evidence is None:
                raise ImportBlockedError("server-held reviewed capture evidence is missing")
            staged = ImportBatchIn.model_validate(evidence["batch_payload"])
            if (staged != batch or evidence["articles_sha256"] != batch.articles_sha256
                    or evidence["source_count"] != batch.capture_source_count):
                raise ImportBlockedError("request differs from immutable reviewed capture")
            if batch.capture_source_count != 112:
                raise ImportBlockedError("SIP-185 requires all 112 mandatory sources")

            mandatory = conn.execute(
                "select id, sip185_code, active from source_library "
                "where mandatory = true",
            ).fetchall()
            required_codes = {entry.source_id for entry in MANDATORY_SOURCES}
            if (
                len(required_codes) != 112
                or len(mandatory) != 112
                or {row["sip185_code"] for row in mandatory} != required_codes
                or any(row["active"] is not True for row in mandatory)
            ):
                raise ImportBlockedError("mandatory SIP-185 source register is not complete")
            recorded = conn.execute(
                "select source_id, outcome, method, fallback_used, "
                "access_error, notes from source_checks where run_id = %s for share",
                (run_id,),
            ).fetchall()
            by_source = {row["source_id"]: row for row in recorded}
            for source in mandatory:
                check = by_source.get(source["id"])
                if check is None or not isinstance(check["notes"], str) or not check["notes"].startswith(
                    "Analyst-confirmed evidence: "
                ):
                    raise ImportBlockedError("112 analyst-confirmed source outcomes are missing")
                try:
                    fields = {
                        "source_id": str(source["id"]),
                        "outcome": check["outcome"],
                        "method": check["method"],
                        "fallback_used": check["fallback_used"],
                        "access_error": check["access_error"],
                        "notes": check["notes"],
                    }
                    RecordSourceCheckIn.model_validate(fields)
                    _require_confirmed_source_note(fields, source["sip185_code"])
                except (ValidationError, ValueError) as exc:
                    raise ImportBlockedError("invalid recorded source outcome evidence") from exc

            existing_count = conn.execute(
                "select count(*) as n from candidates where run_id = %s",
                (run_id,),
            ).fetchone()["n"]
            # Compare proposed candidates with separately staged original capture
            # observations, not with a copy of the candidate batch itself.
            raw_original = evidence["captured_articles"]
            if not isinstance(raw_original, list) or not raw_original:
                raise ImportBlockedError("original capture evidence must be nonempty")
            original = {}
            for raw in raw_original:
                try:
                    captured = CapturedArticleEvidence.model_validate(raw)
                except (ValidationError, ValueError, TypeError) as exc:
                    raise ImportBlockedError("invalid original captured-article evidence") from exc
                if captured.url in original:
                    raise ImportBlockedError("original captured URLs must be unique")
                original[captured.url] = (captured.source_id, captured.published_at)
            require_consistent_batch(
                batch,
                run_id=run["id"],
                run_version=run["version"],
                state=run["state"],
                existing_count=existing_count,
                capture_digest=evidence["articles_sha256"],
                locked_window_start=run["coverage_start_utc"],
                locked_window_end=run["coverage_end_utc"],
                captured_articles=original,
            )
            for candidate in batch.candidates:
                row = conn.execute(
                    "insert into candidates "
                    "(run_id, headline, source_id, url, summary, published_at, "
                    "in_coverage_window, captured_by) "
                    "values (%s,%s,%s,%s,%s,%s,%s,%s) returning id",
                    (
                        run_id, candidate.headline, candidate.source_id,
                        candidate.url, candidate.summary, candidate.published_at,
                        candidate.in_coverage_window, actor,
                    ),
                ).fetchone()
                record_audit(
                    conn, user_id=str(actor), action="candidate.import",
                    record_type="candidates", record_id=str(row["id"]),
                    new_value=candidate.headline,
                    reason=f"reviewed SIP capture {batch.articles_sha256}",
                )
            conn.execute(
                "update runs set analyst_id = %s "
                "where id = %s and analyst_id is null",
                (actor, run_id),
            )
            conn.execute(
                "insert into sip_import_claims "
                "(run_id, claim_key, articles_sha256, candidate_count, actor_id) "
                "values (%s,%s,%s,%s,%s)",
                (
                    run_id, batch.claim_key, batch.articles_sha256,
                    len(batch.candidates), actor,
                ),
            )
            record_audit(
                conn, user_id=str(actor), action="sip.import.commit",
                record_type="runs", record_id=run_id,
                new_value=batch.claim_key,
                reason=f"{len(batch.candidates)} reviewed candidates; "
                       f"capture reference: {evidence['evidence_ref']}",
            )
            # Exit commits candidates, audit records, analyst assignment and
            # claim together; any exception rolls all of them back.
            return ImportOutcome(
                run_id=batch.run_id,
                articles_sha256=batch.articles_sha256,
                claim_key=batch.claim_key,
                candidate_count=len(batch.candidates),
                replay=False,
            )
