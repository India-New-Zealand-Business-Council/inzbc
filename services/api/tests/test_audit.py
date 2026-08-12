"""Integration tests for the transactional audit service (#118), against a real Postgres.

Skipped when `DATABASE_URL` isn't set, like the persistence tests (#117): the whole point of #118 is
that immutability holds *in the database* — an append-only trigger and an INSERT/SELECT-only role —
so a mock that never touches Postgres would prove none of it. CI runs these against the Postgres 16
service container with `database/schema.sql` applied.

Four things are proven here:
- the append-only trigger refuses UPDATE/DELETE from any role (belt-and-braces);
- the INSERT/SELECT-only role is refused UPDATE/DELETE at the privilege layer, before the trigger;
- `record_audit` writes inside the caller's transaction and does not commit on its own;
- `apply_transition` writes a correct audit row atomically with the state change — roll the
  transition back and the audit row goes with it.
"""

from __future__ import annotations

import os
import uuid

import psycopg
import pytest

from apps.sip.pipeline.models import RunState
from services.api import persistence as persistence_module
from services.api.audit import record_audit
from services.api.persistence import AuditRepository, RunRepository
from services.api.tests.role_seed import authorise_run

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - audit tests need a real Postgres with schema.sql applied",
)

# SQLSTATE raised by reject_evidence_change() (schema.sql). 42501 is Postgres' insufficient_privilege.
APPEND_ONLY_SQLSTATE = "55000"
INSUFFICIENT_PRIVILEGE_SQLSTATE = "42501"


@pytest.fixture
def actor_id() -> str:
    """A real users.id, so an audit row's user_id FK is satisfiable."""
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "insert into users (name, email) values (%s, %s) returning id",
            (f"Audit Actor {uuid.uuid4()}", f"{uuid.uuid4()}@example.com"),
        ).fetchone()
        conn.commit()
    return str(row[0])


@pytest.fixture
def repo() -> RunRepository:
    return RunRepository(DATABASE_URL)


@pytest.fixture
def run_id(repo: RunRepository, actor_id: str) -> str:
    run = repo.create_run(
        run_number=f"RUN-AUDIT-{uuid.uuid4().hex[:12]}",
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-07-27T07:00:00+12:00",
        coverage_end_utc="2026-07-28T07:00:00+12:00",
        initiated_by=actor_id,
    )
    return run.id


def _insert_row(user_id: str | None = None) -> int:
    with psycopg.connect(DATABASE_URL) as conn:
        row_id = record_audit(conn, action="test.write", user_id=user_id, reason="seed")
        conn.commit()
    return row_id


def test_update_on_audit_log_is_refused_by_the_trigger() -> None:
    """Even the table owner (the CI superuser) cannot rewrite an audit row."""
    row_id = _insert_row()
    with psycopg.connect(DATABASE_URL) as conn:
        with pytest.raises(psycopg.Error) as exc:
            conn.execute("update audit_log set reason = %s where id = %s", ("tampered", row_id))
        assert exc.value.sqlstate == APPEND_ONLY_SQLSTATE
        conn.rollback()


def test_delete_on_audit_log_is_refused_by_the_trigger() -> None:
    row_id = _insert_row()
    with psycopg.connect(DATABASE_URL) as conn:
        with pytest.raises(psycopg.Error) as exc:
            conn.execute("delete from audit_log where id = %s", (row_id,))
        assert exc.value.sqlstate == APPEND_ONLY_SQLSTATE
        conn.rollback()


def test_insert_select_only_role_cannot_update_or_delete() -> None:
    """The grant in database/audit_role.sql is the real boundary: a role without UPDATE/DELETE is
    refused at the privilege layer (42501), *before* the trigger runs. Uses a uniquely-named,
    NOLOGIN role reached via SET ROLE, so no password or separate connection is needed and cleanup
    is exact.
    """
    role = f"audit_role_{uuid.uuid4().hex[:8]}"
    row_id = _insert_row()
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(f'create role "{role}" nologin')
        try:
            conn.execute(f'revoke all on table audit_log from "{role}"')
            conn.execute(f'grant insert, select on table audit_log to "{role}"')
            conn.execute(f'grant usage, select on sequence audit_log_id_seq to "{role}"')
            conn.commit()

            conn.execute(f'set role "{role}"')

            # INSERT and SELECT are granted, so they must work as this role.
            conn.execute(
                "insert into audit_log (action, reason) values (%s, %s)",
                ("role.insert", "allowed"),
            )
            assert conn.execute("select count(*) from audit_log").fetchone()[0] >= 1

            with pytest.raises(psycopg.Error) as update_exc:
                conn.execute("update audit_log set reason = %s where id = %s", ("x", row_id))
            assert update_exc.value.sqlstate == INSUFFICIENT_PRIVILEGE_SQLSTATE
            conn.rollback()

            conn.execute(f'set role "{role}"')
            with pytest.raises(psycopg.Error) as delete_exc:
                conn.execute("delete from audit_log where id = %s", (row_id,))
            assert delete_exc.value.sqlstate == INSUFFICIENT_PRIVILEGE_SQLSTATE
            conn.rollback()
        finally:
            conn.execute("reset role")
            conn.execute(f'drop owned by "{role}"')
            conn.execute(f'drop role "{role}"')
            conn.commit()


