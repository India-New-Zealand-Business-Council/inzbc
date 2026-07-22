"""Typed shapes for the SIP pipeline API, mirrored field-for-field from database/schema.sql.

These are not an ORM and don't talk to a database directly — apps/sip/pipeline writes through
Bhanu's API only (see client.py). Keeping the enums and field names here in lockstep with
database/schema.sql is what tests/test_models.py checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SignalStrength(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class SourceConfidence(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    UNVERIFIED = "Unverified"


class SourceOutcome(str, Enum):
    INCLUDED = "Included"
    CONTEXT = "Context"
    SUPPRESSED = "Suppressed"
    INACCESSIBLE = "Inaccessible"
    EXCLUDED = "Excluded"
    NO_QUALIFYING_ITEM = "No Qualifying Item"


class VerificationState(str, Enum):
    VERIFIED = "Verified"
    PARTIALLY_VERIFIED = "Partially Verified"
    UNVERIFIED = "Unverified"
    NOT_REQUIRED = "Not Required"
    REJECTED = "Rejected"


class RunState(str, Enum):
    DRAFT = "Draft"
    RUN_AUTHORISED = "Run Authorised"
    COVERAGE_LOCKED = "Coverage Locked"
    SCANNING = "Scanning"
    CANDIDATE_REVIEW = "Candidate Review"
    REPORT_DRAFTED = "Report Drafted"
    QA_IN_PROGRESS = "QA In Progress"
    QA_FAILED = "QA Failed"
    AWAITING_CEO_DECISION = "Awaiting CEO Decision"
    CONTINUE = "Continue"
    CONTINUE_WITH_CORRECTION = "Continue With Correction"
    PAUSED = "Paused"
    STOPPED = "Stopped"
    APPROVED_FOR_MANUAL_DISTRIBUTION = "Approved for Manual Distribution"
    DISTRIBUTED = "Distributed"
    CLOSED = "Closed"
    CORRECTED = "Corrected"
    WITHDRAWN = "Withdrawn"


@dataclass
class Run:
    """Mirrors the `runs` table."""

    run_number: str  # RUN-YYYYMMDD-01
    coverage_start_utc: str
    coverage_end_utc: str
    prompt_version: str
    initiated_by: str  # user id
    id: str | None = None
    coverage_timezone: str = "Pacific/Auckland"
    state: RunState = RunState.DRAFT
    production_enabled: bool = False
    analyst_id: str | None = None
    reviewer_id: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    qa_status: str | None = None


@dataclass
class SourceCheck:
    """Mirrors the `source_checks` table. One row per mandatory source per run."""

    run_id: str
    source_id: str
    outcome: SourceOutcome
    id: str | None = None
    checked_at: str | None = None
    method: str | None = None
    fallback_used: bool = False
    access_error: str | None = None
    notes: str | None = None


@dataclass
class Candidate:
    """Mirrors the `candidates` table."""

    run_id: str
    headline: str
    id: str | None = None
    source_id: str | None = None
    url: str | None = None
    summary: str | None = None
    published_at: str | None = None
    captured_at: str | None = None
    in_coverage_window: bool | None = None
    nz_relevance: int | None = None  # 0..5
    india_relevance: int | None = None
    member_relevance: int | None = None
    signal: SignalStrength | None = None
    confidence: SourceConfidence | None = None
    verification: VerificationState = VerificationState.UNVERIFIED
    duplicate_of: str | None = None
    included: bool | None = None
    reason: str | None = None
    proposed_routing: str | None = None
