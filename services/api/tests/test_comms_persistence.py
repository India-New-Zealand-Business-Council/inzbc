"""Integration tests for CommsDraftRepository, against a real Postgres. Skipped without
`DATABASE_URL`, same convention as test_source_checks.py.
"""

from __future__ import annotations

import os
import uuid

import psycopg
import pytest

from services.api.auth import Principal, SelfApprovalError
from services.api.comms_persistence import CommsDraftRepository

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - comms persistence tests need a real Postgres with schema.sql applied",
)


@pytest.fixture
def repo() -> CommsDraftRepository:
    return CommsDraftRepository(DATABASE_URL)


def _make_user(name: str) -> str:
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "insert into users (name, email) values (%s, %s) returning id",
            (f"{name} {uuid.uuid4()}", f"{uuid.uuid4()}@example.com"),
        ).fetchone()
        conn.commit()
    return str(row[0])


def _principal(user_id: str, *roles: str) -> Principal:
    return Principal(
        user_id=user_id,
        name="Test User",
        roles=frozenset(roles),
        session_id="test-session",
        csrf_token="test-csrf",
    )


def _audit_rows(record_id: str) -> list[tuple]:
    with psycopg.connect(DATABASE_URL) as conn:
        return conn.execute(
            "select action, old_value, new_value, user_id from audit_log "
            "where record_type = 'comms_drafts' and record_id = %s order by id",
            (record_id,),
        ).fetchall()


def test_create_persists_the_draft_in_draft_status(repo: CommsDraftRepository) -> None:
    author = _make_user("Author")
    record = repo.create("newsletter", "announce the FTA explainer", "generated text", authored_by=author)

    assert record.status == "Draft"
    assert record.authored_by == author
    assert record.approved_by is None
    assert record.draft_text == "generated text"


def test_create_writes_one_audit_row(repo: CommsDraftRepository) -> None:
    author = _make_user("Author")
    record = repo.create("linkedin_post", "brief", "text", authored_by=author)

    rows = _audit_rows(record.id)
    assert len(rows) == 1
    action, old_value, new_value, user_id = rows[0]
    assert action == "comms_draft.create"
    assert old_value is None
    assert new_value == "linkedin_post"
    assert str(user_id) == author


def test_approve_sets_status_and_approver(repo: CommsDraftRepository) -> None:
    author = _make_user("Author")
    reviewer = _make_user("Reviewer")
    record = repo.create("newsletter", "brief", "text", authored_by=author)

    approved = repo.approve(record.id, principal=_principal(reviewer, "Reviewer"), reason="looks good")

    assert approved.status == "Approved"
    assert approved.approved_by == reviewer
    assert approved.approved_at is not None
    assert approved.approval_reason == "looks good"


def test_approve_writes_a_second_audit_row_carrying_the_transition(
    repo: CommsDraftRepository,
) -> None:
    """BR8 record: the create act and the approve act are attributed to different users, and the
    audit trail must show both, not just the final Approved state."""
    author = _make_user("Author")
    reviewer = _make_user("Reviewer")
    record = repo.create("newsletter", "brief", "text", authored_by=author)
    repo.approve(record.id, principal=_principal(reviewer, "Reviewer"))

    rows = _audit_rows(record.id)
    assert len(rows) == 2
    action, old_value, new_value, user_id = rows[1]
    assert action == "comms_draft.approve"
    assert old_value == "Draft"
    assert new_value == "Approved"
    assert str(user_id) == reviewer


def test_the_author_cannot_approve_their_own_draft(repo: CommsDraftRepository) -> None:
    """The whole reason this repository exists rather than a bare UPDATE: BR8 says the person
    who produced something does not also approve it."""
    author = _make_user("Author")
    record = repo.create("newsletter", "brief", "text", authored_by=author)

    with pytest.raises(SelfApprovalError):
        repo.approve(record.id, principal=_principal(author, "Reviewer", "SIP Owner"))

    # And the refusal must not have partially applied.
    unchanged = repo.get(record.id)
    assert unchanged.status == "Draft"
    assert unchanged.approved_by is None


def test_a_self_approval_attempt_writes_no_audit_row(repo: CommsDraftRepository) -> None:
    """A refused act is not an act. An audit row for something that did not happen would be
    worse than no row at all - see services/api/audit.py's own reasoning on this."""
    author = _make_user("Author")
    record = repo.create("newsletter", "brief", "text", authored_by=author)

    with pytest.raises(SelfApprovalError):
        repo.approve(record.id, principal=_principal(author, "Reviewer"))

    assert len(_audit_rows(record.id)) == 1, "only the original create row should exist"


