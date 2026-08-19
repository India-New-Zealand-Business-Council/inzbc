"""Unit tests for the `/api/runs/{run_id}/source-checks` router (#55): HTTP <-> repository
mapping only, same shape as test_runs_api.py's FakeRunRepository.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from apps.sip.pipeline.models import SourceOutcome
from services.api.main import app
from services.api.source_checks import SourceCheckRecord, get_source_check_repository

RUN_ID = "11111111-1111-1111-1111-111111111111"
SOURCE_ID = "22222222-2222-2222-2222-222222222222"


class FakeSourceCheckRepository:
    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], SourceCheckRecord] = {}
        self._next_id = 0
        # What the router passed as the acting user. Kept so a test can assert the identity came
        # from the session rather than from anything the caller sent (ADR-0004).
        self.actor_ids: list[str | None] = []

    def record(
        self, run_id, source_id, outcome, method, fallback_used, access_error, notes,
        actor_id=None,
    ) -> SourceCheckRecord:
        self.actor_ids.append(actor_id)
        key = (run_id, source_id)
        if key not in self._by_key:
            self._next_id += 1
        record = SourceCheckRecord(
            id=str(self._next_id),
            run_id=run_id,
            source_id=source_id,
            outcome=outcome,
            checked_at="2026-08-08T00:00:00+00:00",
            method=method,
            fallback_used=fallback_used,
            access_error=access_error,
            notes=notes,
        )
        self._by_key[key] = record
        return record

    def list_for_run(self, run_id: str) -> list[SourceCheckRecord]:
        return [r for (rid, _), r in self._by_key.items() if rid == run_id]


def _client() -> tuple[TestClient, FakeSourceCheckRepository]:
    repo = FakeSourceCheckRepository()
    app.dependency_overrides[get_source_check_repository] = lambda: repo
    return TestClient(app), repo


def test_record_source_check_returns_the_created_row() -> None:
    client, _repo = _client()
    try:
        response = client.post(
            f"/api/runs/{RUN_ID}/source-checks",
            json={"source_id": SOURCE_ID, "outcome": SourceOutcome.INCLUDED.value},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["run_id"] == RUN_ID
        assert body["source_id"] == SOURCE_ID
        assert body["outcome"] == "Included"
        assert body["fallback_used"] is False
    finally:
        app.dependency_overrides.pop(get_source_check_repository, None)


def test_a_second_check_for_the_same_source_updates_not_duplicates() -> None:
    client, repo = _client()
    try:
        client.post(
            f"/api/runs/{RUN_ID}/source-checks",
            json={"source_id": SOURCE_ID, "outcome": SourceOutcome.INACCESSIBLE.value},
        )
        client.post(
            f"/api/runs/{RUN_ID}/source-checks",
            json={
                "source_id": SOURCE_ID,
                "outcome": SourceOutcome.INCLUDED.value,
                "fallback_used": True,
            },
        )
        rows = repo.list_for_run(RUN_ID)
        assert len(rows) == 1
        assert rows[0].outcome == SourceOutcome.INCLUDED
        assert rows[0].fallback_used is True
    finally:
        app.dependency_overrides.pop(get_source_check_repository, None)


def test_list_source_checks_returns_only_this_run() -> None:
    client, _repo = _client()
    try:
        client.post(
            f"/api/runs/{RUN_ID}/source-checks",
            json={"source_id": SOURCE_ID, "outcome": SourceOutcome.INCLUDED.value},
        )
        response = client.get(f"/api/runs/{RUN_ID}/source-checks")
        assert response.status_code == 200
        assert len(response.json()) == 1
    finally:
        app.dependency_overrides.pop(get_source_check_repository, None)


def test_the_acting_user_comes_from_the_session_not_the_request() -> None:
    """ADR-0004: identity is resolved from the session, never taken from the caller.

    This matters more here than on most writes, because the value ends up in the audit row that
    says who changed a recorded source outcome. A body-supplied actor would let a caller sign
    someone else's name to a correction.
    """
    client, repo = _client()
    try:
        response = client.post(
            f"/api/runs/{RUN_ID}/source-checks",
            json={
                "source_id": SOURCE_ID,
                "outcome": SourceOutcome.INCLUDED.value,
                # Ignored: `RecordSourceCheckIn` forbids extra fields, so this is refused
                # outright rather than silently dropped.
                "actor_id": "00000000-0000-0000-0000-0000000000ff",
            },
        )
        assert response.status_code == 422

        assert client.post(
            f"/api/runs/{RUN_ID}/source-checks",
            json={"source_id": SOURCE_ID, "outcome": SourceOutcome.INCLUDED.value},
        ).status_code == 201
        assert repo.actor_ids == ["00000000-0000-0000-0000-0000000000aa"], (
            "the actor must be the session principal from conftest, not anything the caller sent"
        )
    finally:
        app.dependency_overrides.pop(get_source_check_repository, None)
