"""Unit tests for the `/api/candidates` router (#121): HTTP <-> `CandidateRepository` mapping,
plus the verification-gate exception -> 403 translation. `CandidateRepository`'s own gate/audit
behaviour is proven against a real Postgres in `test_candidate_persistence.py`; this file proves
the router calls it correctly, same split as `test_runs_api.py`/`test_persistence.py`.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from apps.sip.collector.verification import UnverifiedHighSignalError
from apps.sip.pipeline.models import VerificationState
from services.api.candidate_persistence import CandidateRecord
from services.api.candidates import get_candidate_repository
from services.api.main import app


class FakeCandidateRepository:
    """In-memory stand-in, same shape as `FakeRunRepository` in `test_runs_api.py`: real state
    for the happy path, a one-shot `next_error` for exercising the router's exception mapping.
    """

    def __init__(self) -> None:
        self._candidates: dict[str, CandidateRecord] = {}
        self.next_error: Exception | None = None

    def capture(self, **kwargs) -> CandidateRecord:
        candidate = CandidateRecord(
            id=str(uuid.uuid4()),
            run_id=kwargs["run_id"],
            headline=kwargs["headline"],
            source_id=kwargs.get("source_id"),
            url=kwargs.get("url"),
            summary=kwargs.get("summary"),
            published_at=kwargs.get("published_at"),
            captured_at="2026-08-05T00:00:00+00:00",
            in_coverage_window=kwargs.get("in_coverage_window"),
            nz_relevance=None,
            india_relevance=None,
            member_relevance=None,
            signal=None,
            confidence=None,
            verification=VerificationState.UNVERIFIED,
            duplicate_of=None,
            included=None,
            reason=None,
            proposed_routing=None,
        )
        self._candidates[candidate.id] = candidate
        return candidate

    def get(self, candidate_id: str) -> CandidateRecord:
        try:
            return self._candidates[candidate_id]
        except KeyError as error:
            raise KeyError(f"no candidate {candidate_id!r}") from error

    def list_for_run(self, run_id: str) -> list[CandidateRecord]:
        return [c for c in self._candidates.values() if c.run_id == run_id]

    def _consume_error(self) -> None:
        if self.next_error is not None:
            error, self.next_error = self.next_error, None
            raise error

    def record_verification(self, candidate_id: str, verification, **kwargs) -> CandidateRecord:
        self._consume_error()
        current = self._candidates[candidate_id]
        from dataclasses import replace

        updated = replace(current, verification=verification)
        self._candidates[candidate_id] = updated
        return updated

    def record_score(self, candidate_id: str, **kwargs) -> CandidateRecord:
        self._consume_error()
        from dataclasses import replace

        current = self._candidates[candidate_id]
        updated = replace(
            current,
            nz_relevance=kwargs.get("nz_relevance"),
            india_relevance=kwargs.get("india_relevance"),
            member_relevance=kwargs.get("member_relevance"),
            signal=kwargs.get("signal"),
            confidence=kwargs.get("confidence"),
        )
        self._candidates[candidate_id] = updated
        return updated

    def record_routing(self, candidate_id: str, **kwargs) -> CandidateRecord:
        self._consume_error()
        from dataclasses import replace

        current = self._candidates[candidate_id]
        updated = replace(
            current,
            proposed_routing=kwargs.get("proposed_routing"),
            included=kwargs.get("included"),
        )
        self._candidates[candidate_id] = updated
        return updated

    def merge(self, candidate_id: str, duplicate_of: str, **kwargs) -> CandidateRecord:
        self._consume_error()
        from dataclasses import replace

        current = self._candidates[candidate_id]
        updated = replace(current, duplicate_of=duplicate_of, included=False)
        self._candidates[candidate_id] = updated
        return updated


@pytest.fixture
def fake_repo() -> FakeCandidateRepository:
    repo = FakeCandidateRepository()
    app.dependency_overrides[get_candidate_repository] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_candidate_repository, None)


@pytest.fixture
def client(fake_repo: FakeCandidateRepository) -> TestClient:
    return TestClient(app)


def _capture(client: TestClient, run_id: str | None = None) -> dict:
    response = client.post(
        "/api/candidates",
        json={
            "run_id": run_id or str(uuid.uuid4()),
            "headline": "Test headline",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_capture_returns_unverified_candidate(client: TestClient) -> None:
    body = _capture(client)
    assert body["verification"] == "Unverified"
    assert body["headline"] == "Test headline"


def test_get_candidate_returns_404_for_unknown_id(client: TestClient) -> None:
    response = client.get(f"/api/candidates/{uuid.uuid4()}")
    assert response.status_code == 404


def test_list_candidates_filters_by_run(client: TestClient) -> None:
    run_id = str(uuid.uuid4())
    created = _capture(client, run_id=run_id)
    _capture(client)  # a different run - must not show up

    response = client.get("/api/candidates", params={"run": run_id})

    assert response.status_code == 200
    ids = {c["id"] for c in response.json()}
    assert ids == {created["id"]}


def test_verify_sets_verification_state(client: TestClient) -> None:
    created = _capture(client)
    response = client.post(
        f"/api/candidates/{created['id']}/verify",
        json={"verification": "Verified", "reason": "checked source"},
    )
    assert response.status_code == 200
    assert response.json()["verification"] == "Verified"


def test_verify_gate_failure_returns_403(
    client: TestClient, fake_repo: FakeCandidateRepository
) -> None:
    created = _capture(client)
    fake_repo.next_error = UnverifiedHighSignalError("Critical signal requires verified source")
    response = client.post(
        f"/api/candidates/{created['id']}/verify",
        json={"verification": "Unverified", "reason": "n/a"},
    )
    assert response.status_code == 403


def test_score_gate_failure_returns_403(
    client: TestClient, fake_repo: FakeCandidateRepository
) -> None:
    created = _capture(client)
    fake_repo.next_error = UnverifiedHighSignalError("Critical signal requires verified source")
    response = client.post(
        f"/api/candidates/{created['id']}/score",
        json={"signal": "Critical", "reason": "n/a"},
    )
    assert response.status_code == 403


def test_route_sets_proposed_routing(client: TestClient) -> None:
    created = _capture(client)
    response = client.post(
        f"/api/candidates/{created['id']}/route",
        json={
            "proposed_routing": "Daily Intelligence",
            "included": True,
            "reason": "relevant to member sector",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["proposed_routing"] == "Daily Intelligence"
    assert body["included"] is True


def test_merge_sets_duplicate_of_and_excludes(client: TestClient) -> None:
    run_id = str(uuid.uuid4())
    original = _capture(client, run_id=run_id)
    duplicate = _capture(client, run_id=run_id)

    response = client.post(
        f"/api/candidates/{duplicate['id']}/merge",
        json={
            "duplicate_of": original["id"],
            "reason": "same story, later capture",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["duplicate_of"] == original["id"]
    assert body["included"] is False


def test_capture_rejects_an_unknown_field(client: TestClient) -> None:
    response = client.post(
        "/api/candidates",
        json={
            "run_id": str(uuid.uuid4()),
            "headline": "x",
            "not_a_real_field": "x",
        },
    )
    assert response.status_code == 422
