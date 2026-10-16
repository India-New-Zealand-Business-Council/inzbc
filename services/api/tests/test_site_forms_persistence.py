"""Postgres persistence tests for `PostgresSiteFormRepository` (#45)."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from services.api.site_forms import (
    PostgresSiteFormRepository,
    SiteFormIdempotencyConflictError,
    SiteFormType,
    SiteFormWebhookIn,
)

DATABASE_URL = os.getenv("DATABASE_URL", "")
REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_SQL = REPO_ROOT / "database" / "schema.sql"

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="DATABASE_URL not set - Postgres site-forms tests need a real database"
)


@pytest.fixture
def pg_conn():
    name = f"formstest_{uuid.uuid4().hex[:12]}"
    admin = DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    with psycopg.connect(admin, autocommit=True) as admin_conn:
        admin_conn.execute(f'create database "{name}"')
    target_url = DATABASE_URL.rsplit("/", 1)[0] + f"/{name}"
    schema_text = SCHEMA_SQL.read_text(encoding="utf-8")
    with psycopg.connect(target_url, autocommit=True) as setup_conn:
        setup_conn.execute(schema_text)
    with psycopg.connect(target_url) as conn:
        yield conn


def _payload(**overrides) -> SiteFormWebhookIn:
    base = {
        "event_id": uuid.uuid4(),
        "form_type": SiteFormType.TRADE_ENQUIRY,
        "submitted_at": datetime(2026, 10, 16, 10, 30, tzinfo=UTC),
        "page_slug": "/trade",
        "contact_name": "Meera Nair",
        "contact_email": "meera.nair@example.co.nz",
        "organisation": "Koru Trade Advisory",
        "phone": "+64 21 555 0144",
        "subject": "Tariff schedule enquiry",
        "message": "Seeking guidance on kiwifruit and wine customs documentation.",
        "metadata": {"sector": "Horticulture"},
    }
    base.update(overrides)
    return SiteFormWebhookIn(**base)


def test_postgres_records_submission_audits_without_pii_and_enforces_append_only(pg_conn) -> None:
    repo = PostgresSiteFormRepository(pg_conn)
    submission = _payload()

    stored, deduplicated = repo.record(submission)
    assert deduplicated is False
    assert stored.event_id == str(submission.event_id)

    # Idempotent retry returns existing record with deduplicated=True.
    again, dedup_again = repo.record(submission)
    assert dedup_again is True
    assert again.id == stored.id

    # Conflicting payload for the same event_id raises SiteFormIdempotencyConflictError.
    with pytest.raises(SiteFormIdempotencyConflictError):
        repo.record(_payload(event_id=submission.event_id, contact_email="other@example.co.nz"))

    fetched = repo.get(stored.id)
    assert fetched is not None
    assert fetched.contact_email == "meera.nair@example.co.nz"
    assert repo.get("not-a-uuid") is None

    by_type = repo.list(form_type=SiteFormType.TRADE_ENQUIRY)
    assert len(by_type) == 1
    assert by_type[0].id == stored.id
    assert len(repo.list()) == 1

    # Audit log row exists and never stores personal contact fields.
    with pg_conn.cursor() as cur:
        cur.execute(
            "select action, new_value from audit_log where record_type = 'site_form_submission' and record_id = %s",
            (stored.id,),
        )
        audit_row = cur.fetchone()
    assert audit_row is not None
    assert audit_row[0] == "site_form.received"
    assert "meera.nair@example.co.nz" not in audit_row[1]
    assert "Meera Nair" not in audit_row[1]

    # Append-only trigger blocks UPDATE and DELETE on site_form_submissions.
    with pytest.raises(psycopg.Error), pg_conn.cursor() as cur:
        cur.execute("delete from site_form_submissions where id = %s", (stored.id,))
    pg_conn.rollback()
