"""Unit tests for the `/api/runs` router (#120): HTTP <-> `RunRepository` mapping only.

`RunRepository`'s actual concurrency/legality/gate guarantees are proven against a real Postgres
in `test_persistence.py` (skipped without `DATABASE_URL`); duplicating that here with a fake would
only prove the fake agrees with itself. This file instead proves the router calls the repository
correctly and translates each of its documented exceptions to the right status code - a `FakeRun
Repository` that can be told to raise a specific error on the next call is enough for that, and
does not need to reimplement the state machine to do it.
"""

from __future__ import annotations

import uuid
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from apps.sip.core.orchestrator import IllegalTransition
from apps.sip.pipeline.models import RunState
from services.api.main import app
from services.api.persistence import (
    ConcurrentModificationError,
    HumanGateNotSatisfied,
    RunRecord,
)
from services.api.runs import get_run_repository


class FakeRunRepository:
    """In-memory stand-in. `apply_transition` raises `next_error` once (then clears it) rather
    than re-deriving legality/gating/version rules - those belong to `RunRepository` and are
    proven there; this fake exists only to drive the router's exception -> status mapping
    deterministically.
    """

    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self.next_error: Exception | None = None
        # What the router last handed down. Without this the fake swallows its arguments, so a
        # router that dropped or hardcoded one would still pass every test here.
        self.last_transition: dict | None = None

    def create_run(
        self,
        *,
        run_number: str,
        prompt_version: str,
        coverage_start_utc: str,
        coverage_end_utc: str,
        initiated_by: str,
    ) -> RunRecord:
        run = RunRecord(
            id=str(uuid.uuid4()),
            run_number=run_number,
            state=RunState.DRAFT,
            version=0,
            prompt_version=prompt_version,
            coverage_start_utc=coverage_start_utc,
            coverage_end_utc=coverage_end_utc,
            initiated_by=initiated_by,
        )
        self._runs[run.id] = run
        return run

    def get_run(self, run_id: str) -> RunRecord:
        try:
            return self._runs[run_id]
        except KeyError as error:
            raise KeyError(f"no run {run_id!r}") from error

    def list_runs(self) -> list[RunRecord]:
        return list(self._runs.values())

    def apply_transition(
        self,
        run_id: str,
        *,
        expected_version: int,
        new_state: RunState,
        actor_id: str,
        reason: str,
        approval_ref: str | None = None,
    ) -> RunRecord:
        self.last_transition = {
            "run_id": run_id,
            "expected_version": expected_version,
            "new_state": new_state,
            "actor_id": actor_id,
            "reason": reason,
            "approval_ref": approval_ref,
        }
        if self.next_error is not None:
            error, self.next_error = self.next_error, None
            raise error
        current = self._runs[run_id]
        updated = replace(current, state=new_state, version=current.version + 1)
        self._runs[run_id] = updated
        return updated


@pytest.fixture
def fake_repo() -> FakeRunRepository:
    repo = FakeRunRepository()
    app.dependency_overrides[get_run_repository] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_run_repository, None)


@pytest.fixture
def client(fake_repo: FakeRunRepository) -> TestClient:
    return TestClient(app)


