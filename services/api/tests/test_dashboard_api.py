"""Unit tests for the `/api/dashboard` router (#47): HTTP mapping only.

The SQL aggregation is proven against a real Postgres in `test_dashboard_persistence.py`. A fake
here would only prove the fake agrees with itself, which is the same reason `test_runs_api.py`
splits the same way.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.sip.pipeline.models import RunState
from services.api.dashboard import get_dashboard_repository
from services.api.main import app
from services.api.persistence import (
    VERIFICATION_STATES,
    DashboardSummary,
    OpenAction,
    RunRecord,
)


def _run() -> RunRecord:
    return RunRecord(
        id="00000000-0000-0000-0000-0000000000ff",
        run_number="RUN-20260813-01",
        state=RunState.CANDIDATE_REVIEW,
        version=3,
        prompt_version="SIP-050 v1.1",
        coverage_start_utc="2026-08-12T07:00:00+12:00",
        coverage_end_utc="2026-08-13T07:00:00+12:00",
        initiated_by="00000000-0000-0000-0000-0000000000aa",
    )


class FakeDashboardRepository:
    def __init__(self) -> None:
        self.next_summary = DashboardSummary(
            run=_run(),
            total_candidates=7,
            included_candidates=2,
            by_verification={state: 0 for state in VERIFICATION_STATES} | {"Verified": 5},
            open_actions=[],
        )

    def summary(self) -> DashboardSummary:
        return self.next_summary


@pytest.fixture
def fake_repo() -> FakeDashboardRepository:
    repo = FakeDashboardRepository()
    app.dependency_overrides[get_dashboard_repository] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_dashboard_repository, None)


@pytest.fixture
def client(fake_repo: FakeDashboardRepository) -> TestClient:
    return TestClient(app)


def test_it_returns_the_run_and_its_coverage(client: TestClient) -> None:
    body = client.get("/api/dashboard").json()

    assert body["run"]["run_number"] == "RUN-20260813-01"
    assert body["run"]["state"] == "Candidate Review"
    assert body["coverage"]["total"] == 7
    assert body["coverage"]["included"] == 2
    assert body["coverage"]["by_verification"]["Verified"] == 5


def test_every_verification_state_is_present_even_at_zero(client: TestClient) -> None:
    """The point of the endpoint. A state absent from the map would force the UI to know the full
    enum to render the panel, which is the coupling this replaces."""
    by_verification = client.get("/api/dashboard").json()["coverage"]["by_verification"]

    assert set(by_verification) == set(VERIFICATION_STATES)
    assert by_verification["Rejected"] == 0


def test_no_run_is_200_with_a_null_run_not_404(
    client: TestClient, fake_repo: FakeDashboardRepository
) -> None:
    """"No run yet" is a state the dashboard renders. A 404 would make an empty system
    indistinguishable from a broken one, and the open-actions panel is still worth showing."""
    fake_repo.next_summary = DashboardSummary(
        run=None,
        total_candidates=0,
        included_candidates=0,
        by_verification={state: 0 for state in VERIFICATION_STATES},
        open_actions=[
            OpenAction(
                action_code="ACT-016",
                title="Confirm MFA on the registrar account",
                owner="Executive Sponsor",
                priority="High",
                due_date="2026-08-01",
                status="Open",
                overdue=True,
            )
        ],
    )

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["run"] is None
    assert body["open_actions"][0]["action_code"] == "ACT-016"
    assert body["open_actions"][0]["overdue"] is True


def test_the_response_shape_is_closed(client: TestClient) -> None:
    """`extra="forbid"` on every model, so a field added server-side cannot reach the UI
    unannounced and a typo in one cannot pass silently."""
    body = client.get("/api/dashboard").json()

    assert set(body) == {"run", "coverage", "open_actions"}
    assert set(body["coverage"]) == {"total", "included", "by_verification"}
