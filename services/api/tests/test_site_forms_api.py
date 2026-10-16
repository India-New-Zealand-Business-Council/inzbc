"""Unit and HTTP router tests for Wix site-forms webhook receiver and staff read endpoints (#45)."""

from __future__ import annotations

import json
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from services.api.main import app
from services.api.site_forms import (
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    InMemorySiteFormRepository,
    SiteFormType,
    SiteFormWebhookIn,
    WebhookNotConfiguredError,
    WebhookSignatureError,
    canonical_payload_sha256,
    compute_wix_webhook_signature,
    get_site_form_repository,
    get_webhook_secret,
    verify_wix_webhook_signature,
)

TEST_SECRET = "wix-webhook-test-secret-0123456789abcdef"


def _sample_payload(**overrides) -> dict:
    base = {
        "event_id": str(uuid.uuid4()),
        "form_type": "membership_enquiry",
        "submitted_at": "2026-10-16T10:15:00Z",
        "page_slug": "/members",
        "contact_name": "Aarav Patel",
        "contact_email": "aarav.patel@example.co.nz",
        "organisation": "Southern Cross Exports Ltd",
        "phone": "+64 9 555 0199",
        "subject": "Corporate membership enquiry",
        "message": "We export honey and dairy ingredients to Mumbai and would like to join INZBC.",
        "metadata": {
            "membership_tier": "corporate",
            "sector": "Food & Beverage",
        },
    }
    base.update(overrides)
    return base


def _signed_headers(raw_body: bytes, *, secret: str = TEST_SECRET, ts: int | None = None) -> dict[str, str]:
    timestamp = str(int(time.time()) if ts is None else ts)
    signature = compute_wix_webhook_signature(
        secret=secret,
        timestamp=timestamp,
        raw_body=raw_body,
    )
    return {
        TIMESTAMP_HEADER: timestamp,
        SIGNATURE_HEADER: signature,
        "Content-Type": "application/json",
    }


@pytest.fixture
def site_form_repo() -> InMemorySiteFormRepository:
    repo = InMemorySiteFormRepository()
    app.dependency_overrides[get_site_form_repository] = lambda: repo
    app.dependency_overrides[get_webhook_secret] = lambda: TEST_SECRET
    yield repo
    app.dependency_overrides.pop(get_site_form_repository, None)
    app.dependency_overrides.pop(get_webhook_secret, None)


def test_verify_signature_accepts_valid_hmac_and_rejects_tampering() -> None:
    raw = b'{"event_id":"9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"}'
    sig = compute_wix_webhook_signature(secret=TEST_SECRET, timestamp="1760612400", raw_body=raw)
    verify_wix_webhook_signature(
        raw,
        timestamp_header="1760612400",
        signature_header=sig,
        secret=TEST_SECRET,
        now_epoch=1760612450,
    )

    with pytest.raises(WebhookSignatureError, match="invalid"):
        verify_wix_webhook_signature(
            raw + b" ",
            timestamp_header="1760612400",
            signature_header=sig,
            secret=TEST_SECRET,
            now_epoch=1760612450,
        )


def test_verify_signature_refuses_missing_secret_or_stale_timestamp() -> None:
    raw = b"{}"
    with pytest.raises(WebhookNotConfiguredError):
        verify_wix_webhook_signature(
            raw,
            timestamp_header="1760612400",
            signature_header="sha256=" + "0" * 64,
            secret="",
            now_epoch=1760612400,
        )

    sig = compute_wix_webhook_signature(secret=TEST_SECRET, timestamp="1760612000", raw_body=raw)
    with pytest.raises(WebhookSignatureError, match="replay window"):
        verify_wix_webhook_signature(
            raw,
            timestamp_header="1760612000",
            signature_header=sig,
            secret=TEST_SECRET,
            now_epoch=1760612400,
        )


@pytest.mark.parametrize(
    ("ts_header", "sig_header", "expected_msg"),
    [
        (None, "sha256=" + "a" * 64, "missing X-Wix-Webhook-Timestamp"),
        ("1760612400", None, "missing X-Wix-Webhook-Signature"),
        ("not-an-int", "sha256=" + "a" * 64, "invalid X-Wix-Webhook-Timestamp"),
        ("1760612400", "md5=1234", "malformed X-Wix-Webhook-Signature"),
    ],
)
def test_verify_signature_rejects_malformed_headers(
    ts_header: str | None, sig_header: str | None, expected_msg: str
) -> None:
    with pytest.raises(WebhookSignatureError, match=expected_msg):
        verify_wix_webhook_signature(
            b"{}",
            timestamp_header=ts_header,
            signature_header=sig_header,
            secret=TEST_SECRET,
            now_epoch=1760612400,
        )


