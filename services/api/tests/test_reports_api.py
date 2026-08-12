"""Unit tests for the `/api/reports` router (#124): HTTP mapping only.

The database behaviour (version numbering, the trigger that opens the three decision streams) is
proven against a real Postgres in `test_reports_persistence.py`. A fake here would only prove the
fake agrees with itself, the same split `test_runs_api.py` uses.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from services.api.decisions import (
    CurrentDecisions,
    DecisionNotPermittedError,
    ReportVersion,
    ReportVersionConflict,
)
from services.api.main import app
from services.api.reports import get_decision_repository, get_report_repository

VERSION_ID = "00000000-0000-0000-0000-0000000000c1"
RUN_ID = "00000000-0000-0000-0000-0000000000r1".replace("r", "0")
SHA = "a" * 64


def _version() -> ReportVersion:
    return ReportVersion(
        id=VERSION_ID,
        run_id=RUN_ID,
        version_number=2,
        created_by="00000000-0000-0000-0000-0000000000aa",
        content_sha256=SHA,
        created_at="2026-08-13T09:00:00+00:00",
        submitted_at="2026-08-13T09:05:00+00:00",
    )


class FakeReportRepository:
    def __init__(self) -> None:
        self.next_error: Exception | None = None
        self.role_error: Exception | None = None
        self.last_submit: dict | None = None

    def role_id_for(self, actor_id: str, role_names: tuple[str, ...]) -> int:
        if self.role_error is not None:
            raise self.role_error
        return 7

    def submit(self, **kwargs) -> ReportVersion:
        self.last_submit = kwargs
        if self.next_error is not None:
            error, self.next_error = self.next_error, None
            raise error
        return _version()

    def get(self, report_version_id: str) -> ReportVersion:
        if self.next_error is not None:
            error, self.next_error = self.next_error, None
            raise error
        return _version()


class FakeDecisionRepository:
    def __init__(self) -> None:
        self.next_error: Exception | None = None

    def current(self, report_version_id: str) -> CurrentDecisions:
        if self.next_error is not None:
            error, self.next_error = self.next_error, None
            raise error
        return CurrentDecisions(
            report_version_id=report_version_id,
            ceo_ruling=None,
            report_approval="Approved",
            distribution_authority=None,
            distribution_recipient=None,
            revisions={"CEO Ruling": 0, "Report Approval": 1, "Distribution Authority": 0},
        )


@pytest.fixture
def fake_reports() -> FakeReportRepository:
    repo = FakeReportRepository()
    app.dependency_overrides[get_report_repository] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_report_repository, None)


@pytest.fixture
def fake_decisions() -> FakeDecisionRepository:
    repo = FakeDecisionRepository()
    app.dependency_overrides[get_decision_repository] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_decision_repository, None)


@pytest.fixture
def client(fake_reports, fake_decisions) -> TestClient:
    return TestClient(app)


def _submit_body(**overrides) -> dict:
    return {
        "run_id": RUN_ID,
        "content_sha256": SHA,
        "created_at": datetime.now(UTC).isoformat(),
    } | overrides


def test_submitting_returns_the_new_version(client: TestClient) -> None:
    response = client.post("/api/reports", json=_submit_body())

    assert response.status_code == 201
    assert response.json()["version_number"] == 2


def test_the_actor_comes_from_the_session_not_the_body(
    client: TestClient, fake_reports: FakeReportRepository
) -> None:
    """Identity is never caller-supplied. The conformance test proves the field is absent from the
    model; this proves the router puts the session's principal in its place."""
    client.post("/api/reports", json=_submit_body())

    assert fake_reports.last_submit["actor_id"] == "00000000-0000-0000-0000-0000000000aa"


def test_the_version_number_is_not_caller_supplied(client: TestClient) -> None:
    """A caller-supplied number would be a second opinion about the sequence, and the one that
    disagreed would win. `extra="forbid"` refuses it outright rather than ignoring it, because a
    field silently dropped reads to the caller as a field honoured."""
    response = client.post("/api/reports", json=_submit_body(version_number=9))

    assert response.status_code == 422


@pytest.mark.parametrize(
    "sha", ["", "abc", "A" * 64, "g" * 64, "a" * 63],
    ids=["empty", "short", "uppercase", "non-hex", "off-by-one"],
)
def test_a_content_hash_that_is_not_a_sha256_is_refused(client: TestClient, sha: str) -> None:
    """The database has the same CHECK. Refusing here as well turns an opaque constraint violation
    into a 422 naming the field."""
    assert client.post("/api/reports", json=_submit_body(content_sha256=sha)).status_code == 422


def test_a_concurrent_submission_is_409_not_500(
    client: TestClient, fake_reports: FakeReportRepository
) -> None:
    """Two submissions racing for the same version number is a retry, and saying so is the
    difference between a caller that recovers and one that gives up."""
    fake_reports.next_error = ReportVersionConflict("raced")

    assert client.post("/api/reports", json=_submit_body()).status_code == 409


def test_an_actor_holding_no_submitting_role_is_403(
    client: TestClient, fake_reports: FakeReportRepository
) -> None:
    fake_reports.role_error = DecisionNotPermittedError("holds none of Analyst, SIP Owner")

    assert client.post("/api/reports", json=_submit_body()).status_code == 403


def test_reading_returns_the_version_with_its_current_decisions(client: TestClient) -> None:
    body = client.get(f"/api/reports/{VERSION_ID}").json()

    assert body["report"]["version_number"] == 2
    assert body["decisions"]["report_approval"] == "Approved"
    assert body["decisions"]["ceo_ruling"] is None


def test_undecided_is_null_and_the_revisions_come_with_it(client: TestClient) -> None:
    """Null means undecided after submission, which is a different fact from an explicit refusal.
    The revisions are what a later decision passes back, so a decision built on a superseded ruling
    is detectable."""
    decisions = client.get(f"/api/reports/{VERSION_ID}").json()["decisions"]

    assert decisions["distribution_authority"] is None
    assert decisions["revisions"]["Report Approval"] == 1


def test_an_unknown_version_is_404(client: TestClient, fake_reports: FakeReportRepository) -> None:
    fake_reports.next_error = KeyError("no such version")

    assert client.get(f"/api/reports/{uuid.uuid4()}").status_code == 404


def test_the_response_shape_is_closed(client: TestClient) -> None:
    body = client.get(f"/api/reports/{VERSION_ID}").json()

    assert set(body) == {"report", "decisions"}
    assert set(body["decisions"]) == {
        "ceo_ruling", "report_approval", "distribution_authority",
        "distribution_recipient", "revisions",
    }
