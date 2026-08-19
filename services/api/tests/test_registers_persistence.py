"""Integration tests for ActionRegisterRepository, WatchListRepository and ExceptionRepository
(#209), against a real Postgres. Skipped without `DATABASE_URL`, same convention as
test_source_checks.py / test_comms_persistence.py.
"""

from __future__ import annotations

import os
import uuid

import psycopg
import pytest

from services.api.registers_persistence import (
    ActionRegisterRepository,
    ExceptionRepository,
    WatchListRepository,
)

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - registers tests need a real Postgres with schema.sql applied",
)


@pytest.fixture
def action_repo() -> ActionRegisterRepository:
    return ActionRegisterRepository(DATABASE_URL)


@pytest.fixture
def watch_repo() -> WatchListRepository:
    return WatchListRepository(DATABASE_URL)


@pytest.fixture
def exception_repo() -> ExceptionRepository:
    return ExceptionRepository(DATABASE_URL)


def _make_user() -> str:
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "insert into users (name, email) values (%s, %s) returning id",
            (f"Test User {uuid.uuid4()}", f"{uuid.uuid4()}@example.com"),
        ).fetchone()
        conn.commit()
    return str(row[0])


def _make_run(initiated_by: str) -> str:
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "insert into runs (run_number, prompt_version, coverage_start_utc, "
            "coverage_end_utc, initiated_by) values (%s, %s, now() - interval '1 day', now(), %s) "
            "returning id",
            (f"RUN-TEST-{uuid.uuid4().hex[:12]}", "SIP-050-v1.1", initiated_by),
        ).fetchone()
        conn.commit()
    return str(row[0])


def _audit_rows(record_type: str, record_id: str) -> list[tuple]:
    with psycopg.connect(DATABASE_URL) as conn:
        return conn.execute(
            "select action, old_value, new_value from audit_log "
            "where record_type = %s and record_id = %s order by id",
            (record_type, record_id),
        ).fetchall()


# ---------------------------------------------------------------------------
# ActionRegisterRepository
# ---------------------------------------------------------------------------

def test_create_action_persists_open_with_no_owner_required(action_repo) -> None:
    actor = _make_user()
    action = action_repo.create(
        f"ACT-{uuid.uuid4().hex[:6]}", "Follow up with a lapsed source", "Open", actor_id=actor
    )
    assert action.status == "Open"
    assert action.closed_at is None


def test_create_action_writes_one_audit_row(action_repo) -> None:
    actor = _make_user()
    action = action_repo.create(f"ACT-{uuid.uuid4().hex[:6]}", "Title", "Open", actor_id=actor)
    rows = _audit_rows("action_register", action.id)
    assert len(rows) == 1
    assert rows[0][0] == "action_register.create"


def test_closing_an_action_sets_closed_at(action_repo) -> None:
    actor = _make_user()
    action = action_repo.create(f"ACT-{uuid.uuid4().hex[:6]}", "Title", "Open", actor_id=actor)
    closed = action_repo.update_status(
        action.id, "Closed", actor_id=actor, evidence_ref="PR #999"
    )
    assert closed.status == "Closed"
    assert closed.closed_at is not None
    assert closed.evidence_ref == "PR #999"


def test_moving_to_controlled_monitoring_does_not_set_closed_at(action_repo) -> None:
    """A status other than exactly Closed must never look closed by accident."""
    actor = _make_user()
    action = action_repo.create(f"ACT-{uuid.uuid4().hex[:6]}", "Title", "Open", actor_id=actor)
    updated = action_repo.update_status(action.id, "Controlled Monitoring", actor_id=actor)
    assert updated.status == "Controlled Monitoring"
    assert updated.closed_at is None


def test_reopening_after_close_clears_closed_at(action_repo) -> None:
    actor = _make_user()
    action = action_repo.create(f"ACT-{uuid.uuid4().hex[:6]}", "Title", "Open", actor_id=actor)
    action_repo.update_status(action.id, "Closed", actor_id=actor)
    reopened = action_repo.update_status(action.id, "Open", actor_id=actor)
    assert reopened.closed_at is None


def test_update_status_on_missing_action_raises(action_repo) -> None:
    actor = _make_user()
    with pytest.raises(KeyError):
        action_repo.update_status(
            "00000000-0000-0000-0000-000000000000", "Closed", actor_id=actor
        )


def test_get_and_list_all_round_trip(action_repo) -> None:
    actor = _make_user()
    action_repo.create(f"ACT-{uuid.uuid4().hex[:6]}", "One", "Open", actor_id=actor)
    second = action_repo.create(f"ACT-{uuid.uuid4().hex[:6]}", "Two", "Open", actor_id=actor)
    assert action_repo.get(second.id).title == "Two"
    ids = {a.id for a in action_repo.list_all()}
    assert second.id in ids


