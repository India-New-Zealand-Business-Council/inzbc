"""Pure, fail-closed candidate batch envelope validation for the future SIP import (#55).

No database connection, external request, endpoint registration, or write activation.
The backend must independently enforce these invariants INSIDE its run-lock transaction.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_MAX_BATCH = 5000
_MAX_TEXT = 4000


class ImportCandidateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(min_length=1, max_length=500)
    source_id: uuid.UUID
    url: str = Field(min_length=1, max_length=2048)
    summary: str | None = Field(default=None, max_length=_MAX_TEXT)
    published_at: datetime
    in_coverage_window: bool = Field(strict=True)

    @field_validator("headline")
    @classmethod
    def headline_not_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("headline must not be whitespace")
        return value

    @field_validator("published_at")
    @classmethod
    def aware_publication(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("publication time requires an explicit timezone")
        return value

    @field_validator("in_coverage_window")
    @classmethod
    def inside_window(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("cannot import an out-of-window candidate")
        return value

    @field_validator("url")
    @classmethod
    def public_article_url(cls, value: str) -> str:
        # URL provenance is checked in the original capture manifest too.
        # Preserve its exact form; never rewrite/normalize after digest validation.
        from apps.sip.collector.capture_manifest import _source_url

        _source_url(value)
        return value


class ImportBatchIn(BaseModel):
    """Schema ONLY. Not a write API and not proof of SIP-191 authorisation."""

    model_config = ConfigDict(extra="forbid")

    run_id: uuid.UUID
    articles_sha256: str
    expected_run_version: int = Field(ge=0, strict=True)
    candidates: list[ImportCandidateIn] = Field(min_length=1, max_length=_MAX_BATCH)
    capture_source_count: int = Field(ge=1, le=1000, strict=True)

    @field_validator("articles_sha256")
    @classmethod
    def canonical_digest(cls, value: str) -> str:
        if not _DIGEST.fullmatch(value):
            raise ValueError("articles_sha256 must be lowercase hex SHA-256")
        return value

    @model_validator(mode="after")
    def unique_urls(self) -> ImportBatchIn:
        seen: set[str] = set()
        for candidate in self.candidates:
            canonical = candidate.url.strip().casefold().rstrip("/")
            if canonical in seen:
                raise ValueError("duplicate URL within batch")
            seen.add(canonical)
        return self

    @property
    def claim_key(self) -> str:
        """Deterministic identity for run + canonical captured-articles digest.

        The claim is not authority, and must be checked against server-held original
        capture evidence before any insertion. It is not a request-supplied idempotency key.
        """
        return hashlib.sha256(
            f"{self.run_id}:{self.articles_sha256}".encode("ascii")
        ).hexdigest()


@dataclass(frozen=True)
class ImportOutcome:
    """Expected response-shape reference for backend implementation/replay tests."""

    run_id: uuid.UUID
    articles_sha256: str
    claim_key: str
    candidate_count: int
    replay: bool


def require_consistent_batch(
    batch: ImportBatchIn, *, run_id: uuid.UUID, run_version: int,
    state: str, existing_count: int, capture_digest: str,
) -> None:
    """Snapshot precondition used in tests/design. NOT a substitute for a row lock."""
    if batch.run_id != run_id:
        raise ValueError("candidate batch run mismatch")
    if batch.expected_run_version != run_version:
        raise ValueError("candidate batch run version changed")
    if state != "Scanning":
        raise ValueError("candidate batch requires authorised Scanning state")
    if existing_count != 0:
        raise ValueError("run has existing candidates; reconcile before import")
    if batch.articles_sha256 != capture_digest:
        raise ValueError("canonical capture digest mismatch")