def test_payload_validation_enforces_email_timezone_and_slug_rules() -> None:
    valid = SiteFormWebhookIn.model_validate(_sample_payload())
    assert valid.form_type is SiteFormType.MEMBERSHIP_ENQUIRY
    assert len(canonical_payload_sha256(valid)) == 64

    with pytest.raises(ValueError, match="timezone"):
        SiteFormWebhookIn.model_validate(_sample_payload(submitted_at="2026-10-16T10:15:00"))

    with pytest.raises(ValueError, match="page_slug must start with '/'"):
        SiteFormWebhookIn.model_validate(_sample_payload(page_slug="members"))

    with pytest.raises(ValueError, match="query parameters"):
        SiteFormWebhookIn.model_validate(_sample_payload(page_slug="/members?email=a@b.c"))

    with pytest.raises(ValueError, match="contact_name"):
        SiteFormWebhookIn.model_validate(_sample_payload(contact_name="   "))

    with pytest.raises(ValueError, match="contact_email"):
        SiteFormWebhookIn.model_validate(_sample_payload(contact_email="not-an-email"))

    with pytest.raises(ValueError, match="at most 20 keys"):
        SiteFormWebhookIn.model_validate(
            _sample_payload(metadata={f"k{i}": "v" for i in range(21)})
        )


def test_webhook_rejects_any_query_string_parameter_before_reading_body(
    site_form_repo: InMemorySiteFormRepository,
) -> None:
    """Acceptance criterion (#45): no sensitive value in the URL or query string."""
    client = TestClient(app)
    raw = json.dumps(_sample_payload()).encode("utf-8")
    response = client.post(
        "/api/webhooks/wix/site-forms?secret=leaked&email=user@example.com",
        content=raw,
        headers=_signed_headers(raw),
    )
    assert response.status_code == 400
    assert "query string parameters are forbidden" in response.json()["error"]["message"]
    assert site_form_repo.list() == []


def test_webhook_persists_valid_submission_and_handles_idempotent_retries(
    site_form_repo: InMemorySiteFormRepository,
) -> None:
    client = TestClient(app)
    payload = _sample_payload()
    raw = json.dumps(payload).encode("utf-8")

    first = client.post(
        "/api/webhooks/wix/site-forms",
        content=raw,
        headers=_signed_headers(raw),
    )
    assert first.status_code == 201
    first_body = first.json()
    assert first_body["event_id"] == payload["event_id"]
    assert first_body["deduplicated"] is False
    submission_id = first_body["submission_id"]

    # Retry with the exact same event_id and payload returns 200 and deduplicated=True.
    second = client.post(
        "/api/webhooks/wix/site-forms",
        content=raw,
        headers=_signed_headers(raw),
    )
    assert second.status_code == 200
    assert second.json()["submission_id"] == submission_id
    assert second.json()["deduplicated"] is True

    # Reusing the same event_id with a different payload returns 409 Conflict.
    mutated = _sample_payload(
        event_id=payload["event_id"],
        contact_email="different@example.co.nz",
    )
    mutated_raw = json.dumps(mutated).encode("utf-8")
    conflict = client.post(
        "/api/webhooks/wix/site-forms",
        content=mutated_raw,
        headers=_signed_headers(mutated_raw),
    )
    assert conflict.status_code == 409


def test_webhook_fails_closed_when_secret_unset_or_signature_invalid(
    site_form_repo: InMemorySiteFormRepository,
) -> None:
    client = TestClient(app)
    raw = json.dumps(_sample_payload()).encode("utf-8")

    bad_sig = client.post(
        "/api/webhooks/wix/site-forms",
        content=raw,
        headers=_signed_headers(raw, secret="wrong-secret"),
    )
    assert bad_sig.status_code == 401

    app.dependency_overrides[get_webhook_secret] = lambda: None
    unconfigured = client.post(
        "/api/webhooks/wix/site-forms",
        content=raw,
        headers=_signed_headers(raw),
    )
    assert unconfigured.status_code == 503


def test_webhook_returns_400_on_non_json_and_422_on_schema_violation(
    site_form_repo: InMemorySiteFormRepository,
) -> None:
    client = TestClient(app)
    bad_json = b"{not-json"
    res_400 = client.post(
        "/api/webhooks/wix/site-forms",
        content=bad_json,
        headers=_signed_headers(bad_json),
    )
    assert res_400.status_code == 400

    invalid_payload = json.dumps({"event_id": str(uuid.uuid4())}).encode("utf-8")
    res_422 = client.post(
        "/api/webhooks/wix/site-forms",
        content=invalid_payload,
        headers=_signed_headers(invalid_payload),
    )
    assert res_422.status_code == 422


def test_staff_read_endpoints_list_filter_and_fetch_submissions(
    site_form_repo: InMemorySiteFormRepository,
) -> None:
    client = TestClient(app)
    p1 = _sample_payload(form_type="membership_enquiry", organisation="   ")
    p2 = _sample_payload(form_type="event_registration", page_slug="/events")

    for payload in (p1, p2):
        raw = json.dumps(payload).encode("utf-8")
        res = client.post(
            "/api/webhooks/wix/site-forms",
            content=raw,
            headers=_signed_headers(raw),
        )
        assert res.status_code == 201

    all_items = client.get("/api/site-forms").json()
    assert len(all_items) == 2

    events_only = client.get(
        "/api/site-forms", params={"form_type": "event_registration"}
    ).json()
    assert len(events_only) == 1
    assert events_only[0]["page_slug"] == "/events"

    single = client.get(f"/api/site-forms/{events_only[0]['id']}")
    assert single.status_code == 200
    assert single.json()["event_id"] == p2["event_id"]

    missing = client.get(f"/api/site-forms/{uuid.uuid4()}")
    assert missing.status_code == 404