# ---------------------------------------------------------------------------
# WatchListRepository
# ---------------------------------------------------------------------------

def test_create_watch_list_entry(watch_repo) -> None:
    actor = _make_user()
    entry = watch_repo.create(
        f"WL-{uuid.uuid4().hex[:6]}", "Dairy tariff review", "Open",
        actor_id=actor, category="Opportunity Register",
    )
    assert entry.status == "Open"
    assert entry.category == "Opportunity Register"


def test_watch_list_update_status_writes_audit_with_old_and_new(watch_repo) -> None:
    actor = _make_user()
    entry = watch_repo.create(f"WL-{uuid.uuid4().hex[:6]}", "Title", "Open", actor_id=actor)
    watch_repo.update_status(entry.id, "Closed", actor_id=actor)
    rows = _audit_rows("watch_lists", entry.id)
    assert len(rows) == 2
    action, old_value, new_value = rows[1]
    assert action == "watch_list.update_status"
    assert old_value == "Open"
    assert new_value == "Closed"


def test_watch_list_update_on_missing_entry_raises(watch_repo) -> None:
    actor = _make_user()
    with pytest.raises(KeyError):
        watch_repo.update_status(
            "00000000-0000-0000-0000-000000000000", "Closed", actor_id=actor
        )


# ---------------------------------------------------------------------------
# ExceptionRepository - append-only
# ---------------------------------------------------------------------------

def test_record_an_exception(exception_repo) -> None:
    actor = _make_user()
    run_id = _make_run(actor)
    exc = exception_repo.record(
        "Source Inaccessible", "High", "Open", actor_id=actor, run_id=run_id
    )
    assert exc.run_id == run_id
    assert exc.original_preserved is True
    assert exc.correction_ref is None


def test_correcting_an_exception_leaves_the_original_untouched(exception_repo) -> None:
    """The whole point of append-only: the original row must read exactly as it did before the
    correction, not be silently rewritten."""
    actor = _make_user()
    run_id = _make_run(actor)
    original = exception_repo.record(
        "Source Inaccessible", "High", "Open", actor_id=actor, run_id=run_id
    )

    correction = exception_repo.correct(
        original.id, "Source Inaccessible", "Low", "Resolved",
        actor_id=actor, reason="fallback feed confirmed working",
    )

    reread_original = exception_repo.get(original.id)
    assert reread_original.status == "Open", "the original must not have been rewritten"
    assert reread_original.severity == "High"
    assert reread_original.correction_ref is None

    assert correction.correction_ref == original.id
    assert correction.status == "Resolved"
    assert correction.severity == "Low"


def test_a_correction_carries_forward_run_id_and_owner_from_the_original(exception_repo) -> None:
    actor = _make_user()
    owner = _make_user()
    run_id = _make_run(actor)
    original = exception_repo.record(
        "Source Inaccessible", "High", "Open", actor_id=actor, run_id=run_id, owner_id=owner
    )
    correction = exception_repo.correct(
        original.id, "Source Inaccessible", "Low", "Resolved", actor_id=actor, reason="fixed"
    )
    assert correction.run_id == run_id
    assert correction.owner_id == owner


def test_correcting_a_missing_exception_raises(exception_repo) -> None:
    actor = _make_user()
    with pytest.raises(KeyError):
        exception_repo.correct(
            "00000000-0000-0000-0000-000000000000", "x", "Low", "Resolved",
            actor_id=actor, reason="x",
        )


def test_exception_correction_writes_a_second_audit_row_not_a_rewrite(exception_repo) -> None:
    actor = _make_user()
    run_id = _make_run(actor)
    original = exception_repo.record(
        "Source Inaccessible", "High", "Open", actor_id=actor, run_id=run_id
    )
    exception_repo.correct(
        original.id, "Source Inaccessible", "Low", "Resolved", actor_id=actor, reason="fixed"
    )
    original_rows = _audit_rows("exceptions", original.id)
    assert len(original_rows) == 1, "the original's own audit history must not gain a row either"
    assert original_rows[0][0] == "exception.record"


def test_list_for_run_only_returns_that_runs_exceptions(exception_repo) -> None:
    actor = _make_user()
    run_a = _make_run(actor)
    run_b = _make_run(actor)
    exception_repo.record("Type", "Low", "Open", actor_id=actor, run_id=run_a)
    exception_repo.record("Type", "Low", "Open", actor_id=actor, run_id=run_b)
    assert len(exception_repo.list_for_run(run_a)) == 1
