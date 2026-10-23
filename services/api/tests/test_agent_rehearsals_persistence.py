"""`agent_rehearsals` against real Postgres: stored, read back exactly, audited, append-only."""

from __future__ import annotations

import os
import uuid

import psycopg
import pytest

from apps.sip.core.agent_record import audit_from_json, audit_to_json
from apps.sip.core.audit_seal import audit_chain_head
from apps.sip.core.eval._fixtures import redaction_policy
from apps.sip.core.eval.replay_fidelity import execute, generate
from services.api.agent_rehearsals import AgentRehearsalRepository
from services.api.persistence import RunRepository

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - rehearsal persistence needs a real Postgres with schema.sql",
)

APPEND_ONLY_SQLSTATE = "55000"


@pytest.fixture
def actor_id() -> str:
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "insert into users (name, email) values (%s, %s) returning id",
            (f"Rehearsal Actor {uuid.uuid4()}", f"{uuid.uuid4()}@example.com"),
        ).fetchone()
        conn.commit()
    return str(row[0])


@pytest.fixture
def run_id(actor_id: str) -> str:
    return RunRepository(DATABASE_URL).create_run(
        run_number=f"RUN-REH-{uuid.uuid4().hex[:12]}", prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-07-27T07:00:00+12:00",
        coverage_end_utc="2026-07-28T07:00:00+12:00", initiated_by=actor_id,
    ).id


def _stored(run_id: str, actor_id: str):
    with redaction_policy():
        audit = execute(generate(3, 0)).audit_log()
    repo = AgentRehearsalRepository(DATABASE_URL)
    record = repo.record(
        run_id=run_id, started_by=actor_id, outcome="reached_qa", stop_reason=None,
        final_state=audit.transitions[-1].to_state.value, steps=len(audit.tool_records),
        audit=audit_to_json(audit), chain_head=audit_chain_head(audit), seal=None,
    )
    return repo, record, audit


def test_a_stored_trail_reads_back_with_the_same_chain_head(run_id: str, actor_id: str) -> None:
    repo, record, audit = _stored(run_id, actor_id)

    read = repo.get(run_id, record.id)
    assert audit_chain_head(audit_from_json(read.audit)) == audit_chain_head(audit)
    assert read.chain_head == record.chain_head
    assert [r.id for r in repo.for_run(run_id)] == [record.id]
    with pytest.raises(KeyError):
        repo.get(run_id, str(uuid.uuid4()))


def test_starting_a_rehearsal_writes_an_audit_row_naming_who(run_id: str, actor_id: str) -> None:
    _repo, record, _audit = _stored(run_id, actor_id)

    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "select user_id, new_value, approval_ref from audit_log "
            "where record_id = %s and action = 'agent.rehearsal'", (run_id,),
        ).fetchone()
    assert (str(row[0]), row[1], row[2]) == (actor_id, "reached_qa", record.id)


@pytest.mark.parametrize("statement", [
    "update agent_rehearsals set outcome = 'stopped', stop_reason = 'x' where id = %s",
    "delete from agent_rehearsals where id = %s",
])
def test_a_stored_trail_cannot_be_rewritten(run_id: str, actor_id: str, statement: str) -> None:
    _repo, record, _audit = _stored(run_id, actor_id)

    with psycopg.connect(DATABASE_URL) as conn, pytest.raises(psycopg.Error) as refused:
        conn.execute(statement, (record.id,))
    assert refused.value.sqlstate == APPEND_ONLY_SQLSTATE


def test_a_stop_needs_a_reason(run_id: str, actor_id: str) -> None:
    with redaction_policy():
        audit = execute(generate(3, 1)).audit_log()
    with pytest.raises(psycopg.errors.CheckViolation):
        AgentRehearsalRepository(DATABASE_URL).record(
            run_id=run_id, started_by=actor_id, outcome="stopped", stop_reason="  ",
            final_state="Scanning", steps=1, audit=audit_to_json(audit),
            chain_head=audit_chain_head(audit), seal=None,
        )