def test_approving_an_already_approved_draft_is_idempotent_not_a_second_event(
    repo: CommsDraftRepository,
) -> None:
    """A duplicate request (retry, double-click) must not read as a second reviewer having
    independently signed off - that would overstate how many people actually reviewed it."""
    author = _make_user("Author")
    reviewer = _make_user("Reviewer")
    record = repo.create("newsletter", "brief", "text", authored_by=author)

    first = repo.approve(record.id, principal=_principal(reviewer, "Reviewer"), reason="ok")
    second = repo.approve(record.id, principal=_principal(reviewer, "Reviewer"), reason="ok again")

    assert first.approved_at == second.approved_at
    assert len(_audit_rows(record.id)) == 2, "still just create + the one real approval"


def test_approving_a_missing_draft_raises_key_error(repo: CommsDraftRepository) -> None:
    with pytest.raises(KeyError):
        repo.approve(
            "00000000-0000-0000-0000-000000000000",
            principal=_principal(_make_user("Reviewer"), "Reviewer"),
        )


def test_delete_removes_the_row(repo: CommsDraftRepository) -> None:
    author = _make_user("Author")
    record = repo.create("newsletter", "brief", "text", authored_by=author)

    repo.delete(record.id, actor_id=author, reason="superseded")

    with pytest.raises(KeyError):
        repo.get(record.id)


def test_delete_of_an_approved_draft_still_succeeds(repo: CommsDraftRepository) -> None:
    """Any status is deletable, including Approved: deleting the row does not erase the approval
    - it already wrote its own audit entry, and that survives even though the row is gone."""
    author = _make_user("Author")
    reviewer = _make_user("Reviewer")
    record = repo.create("newsletter", "brief", "text", authored_by=author)
    repo.approve(record.id, principal=_principal(reviewer, "Reviewer"))

    repo.delete(record.id, actor_id=reviewer, reason="contained personal information")

    with pytest.raises(KeyError):
        repo.get(record.id)
    rows = _audit_rows(record.id)
    assert any(action == "comms_draft.approve" for action, *_ in rows), (
        "the approval's own audit row must survive even though the draft row is gone"
    )


def test_delete_writes_an_audit_row_naming_only_the_status_transition(
    repo: CommsDraftRepository,
) -> None:
    author = _make_user("Author")
    record = repo.create("newsletter", "brief", "text", authored_by=author)

    repo.delete(record.id, actor_id=author, reason="created in error")

    rows = _audit_rows(record.id)
    assert len(rows) == 2
    action, old_value, new_value, user_id = rows[1]
    assert action == "comms_draft.delete"
    assert old_value == "Draft"
    assert new_value == "Deleted"
    assert str(user_id) == author


def test_delete_audits_the_act_without_recording_the_text(repo: CommsDraftRepository) -> None:
    """`audit_log` is append-only - nothing can remove a row from it. Recording what was in a
    deleted draft would make the sensitive text permanent in the one table nothing can remove it
    from, the exact opposite of what someone deleting a draft is trying to achieve.

    Scans every `old_value`/`new_value`/`reason` in the whole table, not just this record's own
    rows - the failure being guarded against is the text leaking into a column nobody thought
    about, not just the obvious one.
    """
    distinctive = f"leaked-name-{uuid.uuid4()}"
    author = _make_user("Author")
    record = repo.create("newsletter", "brief", distinctive, authored_by=author)

    repo.delete(record.id, actor_id=author, reason="contained personal information")

    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            "select old_value, new_value, reason from audit_log "
            "where old_value like %s or new_value like %s or reason like %s",
            (f"%{distinctive}%", f"%{distinctive}%", f"%{distinctive}%"),
        ).fetchall()
    assert rows == []


def test_deleting_a_missing_draft_raises_key_error(repo: CommsDraftRepository) -> None:
    with pytest.raises(KeyError):
        repo.delete(
            "00000000-0000-0000-0000-000000000000",
            actor_id=_make_user("Someone"),
            reason="created in error",
        )


def test_get_and_list_all_round_trip(repo: CommsDraftRepository) -> None:
    author = _make_user("Author")
    first = repo.create("newsletter", "brief one", "text one", authored_by=author)
    second = repo.create("event_announcement", "brief two", "text two", authored_by=author)

    assert repo.get(first.id).brief == "brief one"

    ids = {r.id for r in repo.list_all()}
    assert first.id in ids
    assert second.id in ids