def test_record_audit_writes_inside_the_callers_transaction_and_does_not_commit() -> None:
    """A rollback must discard the row: record_audit owning its own commit would defeat #118's
    'state and audit commit together or not at all'.
    """
    marker = f"rollback-{uuid.uuid4()}"
    with psycopg.connect(DATABASE_URL) as conn:
        record_audit(conn, action="test.rollback", reason=marker)
        conn.rollback()

    with psycopg.connect(DATABASE_URL) as conn:
        count = conn.execute(
            "select count(*) from audit_log where reason = %s", (marker,)
        ).fetchone()[0]
    assert count == 0, "record_audit must not commit on its own; a rollback should discard it"


def test_apply_transition_writes_a_matching_audit_row(
    repo: RunRepository, run_id: str, actor_id: str
) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        authorisation = authorise_run(conn, run_id, actor_id)

    repo.apply_transition(
        run_id,
        expected_version=0,
        new_state=RunState.RUN_AUTHORISED,
        actor_id=actor_id,
        reason="authorise the daily run",
        approval_ref=authorisation,
    )

    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "select user_id, action, record_type, record_id, old_value, new_value, reason, "
            "approval_ref from audit_log where record_type = 'runs' and record_id = %s "
            "and action = 'run.transition'",
            (run_id,),
        ).fetchone()

    assert row is not None, "a committed transition must leave exactly one audit row"
    user_id, action, record_type, record_id, old_value, new_value, reason, approval_ref = row
    assert str(user_id) == actor_id
    assert action == "run.transition"
    assert record_type == "runs"
    assert record_id == run_id
    assert old_value == RunState.DRAFT.value
    assert new_value == RunState.RUN_AUTHORISED.value
    assert reason == "authorise the daily run"
    # The recorded reference is the authorisation's own id, which is the point: the audit row
    # points at an append-only record rather than repeating a string somebody typed.
    assert approval_ref == authorisation


