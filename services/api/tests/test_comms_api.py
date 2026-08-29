"""Unit tests for `/api/comms` (#53, plus the persistence/approval gap #60 and #65 depend on):
HTTP <-> `generate_draft`/`CommsDraftRepository` mapping.

`apps/comms/tests/test_draft.py` proves the drafting logic itself; `test_comms_persistence.py`
proves the repository's self-approval refusal against a real Postgres. This file proves the
router wires both correctly and maps their failures to the right HTTP status.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from services.api.auth import Principal, SelfApprovalError
from services.api.comms import get_comms_draft_repository, get_model_gateway
from services.api.comms_persistence import CommsDraftRecord
from services.api.main import app
from services.api.model_gateway import (
    GatewayCallError,
    GatewayNotConfiguredError,
    GatewayResult,
)
from services.api.prompt_boundary import PromptSource
from services.api.redaction import RedactionNotConfiguredError


class FakeGateway:
    def __init__(self) -> None:
        self.next_error: Exception | None = None
        self.next_text = "a generated draft"
        self.last_source: PromptSource | None = None

    def complete(self, prompt: str, *, source: PromptSource) -> GatewayResult:
        self.last_source = source
        if self.next_error is not None:
            error, self.next_error = self.next_error, None
            raise error
        return GatewayResult(text=self.next_text, model="fake-model", duration_seconds=0.0)


class FakeCommsDraftRepository:
    """In-memory stand-in, same shape as `FakeCandidateRepository` in `test_candidates_api.py`:
    real state for the happy path, a raisable `next_error` for exercising the router's mapping.
    """

    def __init__(self) -> None:
        self._drafts: dict[str, CommsDraftRecord] = {}
        self.next_approve_error: Exception | None = None
        self.last_approve_principal: Principal | None = None

    def create(self, content_type, brief, draft_text, *, authored_by) -> CommsDraftRecord:
        record = CommsDraftRecord(
            id=str(uuid.uuid4()),
            content_type=content_type,
            brief=brief,
            draft_text=draft_text,
            status="Draft",
            authored_by=authored_by,
            approved_by=None,
            approved_at=None,
            approval_reason=None,
            created_at="2026-08-14T00:00:00+00:00",
        )
        self._drafts[record.id] = record
        return record

    def approve(self, draft_id, *, principal, reason=None) -> CommsDraftRecord:
        self.last_approve_principal = principal
        if self.next_approve_error is not None:
            error, self.next_approve_error = self.next_approve_error, None
            raise error
        try:
            current = self._drafts[draft_id]
        except KeyError as error:
            raise KeyError(f"no comms draft {draft_id!r}") from error
        approved = CommsDraftRecord(
            id=current.id,
            content_type=current.content_type,
            brief=current.brief,
            draft_text=current.draft_text,
            status="Approved",
            authored_by=current.authored_by,
            approved_by=principal.user_id,
            approved_at="2026-08-14T01:00:00+00:00",
            approval_reason=reason,
            created_at=current.created_at,
        )
        self._drafts[draft_id] = approved
        return approved

    def get(self, draft_id: str) -> CommsDraftRecord:
        try:
            return self._drafts[draft_id]
        except KeyError as error:
            raise KeyError(f"no comms draft {draft_id!r}") from error

    def delete(self, draft_id: str, *, actor_id: str, reason: str) -> None:
        try:
            del self._drafts[draft_id]
        except KeyError as error:
            raise KeyError(f"no comms draft {draft_id!r}") from error

    def list_all(self) -> list[CommsDraftRecord]:
        return list(self._drafts.values())


@pytest.fixture
def fake_gateway() -> FakeGateway:
    gateway = FakeGateway()
    app.dependency_overrides[get_model_gateway] = lambda: gateway
    yield gateway
    app.dependency_overrides.pop(get_model_gateway, None)


@pytest.fixture
def fake_repo() -> FakeCommsDraftRepository:
    repo = FakeCommsDraftRepository()
    app.dependency_overrides[get_comms_draft_repository] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_comms_draft_repository, None)


@pytest.fixture
def client(fake_gateway: FakeGateway, fake_repo: FakeCommsDraftRepository) -> TestClient:
    return TestClient(app)


def _post_draft(client: TestClient, **overrides) -> object:
    body = {"content_type": "newsletter", "brief": "announce the new FTA explainer"}
    body.update(overrides)
    return client.post("/api/comms/draft", json=body)


def test_draft_returns_the_generated_text(client: TestClient, fake_gateway: FakeGateway) -> None:
    fake_gateway.next_text = "Dear members, we're pleased to announce..."
    response = _post_draft(client)
    assert response.status_code == 200
    assert response.json()["draft"] == "Dear members, we're pleased to announce..."


def test_draft_response_carries_an_id_and_status_additively(client: TestClient) -> None:
    """The UI's isCommsDraftResult guard only checks `draft`, so adding fields is safe - proven
    here by asserting both the old field and the new ones are present, not by asserting the
    envelope is exactly {"draft"} as the pre-persistence version of this test did."""
    response = _post_draft(client)
    body = response.json()
    assert isinstance(body["draft"], str) and len(body["draft"]) > 0
    assert isinstance(body["id"], str) and len(body["id"]) > 0
    assert body["status"] == "Draft"


def test_draft_persists_before_returning(
    client: TestClient, fake_repo: FakeCommsDraftRepository
) -> None:
    response = _post_draft(client)
    draft_id = response.json()["id"]
    assert fake_repo.get(draft_id).status == "Draft"


def test_draft_rejects_an_unknown_content_type(client: TestClient) -> None:
    response = _post_draft(client, content_type="press_release")
    assert response.status_code == 422


def test_draft_rejects_a_blank_brief(client: TestClient) -> None:
    response = _post_draft(client, brief="   ")
    assert response.status_code == 422


def test_draft_rejects_an_unknown_field(client: TestClient) -> None:
    response = _post_draft(client, extra_field="x")
    assert response.status_code == 422


def test_draft_returns_503_when_gateway_not_configured(
    client: TestClient, fake_gateway: FakeGateway
) -> None:
    fake_gateway.next_error = GatewayNotConfiguredError("no API key")
    response = _post_draft(client)
    assert response.status_code == 503


def test_draft_returns_503_when_redaction_not_configured(
    client: TestClient, fake_gateway: FakeGateway
) -> None:
    fake_gateway.next_error = RedactionNotConfiguredError("no policy configured")
    response = _post_draft(client)
    assert response.status_code == 503


def test_draft_returns_502_when_the_provider_call_fails(
    client: TestClient, fake_gateway: FakeGateway
) -> None:
    fake_gateway.next_error = GatewayCallError("provider failed after retries")
    response = _post_draft(client)
    assert response.status_code == 502


def test_a_failed_generation_persists_nothing(
    client: TestClient, fake_gateway: FakeGateway, fake_repo: FakeCommsDraftRepository
) -> None:
    """A draft that failed to generate must not leave a row behind with no text worth reviewing."""
    fake_gateway.next_error = GatewayCallError("provider failed after retries")
    _post_draft(client)
    assert fake_repo.list_all() == []


# ---------------------------------------------------------------------------
# approve
# ---------------------------------------------------------------------------

def test_approve_returns_the_approved_draft(
    client: TestClient, fake_repo: FakeCommsDraftRepository
) -> None:
    draft_id = _post_draft(client).json()["id"]
    response = client.post(f"/api/comms/drafts/{draft_id}/approve", json={"reason": "looks good"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "Approved"
    assert body["approval_reason"] == "looks good"


def test_approve_accepts_no_reason(
    client: TestClient, fake_repo: FakeCommsDraftRepository
) -> None:
    draft_id = _post_draft(client).json()["id"]
    response = client.post(f"/api/comms/drafts/{draft_id}/approve", json={})
    assert response.status_code == 200


def test_approve_a_missing_draft_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/comms/drafts/00000000-0000-0000-0000-000000000000/approve", json={}
    )
    assert response.status_code == 404


def test_self_approval_returns_403(
    client: TestClient, fake_repo: FakeCommsDraftRepository
) -> None:
    """The router's mapping of the repository's refusal - the refusal logic itself is proven
    against a real Postgres in test_comms_persistence.py."""
    draft_id = _post_draft(client).json()["id"]
    fake_repo.next_approve_error = SelfApprovalError("the author cannot also approve this")
    response = client.post(f"/api/comms/drafts/{draft_id}/approve", json={})
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# get / list
# ---------------------------------------------------------------------------

def test_get_draft_returns_it(client: TestClient) -> None:
    draft_id = _post_draft(client).json()["id"]
    response = client.get(f"/api/comms/drafts/{draft_id}")
    assert response.status_code == 200
    assert response.json()["id"] == draft_id


def test_get_a_missing_draft_returns_404(client: TestClient) -> None:
    response = client.get("/api/comms/drafts/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_list_drafts_returns_every_created_draft(client: TestClient) -> None:
    _post_draft(client, content_type="newsletter")
    _post_draft(client, content_type="linkedin_post")
    response = client.get("/api/comms/drafts")
    assert response.status_code == 200
    assert len(response.json()) == 2


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

def test_delete_returns_204(client: TestClient) -> None:
    draft_id = _post_draft(client).json()["id"]
    response = client.request(
        "DELETE", f"/api/comms/drafts/{draft_id}", json={"reason": "contained personal information"}
    )
    assert response.status_code == 204
    assert response.content == b""


def test_deleted_draft_is_gone(client: TestClient, fake_repo: FakeCommsDraftRepository) -> None:
    draft_id = _post_draft(client).json()["id"]
    client.request("DELETE", f"/api/comms/drafts/{draft_id}", json={"reason": "superseded"})

    assert client.get(f"/api/comms/drafts/{draft_id}").status_code == 404
    assert fake_repo.list_all() == []


def test_delete_a_missing_draft_returns_404(client: TestClient) -> None:
    response = client.request(
        "DELETE",
        "/api/comms/drafts/00000000-0000-0000-0000-000000000000",
        json={"reason": "created in error"},
    )
    assert response.status_code == 404


def test_delete_requires_a_reason(client: TestClient) -> None:
    draft_id = _post_draft(client).json()["id"]
    response = client.request("DELETE", f"/api/comms/drafts/{draft_id}", json={"reason": ""})
    assert response.status_code == 422


def test_delete_rejects_a_reason_over_500_characters(client: TestClient) -> None:
    draft_id = _post_draft(client).json()["id"]
    response = client.request(
        "DELETE", f"/api/comms/drafts/{draft_id}", json={"reason": "x" * 501}
    )
    assert response.status_code == 422


def test_delete_rejects_an_unknown_field(client: TestClient) -> None:
    draft_id = _post_draft(client).json()["id"]
    response = client.request(
        "DELETE",
        f"/api/comms/drafts/{draft_id}",
        json={"reason": "superseded", "brief_summary": "leaked name"},
    )
    assert response.status_code == 422
