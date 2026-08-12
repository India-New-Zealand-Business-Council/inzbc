"""The dashboard aggregate against a real Postgres (#47).

The counting happens in SQL, so a fake would prove nothing about it. These tests exist for the
three things the query can get wrong quietly: a state that should read 0 going missing, the
`included` filter counting the wrong rows, and overdue being decided by the wrong clock.
"""

from __future__ import annotations

import os
import uuid

import psycopg
import pytest

from apps.sip.pipeline.models import VerificationState
from services.api.persistence import (
    VERIFICATION_STATES,
    DashboardRepository,
    RunRepository,
)
from services.api.tests.role_seed import grant

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - dashboard aggregate tests need a real Postgres",
)


@pytest.fixture
def actor_id() -> str:
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "insert into users (name, email) values (%s, %s) returning id",
            (f"Dash User {uuid.uuid4()}", f"{uuid.uuid4()}@example.com"),
        ).fetchone()
        grant(conn, row[0], "Analyst")
        conn.commit()
    return str(row[0])


@pytest.fixture
def run_id(actor_id: str) -> str:
    run = RunRepository(DATABASE_URL).create_run(
        run_number=f"RUN-DASH-{uuid.uuid4().hex[:12]}",
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-08-12T07:00:00+12:00",
        coverage_end_utc="2026-08-13T07:00:00+12:00",
        initiated_by=actor_id,
    )
    return run.id


def _candidate(run_id: str, actor_id: str, *, verification: str, included: bool | None) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "insert into candidates (run_id, headline, captured_by, verification, included) "
            "values (%s, %s, %s, %s, %s)",
            (run_id, f"Headline {uuid.uuid4().hex[:8]}", actor_id, verification, included),
        )
        conn.commit()


def test_counts_come_back_per_verification_state(run_id: str, actor_id: str) -> None:
    _candidate(run_id, actor_id, verification=VerificationState.VERIFIED.value, included=True)
    _candidate(run_id, actor_id, verification=VerificationState.VERIFIED.value, included=False)
    _candidate(run_id, actor_id, verification=VerificationState.UNVERIFIED.value, included=None)

    summary = DashboardRepository(DATABASE_URL).summary()

    assert summary.total_candidates == 3
    assert summary.included_candidates == 1
    assert summary.by_verification["Verified"] == 2
    assert summary.by_verification["Unverified"] == 1


def test_a_state_with_no_candidates_reads_zero_rather_than_going_missing(
    run_id: str, actor_id: str
) -> None:
    """`GROUP BY` returns no row for a value nothing matches. A missing key and a zero mean
    different things to the panel reading them, and the UI would have to know the enum to tell
    them apart, which is the coupling this endpoint removes."""
    _candidate(run_id, actor_id, verification=VerificationState.VERIFIED.value, included=True)

    summary = DashboardRepository(DATABASE_URL).summary()

    assert set(summary.by_verification) == set(VERIFICATION_STATES)
    assert summary.by_verification["Rejected"] == 0


def test_included_counts_only_true_not_merely_decided(run_id: str, actor_id: str) -> None:
    """`included` is nullable: null means undecided, false means deliberately excluded. Counting
    "not null" instead of "true" would report an exclusion as an inclusion."""
    _candidate(run_id, actor_id, verification=VerificationState.VERIFIED.value, included=True)
    _candidate(run_id, actor_id, verification=VerificationState.VERIFIED.value, included=False)
    _candidate(run_id, actor_id, verification=VerificationState.VERIFIED.value, included=None)

    summary = DashboardRepository(DATABASE_URL).summary()

    assert summary.total_candidates == 3
    assert summary.included_candidates == 1


def test_coverage_is_for_the_current_run_only(run_id: str, actor_id: str) -> None:
    """The newest run is the current one. A count spanning every run ever would grow forever and
    describe nothing."""
    _candidate(run_id, actor_id, verification=VerificationState.VERIFIED.value, included=True)
    newer = RunRepository(DATABASE_URL).create_run(
        run_number=f"RUN-DASH-{uuid.uuid4().hex[:12]}",
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-08-12T07:00:00+12:00",
        coverage_end_utc="2026-08-13T07:00:00+12:00",
        initiated_by=actor_id,
    )

    summary = DashboardRepository(DATABASE_URL).summary()

    assert summary.run is not None
    assert summary.run.id == newer.id
    assert summary.total_candidates == 0, "counted the previous run's candidates"


def test_open_actions_exclude_closed_ones_and_mark_overdue(actor_id: str) -> None:
    """Overdue is decided by the database's clock, so a client with a wrong one cannot make a late
    action look on time."""
    late = f"ACT-{uuid.uuid4().hex[:6]}"
    future = f"ACT-{uuid.uuid4().hex[:6]}"
    closed = f"ACT-{uuid.uuid4().hex[:6]}"
    # Due dates computed by the database, not by Python. The behaviour under test is that the
    # database decides what is overdue, so a test that supplied the client's idea of today would
    # be comparing two clocks and passing for the wrong reason.
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "insert into action_register (action_code, title, status, due_date, owner_id) "
            "values (%s, %s, 'Open', current_date - 3, %s)",
            (late, "Overdue action", actor_id),
        )
        conn.execute(
            "insert into action_register (action_code, title, status, due_date) "
            "values (%s, %s, 'Open', current_date + 30)",
            (future, "Future action"),
        )
        conn.execute(
            "insert into action_register (action_code, title, status, closed_at) "
            "values (%s, %s, 'Closed', now())",
            (closed, "Closed action"),
        )
        conn.commit()

    actions = {a.action_code: a for a in DashboardRepository(DATABASE_URL).summary().open_actions}

    assert actions[late].overdue is True
    assert actions[future].overdue is False
    assert closed not in actions, "a closed action is not an open one"


def test_the_owner_falls_back_to_the_free_text_name(actor_id: str) -> None:
    """`action_register` carries either a user reference or a text owner. Reporting an unowned
    action rather than dropping it matters: an action with no owner is the one to chase."""
    code = f"ACT-{uuid.uuid4().hex[:6]}"
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "insert into action_register (action_code, title, status, owner_text) "
            "values (%s, %s, 'Open', %s)",
            (code, "Text-owned action", "Executive Sponsor"),
        )
        conn.commit()

    actions = {a.action_code: a for a in DashboardRepository(DATABASE_URL).summary().open_actions}

    assert actions[code].owner == "Executive Sponsor"
