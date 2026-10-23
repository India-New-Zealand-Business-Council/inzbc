"""Wix-to-internal site-forms webhook receiver and staff read endpoints (#45).

Implements the contract in `schemas/webhooks.md`:
- `POST /api/webhooks/wix/site-forms`: machine-to-machine webhook endpoint authenticated via
  HMAC-SHA256 (`X-Wix-Webhook-Signature` + `X-Wix-Webhook-Timestamp` over `<timestamp>.<body>`),
  failing closed when `WIX_WEBHOOK_SECRET` is unset (503) or when the signature/timestamp is
  missing, expired, or invalid (401).
- Refuses any request carrying query-string parameters (400) before reading the body, so neither
  webhook secrets nor submitter personal data can ever be sent in the URL or query string.
- Bounds unauthenticated work: the body is capped at `MAX_WEBHOOK_BODY_BYTES` (413) while it is
  read, and the database connection is opened only after the signature verifies.
- Fails closed (503) when `DATABASE_URL` is unset: a submission is never acknowledged unless it
  is durably stored.
- Idempotent on `event_id`: retries with an identical canonical payload return 200 with
  `deduplicated=True`; reusing `event_id` with a mutated payload returns 409 Conflict.
- `GET /api/site-forms` and `GET /api/site-forms/{submission_id}`: staff-authenticated read surface
  protected by `read_access(*STAFF_READ)`.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Protocol

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from services.api.audit import record_audit
from services.api.auth import STAFF_READ, Principal
from services.api.session import AUTH_RESPONSES, read_access

WEBHOOK_SECRET_ENV = "WIX_WEBHOOK_SECRET"
SIGNATURE_HEADER = "X-Wix-Webhook-Signature"
TIMESTAMP_HEADER = "X-Wix-Webhook-Timestamp"
REPLAY_WINDOW_SECONDS = 300
# The largest valid payload (5000-char message, 20 x 500-char metadata values, the other capped
# fields) is well under 32 KiB of JSON, so 64 KiB leaves room without letting an unauthenticated
# caller make the process buffer an arbitrarily large body before the signature is checked.
MAX_WEBHOOK_BODY_BYTES = 64 * 1024

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SiteFormType(str, Enum):
    GENERAL_ENQUIRY = "general_enquiry"
    MEMBERSHIP_ENQUIRY = "membership_enquiry"
    EVENT_REGISTRATION = "event_registration"
    TRADE_ENQUIRY = "trade_enquiry"
    PARTNERSHIP_ENQUIRY = "partnership_enquiry"


class WebhookNotConfiguredError(RuntimeError):
    """Raised when `WIX_WEBHOOK_SECRET` is unset or empty."""


class WebhookSignatureError(ValueError):
    """Raised when the webhook timestamp or HMAC-SHA256 signature is missing, stale, or invalid."""


class SiteFormStoreNotConfiguredError(RuntimeError):
    """Raised when `DATABASE_URL` is unset, so there is nowhere durable to store a submission."""


class WebhookBodyTooLargeError(ValueError):
    """Raised when the webhook body exceeds `MAX_WEBHOOK_BODY_BYTES`."""


class SiteFormIdempotencyConflictError(ValueError):
    """Raised when `event_id` is replayed with a different payload digest."""


def compute_wix_webhook_signature(
    *, secret: str, timestamp: str, raw_body: bytes
) -> str:
    """Computes `sha256=<hex>` over `<timestamp>.<raw_body>` using `secret`."""
    signing_input = timestamp.encode("ascii") + b"." + raw_body
    digest = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_wix_webhook_signature(
    raw_body: bytes,
    *,
    timestamp_header: str | None,
    signature_header: str | None,
    secret: str | None,
    now_epoch: int | None = None,
    replay_window_seconds: int = REPLAY_WINDOW_SECONDS,
) -> None:
    """Verifies the Wix webhook HMAC-SHA256 signature and replay window, failing closed."""
    clean_secret = (secret or "").strip()
    if not clean_secret:
        raise WebhookNotConfiguredError(f"{WEBHOOK_SECRET_ENV} is not configured")

    if not timestamp_header or not timestamp_header.strip():
        raise WebhookSignatureError(f"missing {TIMESTAMP_HEADER} header")
    if not signature_header or not signature_header.strip():
        raise WebhookSignatureError(f"missing {SIGNATURE_HEADER} header")

    raw_ts = timestamp_header.strip()
    try:
        ts_value = int(raw_ts)
    except ValueError as exc:
        raise WebhookSignatureError(f"invalid {TIMESTAMP_HEADER} header") from exc

    current_epoch = int(time.time()) if now_epoch is None else int(now_epoch)
    if abs(current_epoch - ts_value) > replay_window_seconds:
        raise WebhookSignatureError(
            f"{TIMESTAMP_HEADER} is outside the {replay_window_seconds}s replay window"
        )

    provided = signature_header.strip()
    if not provided.startswith("sha256=") or len(provided) != len("sha256=") + 64:
        raise WebhookSignatureError(f"malformed {SIGNATURE_HEADER} header")

    expected = compute_wix_webhook_signature(
        secret=clean_secret,
        timestamp=raw_ts,
        raw_body=raw_body,
    )
    if not hmac.compare_digest(provided.lower(), expected.lower()):
        raise WebhookSignatureError(f"invalid {SIGNATURE_HEADER} digest")


class SiteFormWebhookIn(BaseModel):
    """Validated Wix site-form webhook payload (`schemas/webhooks.md`)."""

    model_config = ConfigDict(extra="forbid")

    event_id: uuid.UUID
    form_type: SiteFormType
    submitted_at: datetime
    page_slug: str = Field(..., min_length=1, max_length=120)
    contact_name: str = Field(..., min_length=1, max_length=200)
    contact_email: str = Field(..., min_length=3, max_length=320)
    organisation: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=60)
    subject: str | None = Field(default=None, max_length=300)
    message: str | None = Field(default=None, max_length=5000)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("submitted_at")
    @classmethod
    def _require_tz(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("submitted_at must include a timezone offset")
        return value.astimezone(UTC)

    @field_validator("page_slug")
    @classmethod
    def _validate_page_slug(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("/"):
            raise ValueError("page_slug must start with '/'")
        if "?" in cleaned or "#" in cleaned or " " in cleaned:
            raise ValueError("page_slug must not contain query parameters, fragments, or spaces")
        return cleaned

    @field_validator("contact_name")
    @classmethod
    def _validate_contact_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("contact_name must not be blank")
        return cleaned

    @field_validator("contact_email")
    @classmethod
    def _validate_contact_email(cls, value: str) -> str:
        cleaned = value.strip()
        if not _EMAIL_RE.match(cleaned):
            raise ValueError("contact_email must be a valid email address")
        return cleaned

    @field_validator("organisation", "phone", "subject", "message")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("metadata")
    @classmethod
    def _validate_metadata(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 20:
            raise ValueError("metadata may contain at most 20 keys")
        cleaned: dict[str, str] = {}
        for k, v in value.items():
            key = k.strip()
            if not key or len(key) > 64:
                raise ValueError("metadata keys must be 1..64 non-whitespace characters")
            if len(v) > 500:
                raise ValueError("metadata values must be at most 500 characters")
            cleaned[key] = v
        return cleaned


def canonical_payload_sha256(payload: SiteFormWebhookIn) -> str:
    """Deterministic SHA-256 digest of a validated submission payload."""
    canonical = {
        "event_id": str(payload.event_id),
        "form_type": payload.form_type.value,
        "submitted_at": payload.submitted_at.astimezone(UTC).isoformat(),
        "page_slug": payload.page_slug,
        "contact_name": payload.contact_name,
        "contact_email": payload.contact_email.lower(),
        "organisation": payload.organisation,
        "phone": payload.phone,
        "subject": payload.subject,
        "message": payload.message,
        "metadata": dict(sorted(payload.metadata.items())),
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class StoredSiteFormSubmission:
    id: str
    event_id: str
    form_type: SiteFormType
    submitted_at: datetime
    received_at: datetime
    page_slug: str
    contact_name: str
    contact_email: str
    organisation: str | None
    phone: str | None
    subject: str | None
    message: str | None
    metadata: dict[str, str]
    payload_sha256: str


class SiteFormWebhookAckOut(BaseModel):
    """Receipt returned to the Wix webhook caller (no personal data echoed)."""

    model_config = ConfigDict(extra="forbid")

    submission_id: str
    event_id: str
    form_type: SiteFormType
    received_at: datetime
    deduplicated: bool


class SiteFormSubmissionOut(BaseModel):
    """Staff read representation of a persisted site-form submission."""

    model_config = ConfigDict(extra="forbid")

    id: str
    event_id: str
    form_type: SiteFormType
    submitted_at: datetime
    received_at: datetime
    page_slug: str
    contact_name: str
    contact_email: str
    organisation: str | None = None
    phone: str | None = None
    subject: str | None = None
    message: str | None = None
    metadata: dict[str, str]


class SiteFormRepository(Protocol):
    def record(
        self, payload: SiteFormWebhookIn
    ) -> tuple[StoredSiteFormSubmission, bool]: ...

    def get(self, submission_id: str) -> StoredSiteFormSubmission | None: ...

    def list(
        self,
        *,
        form_type: SiteFormType | None = None,
        limit: int = 50,
    ) -> list[StoredSiteFormSubmission]: ...


class InMemorySiteFormRepository:
    """Deterministic in-memory repository for unit and router tests."""

    def __init__(self) -> None:
        self._by_id: dict[str, StoredSiteFormSubmission] = {}
        self._by_event_id: dict[str, StoredSiteFormSubmission] = {}

    def record(
        self, payload: SiteFormWebhookIn
    ) -> tuple[StoredSiteFormSubmission, bool]:
        event_key = str(payload.event_id)
        digest = canonical_payload_sha256(payload)
        existing = self._by_event_id.get(event_key)
        if existing is not None:
            if existing.payload_sha256 != digest:
                raise SiteFormIdempotencyConflictError(
                    f"event_id {event_key} was already recorded with a different payload"
                )
            return existing, True

        stored = StoredSiteFormSubmission(
            id=str(uuid.uuid4()),
            event_id=event_key,
            form_type=payload.form_type,
            submitted_at=payload.submitted_at,
            received_at=datetime.now(UTC),
            page_slug=payload.page_slug,
            contact_name=payload.contact_name,
            contact_email=payload.contact_email,
            organisation=payload.organisation,
            phone=payload.phone,
            subject=payload.subject,
            message=payload.message,
            metadata=dict(payload.metadata),
            payload_sha256=digest,
        )
        self._by_id[stored.id] = stored
        self._by_event_id[event_key] = stored
        return stored, False

    def get(self, submission_id: str) -> StoredSiteFormSubmission | None:
        return self._by_id.get(submission_id)

    def list(
        self,
        *,
        form_type: SiteFormType | None = None,
        limit: int = 50,
    ) -> list[StoredSiteFormSubmission]:
        items = list(self._by_id.values())
        if form_type is not None:
            items = [item for item in items if item.form_type == form_type]
        items.sort(key=lambda item: (item.received_at, item.id), reverse=True)
        return items[:limit]


class PostgresSiteFormRepository:
    """Postgres-backed site-forms repository with transactional content-free auditing."""

    def __init__(self, conn) -> None:
        self._conn = conn

    def record(
        self, payload: SiteFormWebhookIn
    ) -> tuple[StoredSiteFormSubmission, bool]:
        event_key = str(payload.event_id)
        digest = canonical_payload_sha256(payload)

        with self._conn.cursor() as cur:
            cur.execute(
                """
                insert into site_form_submissions (
                    event_id, form_type, submitted_at, page_slug,
                    contact_name, contact_email, organisation, phone,
                    subject, message, metadata, payload_sha256
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                on conflict (event_id) do nothing
                returning
                    id::text,
                    event_id::text,
                    form_type::text,
                    submitted_at,
                    received_at,
                    page_slug,
                    contact_name,
                    contact_email,
                    organisation,
                    phone,
                    subject,
                    message,
                    metadata,
                    payload_sha256
                """,
                (
                    event_key,
                    payload.form_type.value,
                    payload.submitted_at,
                    payload.page_slug,
                    payload.contact_name,
                    payload.contact_email,
                    payload.organisation,
                    payload.phone,
                    payload.subject,
                    payload.message,
                    json.dumps(payload.metadata, sort_keys=True),
                    digest,
                ),
            )
            inserted = cur.fetchone()
            if inserted is not None:
                stored = _row_to_submission(inserted)
                # Personal contact details (`contact_name`, `contact_email`, `phone`, `message`)
                # are deliberately omitted from the immutable audit_log row.
                record_audit(
                    self._conn,
                    action="site_form.received",
                    record_type="site_form_submission",
                    record_id=stored.id,
                    user_id=None,
                    old_value=None,
                    # `audit_log.new_value` is text; psycopg cannot adapt a bare dict.
                    new_value=json.dumps(
                        {
                            "event_id": stored.event_id,
                            "form_type": stored.form_type.value,
                            "page_slug": stored.page_slug,
                            "payload_sha256": stored.payload_sha256,
                        },
                        sort_keys=True,
                    ),
                    reason=f"Wix site-form webhook ({stored.form_type.value})",
                )
                self._conn.commit()
                return stored, False

            cur.execute(
                """
                select
                    id::text,
                    event_id::text,
                    form_type::text,
                    submitted_at,
                    received_at,
                    page_slug,
                    contact_name,
                    contact_email,
                    organisation,
                    phone,
                    subject,
                    message,
                    metadata,
                    payload_sha256
                from site_form_submissions
                where event_id = %s
                """,
                (event_key,),
            )
            existing_row = cur.fetchone()

        if existing_row is None:  # pragma: no cover - defensive
            raise RuntimeError(f"site_form_submissions row missing for event_id {event_key}")
        existing = _row_to_submission(existing_row)
        if existing.payload_sha256 != digest:
            raise SiteFormIdempotencyConflictError(
                f"event_id {event_key} was already recorded with a different payload"
            )
        return existing, True

    def get(self, submission_id: str) -> StoredSiteFormSubmission | None:
        try:
            uuid.UUID(submission_id)
        except ValueError:
            return None
        with self._conn.cursor() as cur:
            cur.execute(
                """
                select
                    id::text,
                    event_id::text,
                    form_type::text,
                    submitted_at,
                    received_at,
                    page_slug,
                    contact_name,
                    contact_email,
                    organisation,
                    phone,
                    subject,
                    message,
                    metadata,
                    payload_sha256
                from site_form_submissions
                where id = %s
                """,
                (submission_id,),
            )
            row = cur.fetchone()
        return _row_to_submission(row) if row is not None else None

    def list(
        self,
        *,
        form_type: SiteFormType | None = None,
        limit: int = 50,
    ) -> list[StoredSiteFormSubmission]:
        with self._conn.cursor() as cur:
            if form_type is None:
                cur.execute(
                    """
                    select
                        id::text,
                        event_id::text,
                        form_type::text,
                        submitted_at,
                        received_at,
                        page_slug,
                        contact_name,
                        contact_email,
                        organisation,
                        phone,
                        subject,
                        message,
                        metadata,
                        payload_sha256
                    from site_form_submissions
                    order by received_at desc, id desc
                    limit %s
                    """,
                    (limit,),
                )
            else:
                cur.execute(
                    """
                    select
                        id::text,
                        event_id::text,
                        form_type::text,
                        submitted_at,
                        received_at,
                        page_slug,
                        contact_name,
                        contact_email,
                        organisation,
                        phone,
                        subject,
                        message,
                        metadata,
                        payload_sha256
                    from site_form_submissions
                    where form_type = %s
                    order by received_at desc, id desc
                    limit %s
                    """,
                    (form_type.value, limit),
                )
            rows = cur.fetchall()
        return [_row_to_submission(row) for row in rows]


def _row_to_submission(row: tuple) -> StoredSiteFormSubmission:
    raw_metadata = row[12]
    if isinstance(raw_metadata, str):
        parsed_metadata = json.loads(raw_metadata)
    else:
        parsed_metadata = dict(raw_metadata or {})
    return StoredSiteFormSubmission(
        id=str(row[0]),
        event_id=str(row[1]),
        form_type=SiteFormType(str(row[2])),
        submitted_at=row[3],
        received_at=row[4],
        page_slug=str(row[5]),
        contact_name=str(row[6]),
        contact_email=str(row[7]),
        organisation=row[8],
        phone=row[9],
        subject=row[10],
        message=row[11],
        metadata={str(k): str(v) for k, v in parsed_metadata.items()},
        payload_sha256=str(row[13]),
    )


def _to_out(item: StoredSiteFormSubmission) -> SiteFormSubmissionOut:
    return SiteFormSubmissionOut(
        id=item.id,
        event_id=item.event_id,
        form_type=item.form_type,
        submitted_at=item.submitted_at,
        received_at=item.received_at,
        page_slug=item.page_slug,
        contact_name=item.contact_name,
        contact_email=item.contact_email,
        organisation=item.organisation,
        phone=item.phone,
        subject=item.subject,
        message=item.message,
        metadata=item.metadata,
    )


SiteFormRepositoryOpener = Callable[[], AbstractContextManager[SiteFormRepository]]


@contextmanager
def open_site_form_repository() -> Iterator[SiteFormRepository]:
    """Opens the Postgres repository, refusing when `DATABASE_URL` is unset.

    There is deliberately no in-memory fallback outside tests: acknowledging a webhook whose
    personal data lives only in process memory would lose it on restart while Wix treats it as
    delivered. Tests inject `InMemorySiteFormRepository` through dependency overrides.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SiteFormStoreNotConfiguredError("DATABASE_URL is not configured")
    import psycopg

    with psycopg.connect(database_url) as conn:
        yield PostgresSiteFormRepository(conn)


def get_site_form_repository_opener() -> SiteFormRepositoryOpener:
    """The webhook opens the store itself, after verifying the signature, rather than having
    FastAPI connect to Postgres for every unauthenticated request before the handler runs."""
    return open_site_form_repository


def get_site_form_repository(
    opener: SiteFormRepositoryOpener = Depends(get_site_form_repository_opener),
) -> Iterator[SiteFormRepository]:
    """The staff read endpoints' repository; 503 when no durable store is configured."""
    try:
        with opener() as repository:
            yield repository
    except SiteFormStoreNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


async def _read_capped_body(request: Request) -> bytes:
    """Reads the body, refusing once it passes `MAX_WEBHOOK_BODY_BYTES` instead of buffering it all."""
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_WEBHOOK_BODY_BYTES:
        raise WebhookBodyTooLargeError
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_WEBHOOK_BODY_BYTES:
            raise WebhookBodyTooLargeError
    return bytes(body)


def get_webhook_secret() -> str | None:
    return os.getenv(WEBHOOK_SECRET_ENV)


webhook_router = APIRouter(
    prefix="/api/webhooks/wix/site-forms",
    tags=["Webhooks"],
)

site_forms_router = APIRouter(
    prefix="/api/site-forms",
    tags=["Site Forms"],
    responses=AUTH_RESPONSES,
)


@webhook_router.post(
    "",
    response_model=SiteFormWebhookAckOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"description": "Duplicate webhook event_id with identical payload (idempotent retry)."},
        400: {"description": "Query string parameters present on webhook URL, or malformed JSON."},
        401: {"description": "Missing, expired, or invalid Wix HMAC-SHA256 webhook signature."},
        409: {"description": "Duplicate event_id replayed with a different payload."},
        413: {"description": "Request body exceeds the webhook size limit."},
        503: {
            "description": "WIX_WEBHOOK_SECRET or DATABASE_URL is not configured on the server."
        },
    },
)
async def receive_wix_site_form(
    request: Request,
    response: Response,
    wix_timestamp: str | None = Header(default=None, alias=TIMESTAMP_HEADER),
    wix_signature: str | None = Header(default=None, alias=SIGNATURE_HEADER),
    secret: str | None = Depends(get_webhook_secret),
    open_repository: SiteFormRepositoryOpener = Depends(get_site_form_repository_opener),
) -> SiteFormWebhookAckOut:
    """Receives, verifies, and persists a Wix site-form submission (#45)."""
    # Acceptance criterion: no sensitive value (or any parameter) in the URL or query string.
    if request.url.query:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=(
                "query string parameters are forbidden on webhook endpoints; "
                "send the payload in the request body and signature in headers"
            ),
        )

    try:
        raw_body = await _read_capped_body(request)
    except WebhookBodyTooLargeError as exc:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"request body exceeds {MAX_WEBHOOK_BODY_BYTES} bytes",
        ) from exc
    try:
        verify_wix_webhook_signature(
            raw_body,
            timestamp_header=wix_timestamp,
            signature_header=wix_signature,
            secret=secret,
        )
    except WebhookNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except WebhookSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    try:
        parsed_json = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="request body must be valid UTF-8 JSON"
        ) from exc

    try:
        payload = SiteFormWebhookIn.model_validate(parsed_json)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc

    try:
        with open_repository() as repository:
            stored, deduplicated = repository.record(payload)
    except SiteFormStoreNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except SiteFormIdempotencyConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if deduplicated:
        response.status_code = status.HTTP_200_OK

    return SiteFormWebhookAckOut(
        submission_id=stored.id,
        event_id=stored.event_id,
        form_type=stored.form_type,
        received_at=stored.received_at,
        deduplicated=deduplicated,
    )


@site_forms_router.get("", response_model=list[SiteFormSubmissionOut])
def list_site_forms(
    form_type: SiteFormType | None = Query(
        default=None, description="Optional filter by site-form category."
    ),
    limit: int = Query(default=50, ge=1, le=200),
    _principal: Principal = Depends(read_access(*STAFF_READ)),
    repository: SiteFormRepository = Depends(get_site_form_repository),
) -> list[SiteFormSubmissionOut]:
    """Lists received site-form submissions, newest first."""
    return [_to_out(item) for item in repository.list(form_type=form_type, limit=limit)]


@site_forms_router.get("/{submission_id}", response_model=SiteFormSubmissionOut)
def get_site_form(
    submission_id: str,
    _principal: Principal = Depends(read_access(*STAFF_READ)),
    repository: SiteFormRepository = Depends(get_site_form_repository),
) -> SiteFormSubmissionOut:
    """Returns a single persisted site-form submission by ID."""
    stored = repository.get(submission_id)
    if stored is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"site-form submission {submission_id} not found",
        )
    return _to_out(stored)
