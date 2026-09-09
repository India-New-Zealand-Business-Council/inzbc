"""Integration tests for `RunAuthorisationRepository` (#55), against a real Postgres. Skipped
without `DATABASE_URL`, same convention as `test_persistence.py`/`test_source_checks.py`.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import psycopg
import pytest

from services.api.decisions import DecisionNotPermittedError
from services.api.run_authorisations import RunAuthorisationRepository
from services.api.tests.role_seed import grant

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - run_authorisations tests need a real Postgres with "
    "schema.sql applied",
)


@pytest.fixture
def repo() -> RunAuthorisationRepository:
    return RunAuthorisationRepository(DATABASE_URL)


@pytest.fixture
def run_id() -> str:
    with psycopg.connect(DATABASE_URL) as conn:
        user_row = conn.execute(
            "insert into users (name, email) values (%s, %s) returning id",
            (f"Initiator {uuid.uuid4()}", f"{uuid.uuid4()}@example.test"),
        ).fetchone()
        run_row = conn.execute(
            "insert into runs (run_number, prompt_version, coverage_start_utc, "
            "coverage_end_utc, initiated_by) values (%s, %s, now() - interval '1 day', now(), "
            "%s) returning id",
            (f"RUN-AUTH-{uuid.uuid4().hex[:10]}", "SIP-050 v1.1", user_row[0]),
        ).fetchone()
        conn.commit()
    return str(run_row[0])


@pytest.fixture
def sip_owner() -> str:
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "insert into users (name, email) values (%s, %s) returning id",
            (f"Owner {uuid.uuid4()}", f"{uuid.uuid4()}@example.test"),
        ).fetchone()
        grant(conn, row[0], "SIP Owner")
        conn.commit()
    return str(row[0])


def test_authorise_records_a_launch_and_resolves_the_actor_role(
    repo: RunAuthorisationRepository, run_id: str, sip_owner: str
) -> None:
    record = repo.authorise(
        run_id, "Launch",
        actor_id=sip_owner, reason="controlled launch", evidence_ref="SIP-184 launch record",
        decided_at=datetime.now(UTC),
    )

    assert record.run_id == run_id
    assert record.kind == "Launch"
    assert record.actor_id == sip_owner


def test_authorise_refuses_an_actor_with_no_sip_owner_role(
    repo: RunAuthorisationRepository, run_id: str
) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "insert into users (name, email) values (%s, %s) returning id",
            (f"Analyst {uuid.uuid4()}", f"{uuid.uuid4()}@example.test"),
        ).fetchone()
        grant(conn, row[0], "Analyst")
        conn.commit()
    non_owner = str(row[0])

    with pytest.raises(DecisionNotPermittedError):
        repo.authorise(
            run_id, "Launch",
            actor_id=non_owner, reason="attempted launch", evidence_ref="ref",
            decided_at=datetime.now(UTC),
        )


def test_authorise_refuses_a_kind_outside_the_enum(
    repo: RunAuthorisationRepository, run_id: str, sip_owner: str
) -> None:
    with pytest.raises(psycopg.errors.InvalidTextRepresentation):
        repo.authorise(
            run_id, "Bogus",
            actor_id=sip_owner, reason="r", evidence_ref="e", decided_at=datetime.now(UTC),
        )


def test_list_for_run_returns_only_this_runs_authorisations(
    repo: RunAuthorisationRepository, run_id: str, sip_owner: str
) -> None:
    repo.authorise(
        run_id, "Launch",
        actor_id=sip_owner, reason="launch", evidence_ref="ref", decided_at=datetime.now(UTC),
    )

    with psycopg.connect(DATABASE_URL) as conn:
        other_run = conn.execute(
            "insert into runs (run_number, prompt_version, coverage_start_utc, "
            "coverage_end_utc, initiated_by) values (%s, %s, now() - interval '1 day', now(), "
            "%s) returning id",
            (f"RUN-OTHER-{uuid.uuid4().hex[:10]}", "SIP-050 v1.1", sip_owner),
        ).fetchone()
        conn.commit()
    repo.authorise(
        str(other_run[0]), "Launch",
        actor_id=sip_owner, reason="launch", evidence_ref="ref", decided_at=datetime.now(UTC),
    )

    rows = repo.list_for_run(run_id)
    assert len(rows) == 1
    assert rows[0].run_id == run_id
