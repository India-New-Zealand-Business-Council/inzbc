"""Integration tests for the persistence adapter (#117), against a real Postgres.

Skipped entirely when `DATABASE_URL` isn't set, rather than mocking psycopg - a mock would prove
this module calls psycopg correctly, not that the concurrency contract actually holds against a
real database's transaction semantics, which is the entire point of `apply_transition`. CI sets
`DATABASE_URL` against a Postgres service container; run locally against any Postgres 14+ with
`database/schema.sql` applied.
"""

from __future__ import annotations

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest

from apps.sip.core.orchestrator import IllegalTransition
from apps.sip.pipeline.models import RunState
from services.api.persistence import (
    ConcurrentModificationError,
    HumanGateNotSatisfied,
    RunRepository,
)

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
            "insert into users (name, email) values (%s, %s) returning id",
            (f"Test User {uuid.uuid4()}", f"{uuid.uuid4()}@example.com"),
        ).fetchone()
        # ADR-0005 replaced users.role_id with user_roles: one principal may hold several roles,
        # because the steady state after the placement is one person holding every one of them.
        conn.execute(
            "insert into user_roles (user_id, role_id) values (%s, 1)", (row[0],)
        )
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

    updated = repo.apply_transition(
        run.id,
        expected_version=0,
        new_state=RunState.RUN_AUTHORISED,
        approval_ref="launch-authority-recorded",
        actor_id=initiated_by,
        reason="authorise run",
    )

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
    repo.apply_transition(
        run.id,
        expected_version=0,
        new_state=RunState.RUN_AUTHORISED,
        approval_ref="launch-authority-recorded",
        actor_id=initiated_by,
        reason="authorise run",
    )

    # ...so a second caller still holding version=0 (e.g. read before the first committed) must
    # be refused, not silently applied on top.
    with pytest.raises(ConcurrentModificationError):
        repo.apply_transition(
            run.id,
            expected_version=0,
            new_state=RunState.COVERAGE_LOCKED,
            actor_id=initiated_by,
            reason="lock coverage",
        )

    # The refused write must not have landed - state and version are exactly the first writer's.
    current = repo.get_run(run.id)
    assert current.state == RunState.RUN_AUTHORISED
    assert current.version == 1


def test_a_stale_caller_is_told_it_is_stale_not_that_its_transition_is_illegal(
    repo: RunRepository, initiated_by: str
) -> None:
    """Error precedence: staleness outranks legality.

    A caller that lost a race holds an old version *and* an old state, so the transition it asks
    for is usually illegal from the row's current state as well. Reporting that is misleading:
    the caller did nothing wrong and needs to re-read and retry, which is what
    `ConcurrentModificationError` tells it. This is the deterministic form of the race in
    `test_two_concurrent_transitions_cannot_both_commit`, which failed intermittently while
    legality was checked first.
    """
    run = repo.create_run(
        run_number=_run_number(),
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-07-27T07:00:00+12:00",
        coverage_end_utc="2026-07-28T07:00:00+12:00",
        initiated_by=initiated_by,
    )
    repo.apply_transition(
        run.id,
        expected_version=0,
        new_state=RunState.RUN_AUTHORISED,
        approval_ref="launch-authority-recorded",
        actor_id=initiated_by,
        reason="authorise run",
    )

    # Repeating the winner's own transition: illegal from the new state (Run Authorised has no
    # self-loop), and stale. The caller must hear about the staleness.
    with pytest.raises(ConcurrentModificationError):
        repo.apply_transition(
            run.id,
            expected_version=0,
            new_state=RunState.RUN_AUTHORISED,
            approval_ref="launch-authority-recorded",
            actor_id=initiated_by,
            reason="authorise run",
        )

    # A genuinely illegal transition at the *current* version still raises IllegalTransition, so
    # this precedence does not swallow the legality check.
    with pytest.raises(IllegalTransition):
        repo.apply_transition(
            run.id,
            expected_version=1,
            new_state=RunState.CLOSED,
            actor_id=initiated_by,
            reason="close run",
        )

    # The same self-loop as above, but at the current version, must still be IllegalTransition.
    # Without this an implementation that simply treats every self-loop as a conflict would pass:
    # the two assertions above only ever ask for a self-loop while stale, so they cannot tell
    # "checked staleness first" from "special-cased self-loops".
    with pytest.raises(IllegalTransition):
        repo.apply_transition(
            run.id,
            expected_version=1,
            new_state=RunState.RUN_AUTHORISED,
            approval_ref="launch-authority-recorded",
            actor_id=initiated_by,
            reason="authorise run",
        )


def test_apply_transition_rejects_an_illegal_state_jump(
    repo: RunRepository, initiated_by: str
) -> None:
    # Draft's only legal next state is Run Authorised (schemas/state-machine.md). Nothing must
    # let a caller commit straight to Closed - that would skip the CEO decision, approval, QA and
    # distribution record ADR-0005 requires, with no state in between showing any of it happened.
    run = repo.create_run(
        run_number=_run_number(),
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-07-27T07:00:00+12:00",
        coverage_end_utc="2026-07-28T07:00:00+12:00",
        initiated_by=initiated_by,
    )

    with pytest.raises(IllegalTransition):
        repo.apply_transition(
            run.id,
            expected_version=0,
            new_state=RunState.CLOSED,
            actor_id=initiated_by,
            reason="close run",
        )

    # The refused write must not have landed.
    current = repo.get_run(run.id)
    assert current.state == RunState.DRAFT
    assert current.version == 0