def _create(client: TestClient) -> dict:
    response = client.post(
        "/api/runs",
        json={
            "run_number": f"RUN-TEST-{uuid.uuid4().hex[:8]}",
            "prompt_version": "SIP-050 v1.1",
            "coverage_start_utc": "2026-07-27T07:00:00+12:00",
            "coverage_end_utc": "2026-07-28T07:00:00+12:00",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_run_returns_draft_at_version_zero(client: TestClient) -> None:
    body = _create(client)
    assert body["state"] == "Draft"
    assert body["version"] == 0


def test_get_run_reads_back_what_was_created(client: TestClient) -> None:
    created = _create(client)
    response = client.get(f"/api/runs/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_run_returns_404_for_an_unknown_id(client: TestClient) -> None:
    response = client.get(f"/api/runs/{uuid.uuid4()}")
    assert response.status_code == 404


def test_list_runs_includes_a_created_run(client: TestClient) -> None:
    created = _create(client)
    response = client.get("/api/runs")
    assert response.status_code == 200
    assert created["id"] in {run["id"] for run in response.json()}


@pytest.mark.parametrize(
    ("route", "expected_state"),
    [
        ("start", "Run Authorised"),
        ("pause", "Paused"),
        ("resume", "Coverage Locked"),
        ("complete", "Closed"),
    ],
)
def test_each_lifecycle_route_maps_to_its_own_target_state(
    client: TestClient, route: str, expected_state: str
) -> None:
    """Each of the four routes must call `_apply` with its own `RunState`, not share one by
    accident. `FakeRunRepository` doesn't check legality (that's `RunRepository`'s job, proven in
    `test_persistence.py`), so this isolates exactly the router's route -> state wiring: a
    swapped constant (e.g. `pause` accidentally passing `RunState.CLOSED`) would still return 200
    here and only this assertion would catch it - previously only `start` had one.
    """
    created = _create(client)
    response = client.post(
        f"/api/runs/{created['id']}/{route}",
        json={
            "expected_version": 0,
            "reason": f"{route} run",
            "approval_ref": "recorded-authority",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == expected_state
    assert body["version"] == 1


@pytest.mark.parametrize("route", ["start", "pause", "resume", "complete"])
def test_unknown_run_returns_404_on_every_lifecycle_route(
    client: TestClient, route: str
) -> None:
    response = client.post(
        f"/api/runs/{uuid.uuid4()}/{route}",
        json={"expected_version": 0, "reason": "n/a"},
    )
    assert response.status_code == 404


def test_stale_version_returns_409(
    client: TestClient, fake_repo: FakeRunRepository
) -> None:
    created = _create(client)
    fake_repo.next_error = ConcurrentModificationError("stale")
    response = client.post(
        f"/api/runs/{created['id']}/start",
        json={"expected_version": 0, "reason": "authorise run"},
    )
    assert response.status_code == 409


def test_illegal_transition_returns_400(
    client: TestClient, fake_repo: FakeRunRepository
) -> None:
    created = _create(client)
    fake_repo.next_error = IllegalTransition("not reachable")
    response = client.post(
        f"/api/runs/{created['id']}/complete",
        json={"expected_version": 0, "reason": "close run"},
    )
    assert response.status_code == 400


def test_missing_human_gate_authority_returns_403(
    client: TestClient, fake_repo: FakeRunRepository
) -> None:
    created = _create(client)
    fake_repo.next_error = HumanGateNotSatisfied("needs approval_ref")
    response = client.post(
        f"/api/runs/{created['id']}/start",
        json={"expected_version": 0, "reason": "authorise run"},
    )
    assert response.status_code == 403


def test_create_run_rejects_an_unknown_field() -> None:
    # extra="forbid" on CreateRunIn: a typo'd field must be refused, not silently dropped.
    app.dependency_overrides[get_run_repository] = lambda: FakeRunRepository()
    try:
        client = TestClient(app)
        response = client.post(
            "/api/runs",
            json={
                "run_number": "RUN-X",
                "prompt_version": "SIP-050 v1.1",
                "coverage_start_utc": "2026-07-27T07:00:00+12:00",
                "coverage_end_utc": "2026-07-28T07:00:00+12:00",
                "not_a_real_field": "x",
            },
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_run_repository, None)


def test_the_caller_s_authority_reaches_the_repository(
    client: TestClient, fake_repo: FakeRunRepository
) -> None:
    """The router must hand down the authenticated identity, not something of its own.

    The 403 test above proves the error mapping by injecting the exception, so it never exercises
    the argument. Replacing `approval_ref=body.approval_ref` with a hardcoded string passed every
    test in this file: every gated transition would have been authorised by a value the caller
    never supplied, and for a run-level gate nothing downstream re-checks it, because those two
    cannot be verified against `decision_records` (#227).
    """
    created = _create(client)

    client.post(
        f"/api/runs/{created['id']}/start",
        json={
            "expected_version": 0,
            "reason": "authorise run",
            "approval_ref": "launch-authority-2026-08-05",
        },
    )

    handed_down = fake_repo.last_transition
    assert handed_down is not None
    assert handed_down["approval_ref"] == "launch-authority-2026-08-05"
    assert handed_down["reason"] == "authorise run"
    # The actor is the authenticated session's, not anything the request body could set. The
    # body no longer has an actor_id field at all, so an impersonation attempt is a 422 rather
    # than a silently accepted identity.
    assert handed_down["actor_id"] == "00000000-0000-0000-0000-0000000000aa"
