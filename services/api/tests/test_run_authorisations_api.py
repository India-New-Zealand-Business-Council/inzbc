"""Unit tests for the `/api/runs/{run_id}/authorisations` router (#55): HTTP <-> repository
mapping only, same shape as `test_source_checks_api.py`.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from services.api.auth import Principal
from services.api.decisions import DecisionNotPermittedError
from services.api.main import app
from services.api.run_authorisations import (
    RunAuthorisationRecord,
    get_run_authorisation_repository,
)
from services.api.session import require_csrf, require_principal

RUN_ID = "11111111-1111-1111-1111-111111111111"


class FakeRunAuthorisationRepository:
    def __init__(self) -> None:
        self._by_run: dict[str, list[RunAuthorisationRecord]] = {}
        self._next_id = 0
        self.actor_ids: list[str | None] = []

    def authorise(
        self, run_id, kind, *, actor_id, reason, evidence_ref, decided_at,
    ) -> RunAuthorisationRecord:
        self.actor_ids.append(actor_id)
        self._next_id += 1
        record = RunAuthorisationRecord(
            id=str(self._next_id),
            run_id=run_id,
            kind=kind,
            actor_id=actor_id,
            decided_at=decided_at.isoformat(),
            recorded_at="2026-09-02T00:00:00+00:00",
            reason=reason,
            evidence_ref=evidence_ref,
        )
        self._by_run.setdefault(run_id, []).append(record)
        return record

    def list_for_run(self, run_id: str) -> list[RunAuthorisationRecord]:
        return list(self._by_run.get(run_id, []))


def _client() -> tuple[TestClient, FakeRunAuthorisationRepository]:
    repo = FakeRunAuthorisationRepository()
    app.dependency_overrides[get_run_authorisation_repository] = lambda: repo
    return TestClient(app), repo


def test_authorise_run_returns_the_created_row() -> None:
    client, _repo = _client()
    try:
        response = client.post(
            f"/api/runs/{RUN_ID}/authorisations",
            json={
                "kind": "Launch",
                "reason": "controlled launch",
                "evidence_ref": "SIP-184 launch record",
                "decided_at": "2026-09-01T00:00:00+00:00",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["run_id"] == RUN_ID
        assert body["kind"] == "Launch"
    finally:
        app.dependency_overrides.pop(get_run_authorisation_repository, None)


def test_the_acting_user_comes_from_the_session_not_the_request() -> None:
    """ADR-0004: identity is resolved from the session, never taken from the caller."""
    client, repo = _client()
    try:
        response = client.post(
            f"/api/runs/{RUN_ID}/authorisations",
            json={
                "kind": "Launch",
                "reason": "r",
                "evidence_ref": "e",
                "decided_at": "2026-09-01T00:00:00+00:00",
                # Ignored: AuthoriseRunIn forbids extra fields, so this is refused outright.
                "actor_id": "00000000-0000-0000-0000-0000000000ff",
            },
        )
        assert response.status_code == 422

        assert client.post(
            f"/api/runs/{RUN_ID}/authorisations",
            json={
                "kind": "Launch", "reason": "r", "evidence_ref": "e",
                "decided_at": "2026-09-01T00:00:00+00:00",
            },
        ).status_code == 201
        assert repo.actor_ids == ["00000000-0000-0000-0000-0000000000aa"], (
            "the actor must be the session principal from conftest, not anything the caller sent"
        )
    finally:
        app.dependency_overrides.pop(get_run_authorisation_repository, None)


def test_an_actor_holding_no_sip_owner_role_is_refused() -> None:
    """`write_access(SIP_OWNER)` is the coarse role check; a caller without SIP Owner never
    reaches the repository at all.
    """
    client, repo = _client()
    analyst_only = Principal(
        user_id="00000000-0000-0000-0000-0000000000bb",
        name="Analyst Only",
        roles=frozenset({"Analyst"}),
        session_id="test-session-analyst",
        csrf_token="test-csrf-analyst",
    )
    app.dependency_overrides[require_principal] = lambda: analyst_only
    app.dependency_overrides[require_csrf] = lambda: analyst_only
    try:
        response = client.post(
            f"/api/runs/{RUN_ID}/authorisations",
            json={
                "kind": "Launch", "reason": "r", "evidence_ref": "e",
                "decided_at": "2026-09-01T00:00:00+00:00",
            },
        )
        assert response.status_code == 403
        assert repo.actor_ids == []
    finally:
        app.dependency_overrides.pop(get_run_authorisation_repository, None)
        app.dependency_overrides.pop(require_principal, None)
        app.dependency_overrides.pop(require_csrf, None)


def test_a_future_decided_at_is_refused() -> None:
    client, _repo = _client()
    try:
        response = client.post(
            f"/api/runs/{RUN_ID}/authorisations",
            json={
                "kind": "Launch", "reason": "r", "evidence_ref": "e",
                "decided_at": "2099-01-01T00:00:00+00:00",
            },
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_run_authorisation_repository, None)


def test_repository_refusal_becomes_403_not_500() -> None:
    """`DecisionNotPermittedError` from the repository (e.g. the actor's role was disabled
    between session issue and this request) must surface as 403, not an unhandled 500.
    """

    class RefusingRepository(FakeRunAuthorisationRepository):
        def authorise(self, *args, **kwargs):
            raise DecisionNotPermittedError("role no longer enabled")

    repo = RefusingRepository()
    app.dependency_overrides[get_run_authorisation_repository] = lambda: repo
    try:
        response = TestClient(app).post(
            f"/api/runs/{RUN_ID}/authorisations",
            json={
                "kind": "Launch", "reason": "r", "evidence_ref": "e",
                "decided_at": "2026-09-01T00:00:00+00:00",
            },
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_run_authorisation_repository, None)


def test_list_run_authorisations_returns_only_this_run() -> None:
    client, _repo = _client()
    try:
        client.post(
            f"/api/runs/{RUN_ID}/authorisations",
            json={
                "kind": "Launch", "reason": "r", "evidence_ref": "e",
                "decided_at": "2026-09-01T00:00:00+00:00",
            },
        )
        response = client.get(f"/api/runs/{RUN_ID}/authorisations")
        assert response.status_code == 200
        assert len(response.json()) == 1
    finally:
        app.dependency_overrides.pop(get_run_authorisation_repository, None)
