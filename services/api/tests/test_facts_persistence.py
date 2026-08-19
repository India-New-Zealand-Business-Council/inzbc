"""Integration tests for FactRepository (#188), against a real Postgres. Skipped without
`DATABASE_URL`, same convention as test_registers_persistence.py.
"""

from __future__ import annotations

import os
import uuid

import psycopg
import pytest

from services.api.facts_persistence import FactRepository, SelfApprovalError

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - facts tests need a real Postgres with schema.sql applied",
)


@pytest.fixture
def facts_repo() -> FactRepository:
    return FactRepository(DATABASE_URL)


def _make_user() -> str:
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "insert into users (name, email) values (%s, %s) returning id",
            (f"Test User {uuid.uuid4()}", f"{uuid.uuid4()}@example.com"),
        ).fetchone()
        conn.commit()
    return str(row[0])


def _audit_rows(record_id: str) -> list[tuple]:
    with psycopg.connect(DATABASE_URL) as conn:
        return conn.execute(
            "select action, old_value, new_value from audit_log "
            "where record_type = 'approved_facts' and record_id = %s order by id",
            (record_id,),
        ).fetchall()


def _fact_key() -> str:
    return f"TEST-FACT-{uuid.uuid4().hex[:12]}"


def test_draft_creates_version_one(facts_repo: FactRepository) -> None:
    drafter = _make_user()
    fact = facts_repo.draft(
        _fact_key(),
        "NZ-India FTA signed 27 April 2026",
        "MFAT press release",
        actor_id=drafter,
        owner_text="Trade desk",
    )
    assert fact.status == "draft"
    assert fact.version == 1
    assert fact.supersedes_id is None
    assert fact.created_by == drafter
    assert _audit_rows(fact.id) == [("approved_fact.draft", None, "draft")]


def test_self_approval_refused(facts_repo: FactRepository) -> None:
    drafter = _make_user()
    fact = facts_repo.draft(
        _fact_key(), "content", "source", actor_id=drafter, owner_text="Owner"
    )
    with pytest.raises(SelfApprovalError):
        facts_repo.approve(fact.id, actor_id=drafter)
    # Refused before any write: status is unchanged.
    assert facts_repo.get(fact.id).status == "draft"


def test_approve_by_different_actor(facts_repo: FactRepository) -> None:
    drafter = _make_user()
    reviewer = _make_user()
    fact = facts_repo.draft(
        _fact_key(), "content", "source", actor_id=drafter, owner_text="Owner"
    )
    approved = facts_repo.approve(fact.id, actor_id=reviewer)
    assert approved.status == "approved"
    assert approved.approved_by == reviewer
    assert approved.approved_at is not None
    assert _audit_rows(fact.id) == [
        ("approved_fact.draft", None, "draft"),
        ("approved_fact.approve", "draft", "approved"),
    ]


def test_approve_non_draft_rejected(facts_repo: FactRepository) -> None:
    drafter = _make_user()
    reviewer = _make_user()
    fact = facts_repo.draft(
        _fact_key(), "content", "source", actor_id=drafter, owner_text="Owner"
    )
    facts_repo.approve(fact.id, actor_id=reviewer)
    with pytest.raises(ValueError, match="only a draft can be approved"):
        facts_repo.approve(fact.id, actor_id=reviewer)


def test_archive_sets_status_and_timestamp(facts_repo: FactRepository) -> None:
    drafter = _make_user()
    fact = facts_repo.draft(
        _fact_key(), "content", "source", actor_id=drafter, owner_text="Owner"
    )
    archived = facts_repo.archive(fact.id, actor_id=drafter)
    assert archived.status == "archived"
    assert archived.archived_at is not None


def test_supersede_increments_version(facts_repo: FactRepository) -> None:
    drafter = _make_user()
    reviewer = _make_user()
    key = _fact_key()
    v1 = facts_repo.draft(
        key, "old content", "source", actor_id=drafter, owner_text="Owner"
    )
    facts_repo.approve(v1.id, actor_id=reviewer)

    v2 = facts_repo.draft(
        key,
        "corrected content",
        "source",
        actor_id=drafter,
        owner_text="Owner",
        supersedes_id=v1.id,
    )
    assert v2.version == 2
    assert v2.supersedes_id == v1.id
    # v1 is untouched - superseding never overwrites the row it corrects.
    assert facts_repo.get(v1.id).status == "approved"


def test_get_latest_approved_returns_none_when_no_approval(
    facts_repo: FactRepository,
) -> None:
    drafter = _make_user()
    key = _fact_key()
    facts_repo.draft(key, "content", "source", actor_id=drafter, owner_text="Owner")
    assert facts_repo.get_latest_approved(key) is None


def test_get_latest_approved_returns_highest_version(
    facts_repo: FactRepository,
) -> None:
    drafter = _make_user()
    reviewer = _make_user()
    key = _fact_key()
    v1 = facts_repo.draft(key, "v1", "source", actor_id=drafter, owner_text="Owner")
    facts_repo.approve(v1.id, actor_id=reviewer)
    v2 = facts_repo.draft(
        key, "v2", "source", actor_id=drafter, owner_text="Owner", supersedes_id=v1.id
    )
    facts_repo.approve(v2.id, actor_id=reviewer)

    latest = facts_repo.get_latest_approved(key)
    assert latest is not None
    assert latest.id == v2.id
    assert latest.version == 2


def test_history_orders_by_version_desc(facts_repo: FactRepository) -> None:
    drafter = _make_user()
    reviewer = _make_user()
    key = _fact_key()
    v1 = facts_repo.draft(key, "v1", "source", actor_id=drafter, owner_text="Owner")
    facts_repo.approve(v1.id, actor_id=reviewer)
    v2 = facts_repo.draft(
        key, "v2", "source", actor_id=drafter, owner_text="Owner", supersedes_id=v1.id
    )

    history = facts_repo.history(key)
    assert [f.version for f in history] == [2, 1]
    assert [f.id for f in history] == [v2.id, v1.id]


def test_owner_required(facts_repo: FactRepository) -> None:
    """Schema CHECK: a fact naming neither owner_id nor owner_text is rejected outright."""
    drafter = _make_user()
    with pytest.raises(psycopg.errors.CheckViolation):
        facts_repo.draft(_fact_key(), "content", "source", actor_id=drafter)
