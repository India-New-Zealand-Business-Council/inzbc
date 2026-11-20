"""API unit tests for `/api/sector-briefs` (#194)."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from apps.sip.collector.source_register import ALL_SOURCES
from services.api.main import app
from services.api.model_gateway import GatewayNotConfiguredError
from services.api.sector_briefs import get_sector_model_gateway


@dataclass
class _StubCompletion:
    text: str


class _FakeGateway:
    def complete(self, prompt, *, source):
        _ = (prompt, source)
        return _StubCompletion(
            text=json.dumps(
                {
                    "nz_relevance": 4,
                    "india_relevance": 5,
                    "member_relevance": 4,
                    "signal": "High",
                    "confidence": "High",
                    "reason": "Direct corridor opportunity supported by official source.",
                }
            )
        )


class _UnconfiguredGateway:
    def complete(self, prompt, *, source):
        _ = (prompt, source)
        raise GatewayNotConfiguredError("no key")


@pytest.fixture
def client():
    app.dependency_overrides[get_sector_model_gateway] = lambda: _FakeGateway()
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.pop(get_sector_model_gateway, None)


def test_get_corridors_returns_chair_priority_corridors(client: TestClient) -> None:
    response = client.get("/api/sector-briefs/corridors")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 5
    assert any(c["slug"] == "dairy-and-food" for c in body)


def test_generate_sector_brief_returns_advisory_draft(client: TestClient) -> None:
    response = client.post(
        "/api/sector-briefs/generate",
        json={
            "corridor_slug": "dairy-and-food",
            "candidates": [
                {
                    "id": "cand-1",
                    "source_id": ALL_SOURCES[0].source_id,
                    "headline": "India opens dairy cold-chain tender",
                    "published": "2026-11-20T02:00:00Z",
                    "url": "https://example.org/tender",
                }
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["advisory_only"] is True
    assert body["approved"] is False
    assert body["distribution_permitted"] is False
    assert body["included_count"] == 1
    assert body["items"][0]["requires_verification"] is True


def test_generate_sector_brief_rejects_unknown_source_with_422(client: TestClient) -> None:
    response = client.post(
        "/api/sector-briefs/generate",
        json={
            "corridor_slug": "dairy-and-food",
            "candidates": [
                {
                    "id": "cand-1",
                    "source_id": "INVALID-SOURCE",
                    "headline": "Unknown source",
                    "published": "2026-11-20T02:00:00Z",
                    "url": "https://example.org/bad",
                }
            ],
        },
    )
    assert response.status_code == 422


def test_generate_sector_brief_maps_unconfigured_model_to_503() -> None:
    app.dependency_overrides[get_sector_model_gateway] = lambda: _UnconfiguredGateway()
    try:
        with TestClient(app) as tc:
            response = tc.post(
                "/api/sector-briefs/generate",
                json={
                    "corridor_slug": "dairy-and-food",
                    "candidates": [
                        {
                            "id": "cand-1",
                            "source_id": ALL_SOURCES[0].source_id,
                            "headline": "Headline",
                            "published": "2026-11-20T02:00:00Z",
                            "url": "https://example.org/x",
                        }
                    ],
                },
            )
            assert response.status_code == 503
    finally:
        app.dependency_overrides.pop(get_sector_model_gateway, None)
