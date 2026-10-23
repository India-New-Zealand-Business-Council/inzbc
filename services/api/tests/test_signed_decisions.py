"""Signed human decisions in the persisted run path (Studio 6 W6 change), against real Postgres.

`apply_transition` signs a gated transition with the server-held key when it records it, and
`rehydrate` verifies the signature before it rebuilds the decision. Without this, a row written
straight into `audit_log` by anyone holding INSERT could carry a well-formed approval reference
and replay as a genuine human decision (the forged-decision gap in
`docs/research/agent-safety-baseline.md`).
"""

from __future__ import annotations

import os
import uuid

import psycopg
import pytest

from apps.sip.core.audit_seal import (
    REQUIRE_SIGNED_ENV,
    SIGNING_KEY_ENV,
    SigningKeyError,
    sign_decision,
)
from apps.sip.core.orchestrator import CorruptHistory
from apps.sip.pipeline.models import RunState
from services.api.audit import record_audit
from services.api.persistence import AuditRepository, RunRepository
from services.api.tests.role_seed import authorise_run

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - signed-decision tests need a real Postgres with schema.sql",
)

KEY = "test-only-decision-signing-key-0123456789abcdef"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(SIGNING_KEY_ENV, raising=False)
    monkeypatch.delenv(REQUIRE_SIGNED_ENV, raising=False)


@pytest.fixture
def actor_id() -> str:
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "insert into users (name, email) values (%s, %s) returning id",
            (f"Signing Actor {uuid.uuid4()}", f"{uuid.uuid4()}@example.com"),
        ).fetchone()
        conn.commit()
    return str(row[0])


@pytest.fixture
def repo() -> RunRepository:
    return RunRepository(DATABASE_URL)


@pytest.fixture
def run_id(repo: RunRepository, actor_id: str) -> str:
    return repo.create_run(
        run_number=f"RUN-SIGN-{uuid.uuid4().hex[:12]}",
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-07-27T07:00:00+12:00",
        coverage_end_utc="2026-07-28T07:00:00+12:00",
        initiated_by=actor_id,
    ).id


def _authorise_through_the_api(repo: RunRepository, run_id: str, actor_id: str) -> str:
    with psycopg.connect(DATABASE_URL) as conn:
        authorisation = authorise_run(conn, run_id, actor_id)
    repo.apply_transition(
        run_id, expected_version=0, new_state=RunState.RUN_AUTHORISED,
        actor_id=actor_id, reason="authorise", approval_ref=authorisation,
    )
    return authorisation


def _stored_signatures(run_id: str) -> list[str | None]:
    with psycopg.connect(DATABASE_URL) as conn:
        return [r[0] for r in conn.execute(
            "select decision_signature from audit_log where record_id = %s "
            "and action = 'run.transition' order by id", (run_id,)).fetchall()]


def _forge(run_id: str, actor_id: str, approval_ref: str, signature: str | None) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        record_audit(
            conn, user_id=actor_id, action="run.transition", record_type="runs",
            record_id=run_id, old_value=RunState.DRAFT.value,
            new_value=RunState.RUN_AUTHORISED.value, reason="authorise",
            approval_ref=approval_ref, decision_signature=signature,
        )
        conn.commit()


def test_a_gated_transition_is_signed_and_replays_with_its_signature(
    monkeypatch: pytest.MonkeyPatch, repo: RunRepository, run_id: str, actor_id: str
) -> None:
    monkeypatch.setenv(SIGNING_KEY_ENV, KEY)
    _authorise_through_the_api(repo, run_id, actor_id)
    repo.apply_transition(
        run_id, expected_version=1, new_state=RunState.COVERAGE_LOCKED,
        actor_id=actor_id, reason="lock coverage",
    )

    signatures = _stored_signatures(run_id)
    assert signatures[0] is not None and len(signatures[0]) == 64
    assert signatures[1] is None, "a mechanical transition carries no human decision to sign"

    resumed = AuditRepository(DATABASE_URL).rehydrate(run_id)
    assert resumed.state is RunState.COVERAGE_LOCKED
    assert resumed.history[0].human_decision.signature == signatures[0]


