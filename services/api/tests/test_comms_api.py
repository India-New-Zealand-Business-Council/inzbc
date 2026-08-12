"""Unit tests for `/api/comms/draft` (#53): HTTP <-> `generate_draft` mapping, particularly the
three-way failure split (422 blank brief / 503 not configured / 502 provider failure) - the part
most likely to get collapsed into a single 500 by accident. `apps/comms/tests/test_draft.py`
proves the drafting logic itself; this file proves the router calls it correctly.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.api.comms import get_model_gateway
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


@pytest.fixture
def fake_gateway() -> FakeGateway:
    gateway = FakeGateway()
    app.dependency_overrides[get_model_gateway] = lambda: gateway
    yield gateway
    app.dependency_overrides.pop(get_model_gateway, None)


@pytest.fixture
def client(fake_gateway: FakeGateway) -> TestClient:
    return TestClient(app)


def _post(client: TestClient, **overrides) -> object:
    body = {"content_type": "newsletter", "brief": "announce the new FTA explainer"}
    body.update(overrides)
    return client.post("/api/comms/draft", json=body)


def test_draft_returns_the_generated_text(client: TestClient, fake_gateway: FakeGateway) -> None:
    fake_gateway.next_text = "Dear members, we're pleased to announce..."
    response = _post(client)
    assert response.status_code == 200
    assert response.json() == {"draft": "Dear members, we're pleased to announce..."}


def test_draft_rejects_an_unknown_content_type(client: TestClient) -> None:
    response = _post(client, content_type="press_release")
    assert response.status_code == 422


def test_draft_rejects_a_blank_brief(client: TestClient) -> None:
    response = _post(client, brief="   ")
    assert response.status_code == 422


def test_draft_rejects_an_unknown_field(client: TestClient) -> None:
    response = _post(client, extra_field="x")
    assert response.status_code == 422


def test_draft_returns_503_when_gateway_not_configured(
    client: TestClient, fake_gateway: FakeGateway
) -> None:
    fake_gateway.next_error = GatewayNotConfiguredError("no API key")
    response = _post(client)
    assert response.status_code == 503


def test_draft_returns_503_when_redaction_not_configured(
    client: TestClient, fake_gateway: FakeGateway
) -> None:
    # The expected real-deployment state today per ADR-0006 Sec7: no approved
    # REDACTION_POLICY_PATH exists yet, so every live call must refuse exactly this way.
    fake_gateway.next_error = RedactionNotConfiguredError("no policy configured")
    response = _post(client)
    assert response.status_code == 503


def test_draft_returns_502_when_the_provider_call_fails(
    client: TestClient, fake_gateway: FakeGateway
) -> None:
    fake_gateway.next_error = GatewayCallError("provider failed after retries")
    response = _post(client)
    assert response.status_code == 502


def test_draft_response_matches_the_uis_expected_shape(
    client: TestClient, fake_gateway: FakeGateway
) -> None:
    # Mirrors apps/comms/ui/src/api/client.ts's isCommsDraftResult guard: a non-empty string
    # `draft` field and nothing else required.
    response = _post(client)
    body = response.json()
    assert set(body.keys()) == {"draft"}
    assert isinstance(body["draft"], str)
    assert len(body["draft"]) > 0
