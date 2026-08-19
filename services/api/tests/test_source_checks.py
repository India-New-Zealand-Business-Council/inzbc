"""Integration tests for SourceCheckRepository (#55), against a real Postgres. Skipped without
`DATABASE_URL`, same convention as test_persistence.py.
"""

from __future__ import annotations

import os
import uuid

import psycopg
import pytest

from apps.sip.pipeline.models import SourceOutcome
from services.api.source_checks import SourceCheckRepository

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - source_checks tests need a real Postgres with schema.sql applied",
)


@pytest.fixture
def repo() -> SourceCheckRepository:
    return SourceCheckRepository(DATABASE_URL)


@pytest.fixture
def run_and_source() -> tuple[str, str]:
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("insert into roles (id, name) values (1, 'Analyst') on conflict do nothing")
        user_row = conn.execute(
            "insert into users (name, email) values (%s, %s) returning id",
            (f"Test User {uuid.uuid4()}", f"{uuid.uuid4()}@example.com"),
        ).fetchone()
        run_row = conn.execute(
            "insert into runs (run_number, prompt_version, coverage_start_utc, "
            "coverage_end_utc, initiated_by) values (%s, %s, now() - interval '1 day', now(), %s) "
            "returning id",
            (f"RUN-TEST-{uuid.uuid4().hex[:12]}", "SIP-050-v1.1", user_row[0]),
        ).fetchone()
        source_row = conn.execute(
            "insert into source_library (sip185_code, name, layer, mandatory) "
            "values (%s, %s, 1, true) returning id",
            (f"TEST-{uuid.uuid4().hex[:8]}", "Test Source"),
        ).fetchone()
        conn.commit()

    yield str(run_row[0]), str(source_row[0])

    # `source_checks.source_id` has no ON DELETE CASCADE (unlike run_id) - a source check must
    # not silently vanish just because a source_library row is deleted. Delete the run first
    # (cascades source_checks), then the source, so another test's `delete from source_library`
    # doesn't hit a dangling FK from a row this fixture forgot to clean up.
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("delete from runs where id = %s", (run_row[0],))
        conn.execute("delete from source_library where id = %s", (source_row[0],))
        conn.commit()


def test_record_creates_a_row(repo: SourceCheckRepository, run_and_source: tuple[str, str]):
    run_id, source_id = run_and_source
    record = repo.record(
        run_id=run_id,
        source_id=source_id,
        outcome=SourceOutcome.INCLUDED,
        method="Direct access",
        fallback_used=False,
        access_error=None,
        notes=None,
    )
    assert record.run_id == run_id
    assert record.source_id == source_id
    assert record.outcome == SourceOutcome.INCLUDED


def test_record_twice_for_the_same_source_updates_the_existing_row(
    repo: SourceCheckRepository, run_and_source: tuple[str, str]
):
    run_id, source_id = run_and_source
    first = repo.record(
        run_id=run_id,
        source_id=source_id,
        outcome=SourceOutcome.INACCESSIBLE,
        method="Direct access",
        fallback_used=False,
        access_error="timeout",
        notes=None,
    )
    second = repo.record(
        run_id=run_id,
        source_id=source_id,
        outcome=SourceOutcome.INCLUDED,
        method="RSS or approved feed",
        fallback_used=True,
        access_error=None,
        notes="fell back to RSS",
    )

    assert second.id == first.id
    rows = repo.list_for_run(run_id)
    assert len(rows) == 1
    assert rows[0].outcome == SourceOutcome.INCLUDED
    assert rows[0].fallback_used is True


def test_list_for_run_only_returns_that_runs_checks(
    repo: SourceCheckRepository, run_and_source: tuple[str, str]
):
    run_id, source_id = run_and_source
    repo.record(
        run_id=run_id,
        source_id=source_id,
        outcome=SourceOutcome.INCLUDED,
        method=None,
        fallback_used=False,
        access_error=None,
        notes=None,
    )
    other_run_id = "00000000-0000-0000-0000-000000000000"
    assert repo.list_for_run(other_run_id) == []
    assert len(repo.list_for_run(run_id)) == 1


def _actor_for(run_id: str) -> str:
    """The run's initiator, reused as the acting user so the audit assertions have a real id."""
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute("select initiated_by from runs where id = %s", (run_id,)).fetchone()
    return str(row[0])


def _audit_rows(record_id: str) -> list[tuple]:
    with psycopg.connect(DATABASE_URL) as conn:
        return conn.execute(
            "select action, old_value, new_value, user_id from audit_log "
            "where record_type = 'source_checks' and record_id = %s order by id",
            (record_id,),
        ).fetchall()


def test_recording_a_source_check_writes_an_audit_row(
    repo: SourceCheckRepository, run_and_source: tuple[str, str]
):
    run_id, source_id = run_and_source
    actor = _actor_for(run_id)

    record = repo.record(
        run_id=run_id,
        source_id=source_id,
        outcome=SourceOutcome.INCLUDED,
        method="Direct access",
        fallback_used=False,
        access_error=None,
        notes=None,
        actor_id=actor,
    )

    rows = _audit_rows(record.id)
    assert len(rows) == 1
    action, old_value, new_value, user_id = rows[0]
    assert action == "source_check.record"
    assert old_value is None, "a first recording has no prior value to describe"
    assert new_value == SourceOutcome.INCLUDED.value
    assert str(user_id) == actor


def test_overwriting_an_outcome_records_what_it_replaced(
    repo: SourceCheckRepository, run_and_source: tuple[str, str]
):
    """The reason this table is audited at all.

    `source_checks` is not append-only, so the upsert overwrites in place. Without the audit row,
    a source recorded `Inaccessible` becoming `Included` leaves no trace that it ever said
    otherwise - on the register an auditor checks a run against. The prior outcome has to survive
    the write that replaces it.
    """
    run_id, source_id = run_and_source
    actor = _actor_for(run_id)

    first = repo.record(
        run_id=run_id,
        source_id=source_id,
        outcome=SourceOutcome.INACCESSIBLE,
        method="Direct access",
        fallback_used=False,
        access_error="timeout",
        notes=None,
        actor_id=actor,
    )
    repo.record(
        run_id=run_id,
        source_id=source_id,
        outcome=SourceOutcome.INCLUDED,
        method="RSS or approved feed",
        fallback_used=True,
        access_error=None,
        notes="fell back to RSS",
        actor_id=actor,
    )

    rows = _audit_rows(first.id)
    assert len(rows) == 2, "the correction is a second event, not an edit of the first"

    action, old_value, new_value, _ = rows[1]
    assert action == "source_check.update", "a changed answer is a different event to an auditor"
    assert old_value == SourceOutcome.INACCESSIBLE.value
    assert new_value == SourceOutcome.INCLUDED.value


def test_the_audit_row_and_the_check_land_together(
    repo: SourceCheckRepository, run_and_source: tuple[str, str]
):
    """One commit, so there is no state where the check exists unaudited or the reverse.

    Asserted by counting both sides after a write rather than by inspecting the transaction: what
    matters is that a reader never sees one without the other.
    """
    run_id, source_id = run_and_source

    record = repo.record(
        run_id=run_id,
        source_id=source_id,
        outcome=SourceOutcome.EXCLUDED,
        method=None,
        fallback_used=False,
        access_error=None,
        notes=None,
        actor_id=_actor_for(run_id),
    )

    assert len(repo.list_for_run(run_id)) == 1
    assert len(_audit_rows(record.id)) == 1
