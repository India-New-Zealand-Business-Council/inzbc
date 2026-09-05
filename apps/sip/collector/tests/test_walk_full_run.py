"""Tests for the #55 full-walk orchestration script (walk_full_run.py).

The coverage-window helper is pure and tested directly. The walk itself needs a real Postgres
(the mechanical transitions go through `RunRepository.apply_transition`, whose whole point is real
transaction semantics) and the real FastAPI routes for every gate - so the integration test is
skipped unless `DATABASE_URL` is set, the same contract as `services/api/tests/test_persistence.py`.
It drives the routes through a `TestClient` rather than a live server, so it still needs no
uvicorn. The `workflow_dispatch` job (`sip-full-walk.yml`) runs the same path against a real
server.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import psycopg
import pytest

from apps.sip.collector import walk_full_run

DATABASE_URL = os.environ.get("DATABASE_URL")


def test_locked_coverage_window_is_exact_24h_previous_day_0700_to_today_0700() -> None:
    now_utc = datetime(2026, 8, 8, 3, 0, tzinfo=UTC)  # 15:00 NZST, well after 07:00
    start, end = walk_full_run._locked_coverage_window(now_utc)

    start_nz = datetime.fromisoformat(start).astimezone(ZoneInfo("Pacific/Auckland"))
    end_nz = datetime.fromisoformat(end).astimezone(ZoneInfo("Pacific/Auckland"))

    assert start_nz.hour == 7 and start_nz.minute == 0
    assert end_nz.hour == 7 and end_nz.minute == 0
    assert (end_nz - start_nz).total_seconds() == 24 * 3600
    assert end_nz.date() == now_utc.astimezone(ZoneInfo("Pacific/Auckland")).date()


def test_locked_coverage_window_before_0700_nz_uses_previous_boundary() -> None:
    now_utc = datetime(
        2026, 8, 8, 12, 0, tzinfo=UTC
    )  # 00:00 NZST 9 Aug -> before 07:00
    _start, end = walk_full_run._locked_coverage_window(now_utc)
    end_nz = datetime.fromisoformat(end).astimezone(ZoneInfo("Pacific/Auckland"))
    assert end_nz.date() < now_utc.astimezone(ZoneInfo("Pacific/Auckland")).date()


def test_accounts_are_one_distinct_role_per_gate() -> None:
    # The Analyst authors the report; the other three each cross a gate. All distinct, or
    # separation of duties in decisions.py would refuse a decision from the report's author.
    assert set(walk_full_run._ACCOUNTS.values()) == {
        "Analyst",
        "Reviewer",
        "SIP Owner",
        "Secretariat",
    }
    assert len(walk_full_run._ACCOUNTS) == 4


# --- integration: the whole walk against a real database -------------------------------------

pytestmark_db = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - the full walk needs a real Postgres with schema.sql + 0003",
)


def _decision_permissions_seeded() -> bool:
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute("select count(*) from decision_role_permissions").fetchone()
    return bool(row[0])


@pytestmark_db
def test_walk_takes_a_run_to_closed_with_every_gate_recorded() -> None:
    if not _decision_permissions_seeded():
        pytest.skip(
            "decision_role_permissions empty - apply migration 0003 to run this"
        )

    from fastapi.testclient import TestClient

    from services.api.main import app

    # The root conftest's autouse fixture pins every request to one fake principal. This test is
    # specifically about distinct role accounts crossing distinct gates, so it runs against the
    # real session auth instead - each TestClient carries its own minted cookie + CSRF.
    app.dependency_overrides.clear()

    def client_factory(account: walk_full_run.Account) -> TestClient:
        client = TestClient(app)
        client.cookies.set("inzbc_session", account.cookie)
        client.headers["X-CSRF-Token"] = account.csrf
        client.base_url = "http://testserver"  # type: ignore[assignment]
        return client

    evidence = walk_full_run.run_walk(
        base_url="http://testserver",
        database_url=DATABASE_URL,
        client_factory=client_factory,
    )

    # Reached the end of the machine.
    assert evidence["run_row"]["state"] == "Closed"
    assert evidence["run_row"]["production_enabled"] is False
    assert evidence["run_row"]["qa_status"] == "Passed"

    # One decision per ADR-0005 stream, each recorded by a different role.
    kinds = {d["kind"] for d in evidence["decision_records"]}
    assert kinds == {"CEO Ruling", "Report Approval", "Distribution Authority"}
    actor_roles = {d["actor_role_id"] for d in evidence["decision_records"]}
    assert len(actor_roles) == 3

    # Every human-gated transition carries an approval_ref; the mechanical ones do not.
    by_new = {row["new_value"]: row for row in evidence["audit_log"]}
    for gated in (
        "Run Authorised",
        "Awaiting CEO Decision",
        "Approved for Manual Distribution",
        "Distributed",
    ):
        assert by_new[gated]["approval_ref"], f"{gated} has no approval_ref"
    for mechanical in (
        "Coverage Locked",
        "Scanning",
        "Candidate Review",
        "QA In Progress",
    ):
        assert by_new[mechanical]["approval_ref"] is None

    # The two report-level gates point at real decision_records rows.
    decision_ids = {d["id"] for d in evidence["decision_records"]}
    assert by_new["Awaiting CEO Decision"]["approval_ref"] in decision_ids
    assert by_new["Approved for Manual Distribution"]["approval_ref"] in decision_ids
