"""Unit tests for `/api/facts` (#188): HTTP <-> repository mapping, with a fake repository.
Live-Postgres behaviour (self-approval refusal, version chaining) is proven in
test_facts_persistence.py; this file proves the router calls the repository correctly and maps
errors to the right status codes.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from services.api.facts import get_fact_repository
from services.api.facts_persistence import FactRecord, SelfApprovalError
from services.api.main import app

_TEST_PRINCIPAL_ID = "00000000-0000-0000-0000-0000000000aa"


class FakeFactRepository:
    def __init__(self) -> None:
        self._items: dict[str, FactRecord] = {}

    def draft(self, fact_key, content, source, *, actor_id, **kwargs):
        supersedes_id = kwargs.get("supersedes_id")
        version = 1
        if supersedes_id is not None:
            if supersedes_id not in self._items:
                raise KeyError(supersedes_id)
            version = self._items[supersedes_id].version + 1
        record = FactRecord(
            id=str(uuid.uuid4()),
            fact_key=fact_key,
            content=content,
            owner_id=kwargs.get("owner_id"),
            owner_text=kwargs.get("owner_text"),
            status="draft",
            source=source,
            verified_at=kwargs.get("verified_at"),
            review_due_at=kwargs.get("review_due_at"),
            version=version,
            supersedes_id=supersedes_id,
            created_by=actor_id,
            created_at="2026-08-18T00:00:00+00:00",
            approved_by=None,
            approved_at=None,
            archived_at=None,
        )
        self._items[record.id] = record
        return record

    def approve(self, fact_id, *, actor_id):
        current = self._items[fact_id]
        if current.created_by == actor_id:
            raise SelfApprovalError(
                f"actor {actor_id!r} cannot approve their own draft"
            )
        if current.status != "draft":
            raise ValueError(f"fact {fact_id!r} is {current.status!r}")
        updated = FactRecord(
            **{
                **current.__dict__,
                "status": "approved",
                "approved_by": actor_id,
                "approved_at": "2026-08-18T01:00:00+00:00",
            }
        )
        self._items[fact_id] = updated
        return updated

    def archive(self, fact_id, *, actor_id):
        current = self._items[fact_id]
        updated = FactRecord(
            **{
                **current.__dict__,
                "status": "archived",
                "archived_at": "2026-08-18T02:00:00+00:00",
            }
        )
        self._items[fact_id] = updated
        return updated

    def get(self, fact_id):
        return self._items[fact_id]

    def get_latest_approved(self, fact_key):
        approved = [
            f
            for f in self._items.values()
            if f.fact_key == fact_key and f.status == "approved"
        ]
        return max(approved, key=lambda f: f.version) if approved else None

    def history(self, fact_key):
        items = [f for f in self._items.values() if f.fact_key == fact_key]
        return sorted(items, key=lambda f: f.version, reverse=True)


@pytest.fixture
def facts_repo():
    repo = FakeFactRepository()
    app.dependency_overrides[get_fact_repository] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_fact_repository, None)


@pytest.fixture
def client():
    return TestClient(app)


def test_draft_fact_returns_201(client, facts_repo):
    response = client.post(
        "/api/facts",
        json={
            "fact_key": "FTA-TARIFF-WOOL",
            "content": "0% tariff",
            "source": "MFAT",
            "owner_text": "Trade desk",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["version"] == 1


def test_draft_rejects_unknown_field(client, facts_repo):
    response = client.post(
        "/api/facts",
        json={
            "fact_key": "K",
            "content": "c",
            "source": "s",
            "owner_text": "o",
            "surprise": "x",
        },
    )
    assert response.status_code == 422


def test_approve_by_same_principal_is_403(client, facts_repo):
    """The fixture principal drafts and would also be the one approving - refused."""
    fact_id = client.post(
        "/api/facts",
        json={"fact_key": "K", "content": "c", "source": "s", "owner_text": "o"},
    ).json()["id"]
    response = client.post(f"/api/facts/{fact_id}/approve")
    assert response.status_code == 403


def test_approve_non_draft_is_409(client, facts_repo):
    fact_id = client.post(
        "/api/facts",
        json={"fact_key": "K", "content": "c", "source": "s", "owner_text": "o"},
    ).json()["id"]
    facts_repo._items[fact_id] = FactRecord(
        **{
            **facts_repo._items[fact_id].__dict__,
            "created_by": "someone-else",
            "status": "draft",
        }
    )
    client.post(f"/api/facts/{fact_id}/approve")
    response = client.post(f"/api/facts/{fact_id}/approve")
    assert response.status_code == 409


def test_approve_missing_fact_is_404(client, facts_repo):
    response = client.post("/api/facts/00000000-0000-0000-0000-000000000000/approve")
    assert response.status_code == 404


def test_archive_sets_status(client, facts_repo):
    fact_id = client.post(
        "/api/facts",
        json={"fact_key": "K", "content": "c", "source": "s", "owner_text": "o"},
    ).json()["id"]
    response = client.post(f"/api/facts/{fact_id}/archive")
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def test_get_missing_fact_is_404(client, facts_repo):
    response = client.get("/api/facts/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_get_latest_approved_missing_is_404(client, facts_repo):
    response = client.get("/api/facts/by-key/NO-SUCH-KEY/latest")
    assert response.status_code == 404


def test_get_latest_approved_returns_approved_version(client, facts_repo):
    fact_id = client.post(
        "/api/facts",
        json={"fact_key": "K2", "content": "c", "source": "s", "owner_text": "o"},
    ).json()["id"]
    facts_repo._items[fact_id] = FactRecord(
        **{**facts_repo._items[fact_id].__dict__, "created_by": "someone-else"}
    )
    client.post(f"/api/facts/{fact_id}/approve")
    response = client.get("/api/facts/by-key/K2/latest")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_get_history_returns_all_revisions(client, facts_repo):
    client.post(
        "/api/facts",
        json={"fact_key": "K3", "content": "v1", "source": "s", "owner_text": "o"},
    )
    response = client.get("/api/facts/by-key/K3/history")
    assert response.status_code == 200
    assert len(response.json()) == 1
