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