def test_a_failed_audit_write_rolls_back_the_state_change(
    repo: RunRepository, run_id: str, actor_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Atomicity: if the audit write fails, the transition must not land either. Force record_audit
    to raise after the UPDATE and confirm the run is untouched and no audit row exists — the state
    change and its audit record commit together or not at all.
    """

    with psycopg.connect(DATABASE_URL) as conn:
        authorisation = authorise_run(conn, run_id, actor_id)

    def boom(*_args: object, **_kwargs: object) -> int:
        raise RuntimeError("audit write failed")

    monkeypatch.setattr(persistence_module, "record_audit", boom)

    with pytest.raises(RuntimeError, match="audit write failed"):
        repo.apply_transition(
            run_id,
            expected_version=0,
            new_state=RunState.RUN_AUTHORISED,
            approval_ref=authorisation,
            actor_id=actor_id,
            reason="authorise the daily run",
        )

    # State rolled back with the failed audit write...
    current = repo.get_run(run_id)
    assert current.state == RunState.DRAFT
    assert current.version == 0

    # ...and no *transition* audit row was left behind. The run's creation row stays, because
    # create_run is itself an audited write and committed long before this attempt.
    with psycopg.connect(DATABASE_URL) as conn:
        count = conn.execute(
            "select count(*) from audit_log where record_type = 'runs' and record_id = %s "
            "and action = 'run.transition'",
            (run_id,),
        ).fetchone()[0]
    assert count == 0


# ---------- read path (#126) ----------


def test_the_trail_reads_back_newest_first(repo: RunRepository, run_id: str, actor_id: str) -> None:
    """Ordered by id, not by `at`.

    `at` defaults to `now()`, which in Postgres is transaction start time, so rows written in one
    transaction share a timestamp and ordering by it leaves their real order undefined. `create_run`
    and its transition are separate transactions here, but a run that moved twice inside one would
    tie, and that is exactly the sequence the trail exists to record.
    """
    with psycopg.connect(DATABASE_URL) as conn:
        authorisation = authorise_run(conn, run_id, actor_id)
    repo.apply_transition(
        run_id, expected_version=0, new_state=RunState.RUN_AUTHORISED,
        actor_id=actor_id, reason="authorise", approval_ref=authorisation,
    )

    entries = AuditRepository(DATABASE_URL).for_run(run_id)

    assert [e.action for e in entries] == ["run.transition", "run.create"]
    assert entries[0].id > entries[1].id


def test_the_trail_only_returns_this_runs_rows(
    repo: RunRepository, run_id: str, actor_id: str
) -> None:
    """`record_id` is text and holds ids from several tables, so filtering on it alone could
    return a candidate that happened to share a uuid string."""
    other = repo.create_run(
        run_number=f"RUN-AUDIT-{uuid.uuid4().hex[:12]}",
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-07-27T07:00:00+12:00",
        coverage_end_utc="2026-07-28T07:00:00+12:00",
        initiated_by=actor_id,
    )

    entries = AuditRepository(DATABASE_URL).for_run(run_id)

    assert entries, "the run's own create row must be there"
    assert all(e.record_id == run_id for e in entries)
    assert other.id not in {e.record_id for e in entries}


def test_the_cursor_pages_without_repeating_or_skipping(
    repo: RunRepository, run_id: str, actor_id: str
) -> None:
    """Keyset pagination over an append-only table: every row appears exactly once."""
    with psycopg.connect(DATABASE_URL) as conn:
        for _ in range(4):
            record_audit(conn, action="test.page", record_type="runs", record_id=run_id)
        conn.commit()

    audit = AuditRepository(DATABASE_URL)
    first = audit.for_run(run_id, limit=2)
    second = audit.for_run(run_id, limit=2, before_id=first[-1].id)

    ids = [e.id for e in first + second]
    assert len(ids) == 4
    assert len(set(ids)) == 4, "a row was returned on both pages"
    assert ids == sorted(ids, reverse=True)


def test_an_unreasonable_limit_is_clamped_not_obeyed(
    repo: RunRepository, run_id: str, actor_id: str
) -> None:
    """The adapter bounds the read itself. The router validates too, but an unbounded scan is the
    kind of thing a later caller reaches for directly."""
    audit = AuditRepository(DATABASE_URL)

    assert len(audit.for_run(run_id, limit=10_000)) <= 500
    assert audit.for_run(run_id, limit=0), "a nonsense limit must not return nothing"


def test_rehydrate_rebuilds_the_run_from_its_stored_transitions(
    repo: RunRepository, run_id: str, actor_id: str
) -> None:
    """The whole point of #116: the database is the source of truth after a restart.

    Written against real rows rather than a fake, because the thing under test is that what
    `apply_transition` *wrote* is what `from_history` can *read*. A fake would only prove the two
    halves of my own assumption agree.
    """
    with psycopg.connect(DATABASE_URL) as conn:
        authorisation = authorise_run(conn, run_id, actor_id)
    repo.apply_transition(
        run_id, expected_version=0, new_state=RunState.RUN_AUTHORISED,
        actor_id=actor_id, reason="authorise", approval_ref=authorisation,
    )
    repo.apply_transition(
        run_id, expected_version=1, new_state=RunState.COVERAGE_LOCKED,
        actor_id=actor_id, reason="lock coverage",
    )

    resumed = AuditRepository(DATABASE_URL).rehydrate(run_id)

    assert resumed.state is RunState.COVERAGE_LOCKED
    assert resumed.run_id == run_id
    assert [r.to_state for r in resumed.history] == [
        RunState.RUN_AUTHORISED, RunState.COVERAGE_LOCKED
    ]


def test_rehydrate_preserves_when_each_transition_happened(
    repo: RunRepository, run_id: str, actor_id: str
) -> None:
    """A trail whose timestamps move to boot time on every restart is not a trail."""
    with psycopg.connect(DATABASE_URL) as conn:
        authorisation = authorise_run(conn, run_id, actor_id)
    repo.apply_transition(
        run_id, expected_version=0, new_state=RunState.RUN_AUTHORISED,
        actor_id=actor_id, reason="authorise", approval_ref=authorisation,
    )

    with psycopg.connect(DATABASE_URL) as conn:
        stored_at = conn.execute(
            "select at from audit_log where record_id = %s and action = 'run.transition'",
            (run_id,),
        ).fetchone()[0]

    resumed = AuditRepository(DATABASE_URL).rehydrate(run_id)

    assert resumed.history[0].at == stored_at
    assert str(resumed.history[0].actor) == actor_id


def test_rehydrating_a_run_that_never_moved_gives_a_draft(
    repo: RunRepository, run_id: str
) -> None:
    """A created run has a `run.create` row and no transitions. Refusing that would make the first
    resume after creation fail, which is the most common case of all."""
    resumed = AuditRepository(DATABASE_URL).rehydrate(run_id)

    assert resumed.state is RunState.DRAFT
    assert resumed.history == ()