def test_a_row_written_without_the_key_is_refused(
    monkeypatch: pytest.MonkeyPatch, run_id: str, actor_id: str
) -> None:
    """The forged-decision attack: a direct INSERT with a plausible approval and a made-up
    signature, or one signed with a different key."""
    monkeypatch.setenv(SIGNING_KEY_ENV, KEY)
    wrong_key = sign_decision(b"an-attacker-key-that-is-long-enough!!", run_id=run_id,
                              from_state=RunState.DRAFT, to_state=RunState.RUN_AUTHORISED,
                              approver=actor_id, decision="approval-ref", note="authorise")
    _forge(run_id, actor_id, "approval-ref", wrong_key)

    with pytest.raises(CorruptHistory, match="does not verify"):
        AuditRepository(DATABASE_URL).rehydrate(run_id)


def test_a_signature_cannot_be_moved_to_another_run(
    monkeypatch: pytest.MonkeyPatch, repo: RunRepository, run_id: str, actor_id: str
) -> None:
    monkeypatch.setenv(SIGNING_KEY_ENV, KEY)
    authorisation = _authorise_through_the_api(repo, run_id, actor_id)
    genuine = _stored_signatures(run_id)[0]

    other = repo.create_run(
        run_number=f"RUN-SIGN-{uuid.uuid4().hex[:12]}", prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-07-27T07:00:00+12:00",
        coverage_end_utc="2026-07-28T07:00:00+12:00", initiated_by=actor_id,
    ).id
    _forge(other, actor_id, authorisation, genuine)

    with pytest.raises(CorruptHistory, match="does not verify"):
        AuditRepository(DATABASE_URL).rehydrate(other)


def test_signed_rows_cannot_be_replayed_without_the_key(
    monkeypatch: pytest.MonkeyPatch, repo: RunRepository, run_id: str, actor_id: str
) -> None:
    monkeypatch.setenv(SIGNING_KEY_ENV, KEY)
    _authorise_through_the_api(repo, run_id, actor_id)
    monkeypatch.delenv(SIGNING_KEY_ENV)

    with pytest.raises(CorruptHistory, match="cannot be verified"):
        AuditRepository(DATABASE_URL).rehydrate(run_id)


def test_unsigned_legacy_rows_replay_until_signing_is_required(
    monkeypatch: pytest.MonkeyPatch, repo: RunRepository, run_id: str, actor_id: str
) -> None:
    """Rows written before the change have no signature. They keep replaying, so existing runs
    are not stranded, until the deployment turns on `SIP_REQUIRE_SIGNED_DECISIONS`."""
    _authorise_through_the_api(repo, run_id, actor_id)
    assert _stored_signatures(run_id) == [None]
    assert AuditRepository(DATABASE_URL).rehydrate(run_id).state is RunState.RUN_AUTHORISED

    monkeypatch.setenv(REQUIRE_SIGNED_ENV, "true")
    monkeypatch.setenv(SIGNING_KEY_ENV, KEY)
    with pytest.raises(CorruptHistory, match="unsigned"):
        AuditRepository(DATABASE_URL).rehydrate(run_id)


def test_requiring_signatures_without_a_key_refuses_to_record_a_gate(
    monkeypatch: pytest.MonkeyPatch, repo: RunRepository, run_id: str, actor_id: str
) -> None:
    monkeypatch.setenv(REQUIRE_SIGNED_ENV, "true")
    with pytest.raises(SigningKeyError):
        _authorise_through_the_api(repo, run_id, actor_id)
    assert _stored_signatures(run_id) == [], "the refused transition must leave no audit row"
    assert repo.get_run(run_id).state is RunState.DRAFT