def test_apply_transition_raises_key_error_for_an_unknown_run_not_stale_version(
    repo: RunRepository,
) -> None:
    # A missing row and a stale version both used to surface as ConcurrentModificationError from
    # the same 0-row UPDATE result, so a caller couldn't tell 404 from 409. The legality check now
    # reads the row first, so a genuinely missing run raises KeyError instead.
    with pytest.raises(KeyError):
        repo.apply_transition(
            str(uuid.uuid4()),
            expected_version=0,
            new_state=RunState.CLOSED,
            actor_id=str(uuid.uuid4()),
            reason="unreached - run does not exist",
        )


def test_two_concurrent_transitions_cannot_both_commit(
    repo: RunRepository, initiated_by: str
) -> None:
    """The acceptance criterion from #117, proven against a real Postgres with two real OS
    threads racing the same UPDATE, not a sequential simulation of a race.

    Both threads target the *same* legal transition (Draft -> Run Authorised) rather than one
    legal and one illegal target - racing a legal move against an illegal one always "succeeds"
    for the legal side regardless of timing, which is what let a fake implementation with no
    version check at all pass this test. A `threading.Barrier` also forces both threads to reach
    `apply_transition` at the same instant; without it, one thread can simply finish before the
    other starts, and the test would pass by luck rather than by proving anything about the CAS.
    """
    run = repo.create_run(
        run_number=_run_number(),
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-07-27T07:00:00+12:00",
        coverage_end_utc="2026-07-28T07:00:00+12:00",
        initiated_by=initiated_by,
    )
    start = threading.Barrier(2)

    def try_advance() -> object:
        # A fresh RunRepository per thread: psycopg connections are not meant to be shared
        # across threads, and the adapter's contract is that it needs none held between calls.
        thread_repo = RunRepository(DATABASE_URL)
        start.wait()  # both threads release together, forcing a genuine race, not a fluke.
        try:
            return thread_repo.apply_transition(
                run.id,
                expected_version=0,
                new_state=RunState.RUN_AUTHORISED,
                approval_ref="launch-authority-recorded",
                actor_id=initiated_by,
                reason="authorise run",
            )
        except ConcurrentModificationError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        future_a = pool.submit(try_advance)
        future_b = pool.submit(try_advance)
        results = [future_a.result(), future_b.result()]

    succeeded = [r for r in results if not isinstance(r, Exception)]
    failed = [r for r in results if isinstance(r, ConcurrentModificationError)]

    assert len(succeeded) == 1, "exactly one of the two racing transitions must commit"
    assert len(failed) == 1, "the loser must be refused, not silently dropped or merged"

    final = repo.get_run(run.id)
    assert final.version == 1, "version must advance by exactly one commit, not two"
    assert final.state == RunState.RUN_AUTHORISED


def test_a_human_gated_transition_is_refused_without_authority(repo, initiated_by) -> None:
    """The durable path must not commit a gated move on nobody's authority.

    `Draft -> Run Authorised` is human gated. This layer used to check legality only, so it
    committed with `approval_ref` left NULL and the stored state then said the run was authorised
    with nothing anywhere showing that anyone authorised it. The in-memory orchestrator refuses
    this, but nothing reaching the database went through the orchestrator, so the guarantee stopped
    at the edge of that process.
    """
    run = repo.create_run(
        run_number=_run_number(),
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-07-27T07:00:00+12:00",
        coverage_end_utc="2026-07-28T07:00:00+12:00",
        initiated_by=initiated_by,
    )

    with pytest.raises(HumanGateNotSatisfied):
        repo.apply_transition(
            run.id,
            expected_version=0,
            new_state=RunState.RUN_AUTHORISED,
            actor_id=initiated_by,
            reason="authorise run",
        )

    assert repo.get_run(run.id).state == RunState.DRAFT
    assert repo.get_run(run.id).version == 0


def test_a_report_level_gate_needs_a_real_decision_record(repo, initiated_by) -> None:
    """Free text cannot authorise a gated transition that has somewhere to point.

    Run-level authority (launch, resumption) has no home in ADR-0005's streams yet, because those
    are keyed to a report version that does not exist at that point, so those two gates accept an
    unverifiable reference and #227 tracks giving them one. Every other gate is checked against
    `decision_records`, which is append-only, so the reference cannot later be edited into saying
    something else.
    """
    run = repo.create_run(
        run_number=_run_number(),
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-07-27T07:00:00+12:00",
        coverage_end_utc="2026-07-28T07:00:00+12:00",
        initiated_by=initiated_by,
    )

    # Walk to the first gate that is not run level. Only the first move is gated on the way.
    walk = [
        (RunState.RUN_AUTHORISED, "launch-authority-recorded"),
        (RunState.COVERAGE_LOCKED, None),
        (RunState.SCANNING, None),
        (RunState.CANDIDATE_REVIEW, None),
        (RunState.REPORT_DRAFTED, None),
        (RunState.QA_IN_PROGRESS, None),
    ]
    for version, (state, ref) in enumerate(walk):
        repo.apply_transition(
            run.id, expected_version=version, new_state=state,
            actor_id=initiated_by, reason="walk to the QA gate", approval_ref=ref,
        )

    with pytest.raises(HumanGateNotSatisfied, match="not a decision record"):
        repo.apply_transition(
            run.id, expected_version=len(walk), new_state=RunState.AWAITING_CEO_DECISION,
            actor_id=initiated_by, reason="QA sign-off",
            approval_ref="signed-off-by-me-honest",
        )

    assert repo.get_run(run.id).state == RunState.QA_IN_PROGRESS
