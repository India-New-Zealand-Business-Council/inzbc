"""Report versions against a real Postgres (#124).

Three things here are database behaviour and nothing else: the version number the database assigns,
the trigger that opens the three decision streams on insert, and the constraints that refuse a
malformed row. A fake proves none of them.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from services.api.decisions import (
    DecisionNotPermittedError,
    DecisionRepository,
    ReportRepository,
)
from services.api.persistence import RunRepository
from services.api.tests.role_seed import grant, role_id

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - report version tests need a real Postgres",
)

SHA = "b" * 64


@pytest.fixture
def actor_id() -> str:
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "insert into users (name, email) values (%s, %s) returning id",
            (f"Report User {uuid.uuid4()}", f"{uuid.uuid4()}@example.com"),
        ).fetchone()
        grant(conn, row[0], "Analyst")
        conn.commit()
    return str(row[0])


@pytest.fixture
def analyst_role_id(actor_id: str) -> int:
    with psycopg.connect(DATABASE_URL) as conn:
        return role_id(conn, "Analyst")


@pytest.fixture
def run_id(actor_id: str) -> str:
    run = RunRepository(DATABASE_URL).create_run(
        run_number=f"RUN-RPT-{uuid.uuid4().hex[:12]}",
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-08-12T07:00:00+12:00",
        coverage_end_utc="2026-08-13T07:00:00+12:00",
        initiated_by=actor_id,
    )
    return run.id


def _submit(run_id: str, actor_id: str, role: int, *, sha: str = SHA):
    return ReportRepository(DATABASE_URL).submit(
        run_id=run_id,
        content_sha256=sha,
        actor_id=actor_id,
        actor_role_id=role,
        created_at=datetime.now(UTC) - timedelta(minutes=5),
    )


def test_the_first_version_of_a_run_is_one(run_id: str, actor_id: str, analyst_role_id: int):
    version = _submit(run_id, actor_id, analyst_role_id)

    assert version.version_number == 1
    assert version.run_id == run_id


def test_versions_number_upwards_per_run(run_id: str, actor_id: str, analyst_role_id: int):
    """Assigned by the database, not the caller. Two runs must not share a sequence, and a second
    version of the same run must not reuse the first one's number."""
    first = _submit(run_id, actor_id, analyst_role_id)
    second = _submit(run_id, actor_id, analyst_role_id)
    other_run = RunRepository(DATABASE_URL).create_run(
        run_number=f"RUN-RPT-{uuid.uuid4().hex[:12]}",
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-08-12T07:00:00+12:00",
        coverage_end_utc="2026-08-13T07:00:00+12:00",
        initiated_by=actor_id,
    )
    elsewhere = _submit(other_run.id, actor_id, analyst_role_id)

    assert (first.version_number, second.version_number) == (1, 2)
    assert elsewhere.version_number == 1, "the sequence is per run, not global"


def test_submitting_opens_all_three_decision_streams(
    run_id: str, actor_id: str, analyst_role_id: int
):
    """The property that makes a submitted report decidable, and the reason there is no separate
    call to open the streams: a trigger does it, so it cannot be forgotten."""
    version = _submit(run_id, actor_id, analyst_role_id)

    current = DecisionRepository(DATABASE_URL).current(version.id)

    assert set(current.revisions) == {
        "CEO Ruling", "Report Approval", "Distribution Authority",
    }
    assert all(revision == 0 for revision in current.revisions.values())


def test_a_freshly_submitted_version_has_no_decisions(
    run_id: str, actor_id: str, analyst_role_id: int
):
    """Undecided is null, not a default value. `Not Authorised` is a decision; the absence of one
    is a different fact, and collapsing them is what the mutable approvals row used to do."""
    version = _submit(run_id, actor_id, analyst_role_id)

    current = DecisionRepository(DATABASE_URL).current(version.id)

    assert current.ceo_ruling is None
    assert current.report_approval is None
    assert current.distribution_authority is None


def test_reading_back_returns_what_was_submitted(run_id: str, actor_id: str, analyst_role_id: int):
    version = _submit(run_id, actor_id, analyst_role_id)

    assert ReportRepository(DATABASE_URL).get(version.id) == version


def test_an_unknown_version_raises_key_error():
    with pytest.raises(KeyError):
        ReportRepository(DATABASE_URL).get(str(uuid.uuid4()))


def test_a_content_hash_that_is_not_a_sha256_is_refused(
    run_id: str, actor_id: str, analyst_role_id: int
):
    """The router validates the same shape. This proves the database refuses it too, so a caller
    reaching the repository directly cannot store a hash that is not one."""
    with pytest.raises(psycopg.errors.CheckViolation):
        _submit(run_id, actor_id, analyst_role_id, sha="not-a-hash")


def test_submission_cannot_predate_creation(run_id: str, actor_id: str, analyst_role_id: int):
    """`submitted_at >= created_at` is a CHECK. A `created_at` in the future would mean the content
    was made after it was handed over, which is not a thing that happened."""
    with pytest.raises(psycopg.errors.CheckViolation):
        ReportRepository(DATABASE_URL).submit(
            run_id=run_id,
            content_sha256=SHA,
            actor_id=actor_id,
            actor_role_id=analyst_role_id,
            created_at=datetime.now(UTC) + timedelta(days=1),
        )


def test_the_role_must_be_one_the_actor_actually_holds(
    run_id: str, actor_id: str
):
    """`created_by_role_id` references `user_roles`, so a claimed role nobody granted is refused by
    the database rather than recorded as fact."""
    with psycopg.connect(DATABASE_URL) as conn:
        unheld = role_id(conn, "Board Viewer")
        conn.commit()

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _submit(run_id, actor_id, unheld)


def test_role_resolution_prefers_the_first_role_the_actor_holds(actor_id: str):
    """Ordered rather than arbitrary. After this placement one person holds every role, and an
    arbitrary pick would make the recorded role meaningless."""
    with psycopg.connect(DATABASE_URL) as conn:
        grant(conn, actor_id, "SIP Owner")
        analyst = role_id(conn, "Analyst")
        conn.commit()

    repo = ReportRepository(DATABASE_URL)

    assert repo.role_id_for(actor_id, ("Analyst", "SIP Owner")) == analyst


def test_role_resolution_refuses_an_actor_holding_none_of_them(actor_id: str):
    repo = ReportRepository(DATABASE_URL)

    with pytest.raises(DecisionNotPermittedError):
        repo.role_id_for(actor_id, ("Secretariat",))
