"""Integration tests for the persistence adapter (#117), against a real Postgres.

Skipped entirely when `DATABASE_URL` isn't set, rather than mocking psycopg - a mock would prove
this module calls psycopg correctly, not that the concurrency contract actually holds against a
real database's transaction semantics, which is the entire point of `apply_transition`. CI sets
`DATABASE_URL` against a Postgres service container; run locally against any Postgres 14+ with
`database/schema.sql` applied.
"""

from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest

from apps.sip.pipeline.models import RunState
from services.api.persistence import ConcurrentModificationError, RunRepository

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - persistence tests need a real Postgres with schema.sql applied",
)


@pytest.fixture
def repo() -> RunRepository:
    return RunRepository(DATABASE_URL)


@pytest.fixture
def initiated_by() -> str:
    """A real users.id to satisfy runs.initiated_by's NOT NULL FK - inserted directly rather than
    through any app code, since seeding a user isn't this adapter's concern.
    """
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "insert into roles (id, name) values (1, 'Analyst') on conflict do nothing"
        )
        row = conn.execute(
            "insert into users (name, email, role_id) values (%s, %s, 1) returning id",
            (f"Test User {uuid.uuid4()}", f"{uuid.uuid4()}@example.com"),
        ).fetchone()
        conn.commit()
    return str(row[0])


def _run_number() -> str:
    return f"RUN-TEST-{uuid.uuid4().hex[:12]}"


def test_create_run_starts_at_version_zero_in_draft(
    repo: RunRepository, initiated_by: str
) -> None:
    run = repo.create_run(
        run_number=_run_number(),
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-07-27T07:00:00+12:00",
        coverage_end_utc="2026-07-28T07:00:00+12:00",
        initiated_by=initiated_by,
    )

    assert run.version == 0
    assert run.state == RunState.DRAFT
    assert run.initiated_by == initiated_by


def test_get_run_reads_back_what_was_created(repo: RunRepository, initiated_by: str) -> None:
    created = repo.create_run(
        run_number=_run_number(),
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-07-27T07:00:00+12:00",
        coverage_end_utc="2026-07-28T07:00:00+12:00",
        initiated_by=initiated_by,
    )

    fetched = repo.get_run(created.id)

    assert fetched == created


def test_get_run_raises_key_error_for_an_unknown_id(repo: RunRepository) -> None:
    with pytest.raises(KeyError):
        repo.get_run(str(uuid.uuid4()))


def test_apply_transition_commits_and_advances_version(
    repo: RunRepository, initiated_by: str
) -> None:
    run = repo.create_run(
        run_number=_run_number(),
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-07-27T07:00:00+12:00",
        coverage_end_utc="2026-07-28T07:00:00+12:00",
        initiated_by=initiated_by,
    )

    updated = repo.apply_transition(run.id, expected_version=0, new_state=RunState.RUN_AUTHORISED)

    assert updated.state == RunState.RUN_AUTHORISED
    assert updated.version == 1


def test_apply_transition_raises_when_version_is_stale(
    repo: RunRepository, initiated_by: str
) -> None:
    run = repo.create_run(
        run_number=_run_number(),
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-07-27T07:00:00+12:00",
        coverage_end_utc="2026-07-28T07:00:00+12:00",
        initiated_by=initiated_by,
    )
    # A first transition commits and moves the row to version 1...
    repo.apply_transition(run.id, expected_version=0, new_state=RunState.RUN_AUTHORISED)

    # ...so a second caller still holding version=0 (e.g. read before the first committed) must
    # be refused, not silently applied on top.
    with pytest.raises(ConcurrentModificationError):
        repo.apply_transition(run.id, expected_version=0, new_state=RunState.COVERAGE_LOCKED)

    # The refused write must not have landed - state and version are exactly the first writer's.
    current = repo.get_run(run.id)
    assert current.state == RunState.RUN_AUTHORISED
    assert current.version == 1


def test_two_concurrent_transitions_cannot_both_commit(
    repo: RunRepository, initiated_by: str
) -> None:
    """The acceptance criterion from #117, proven against a real Postgres with two real OS
    threads racing the same UPDATE, not a sequential simulation of a race.
    """
    run = repo.create_run(
        run_number=_run_number(),
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-07-27T07:00:00+12:00",
        coverage_end_utc="2026-07-28T07:00:00+12:00",
        initiated_by=initiated_by,
    )

    def try_advance(target: RunState) -> object:
        # A fresh RunRepository per thread: psycopg connections are not meant to be shared
        # across threads, and the adapter's contract is that it needs none held between calls.
        thread_repo = RunRepository(DATABASE_URL)
        try:
            return thread_repo.apply_transition(run.id, expected_version=0, new_state=target)
        except ConcurrentModificationError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        future_a = pool.submit(try_advance, RunState.RUN_AUTHORISED)
        future_b = pool.submit(try_advance, RunState.STOPPED)
        results = [future_a.result(), future_b.result()]

    succeeded = [r for r in results if not isinstance(r, Exception)]
    failed = [r for r in results if isinstance(r, ConcurrentModificationError)]

    assert len(succeeded) == 1, "exactly one of the two racing transitions must commit"
    assert len(failed) == 1, "the loser must be refused, not silently dropped or merged"

    final = repo.get_run(run.id)
    assert final.version == 1, "version must advance by exactly one commit, not two"
    assert final.state == succeeded[0].state, "the final state must be the winner's, not a mix"
