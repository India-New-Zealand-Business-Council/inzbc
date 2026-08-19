"""Unit tests for `/api/action-register`, `/api/watch-lists`, `/api/exceptions` (#209): HTTP <->
repository mapping, with a fake repository per entity. Live-Postgres behaviour (append-only,
status-transition correctness) is proven in test_registers_persistence.py; this file proves the
router calls the repository correctly and maps 404s.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from services.api.main import app
from services.api.registers import (
    get_action_register_repository,
    get_exception_repository,
    get_watch_list_repository,
)
from services.api.registers_persistence import (
    ActionRegisterRecord,
    ExceptionRecord,
    WatchListRecord,
)


class FakeActionRegisterRepository:
    def __init__(self) -> None:
        self._items: dict[str, ActionRegisterRecord] = {}

    def create(self, action_code, title, status, *, actor_id, **kwargs) -> ActionRegisterRecord:
        record = ActionRegisterRecord(
            id=str(uuid.uuid4()),
            action_code=action_code,
            title=title,
            description=kwargs.get("description"),
            owner_id=kwargs.get("owner_id"),
            owner_text=kwargs.get("owner_text"),
            priority=kwargs.get("priority"),
            due_date=kwargs.get("due_date"),
            review_date=kwargs.get("review_date"),
            status=status,
            evidence_ref=kwargs.get("evidence_ref"),
            closed_at=None,
            created_at="2026-08-14T00:00:00+00:00",
        )
        self._items[record.id] = record
        return record

    def update_status(self, action_id, status, *, actor_id, evidence_ref=None):
        current = self._items[action_id]
        updated = ActionRegisterRecord(
            id=current.id, action_code=current.action_code, title=current.title,
            description=current.description, owner_id=current.owner_id,
            owner_text=current.owner_text, priority=current.priority,
            due_date=current.due_date, review_date=current.review_date, status=status,
            evidence_ref=evidence_ref or current.evidence_ref,
            closed_at="2026-08-14T01:00:00+00:00" if status == "Closed" else None,
            created_at=current.created_at,
        )
        self._items[action_id] = updated
        return updated

    def get(self, action_id):
        return self._items[action_id]

    def list_all(self):
        return list(self._items.values())


class FakeWatchListRepository:
    def __init__(self) -> None:
        self._items: dict[str, WatchListRecord] = {}

    def create(self, watch_code, title, status, *, actor_id, **kwargs) -> WatchListRecord:
        record = WatchListRecord(
            id=str(uuid.uuid4()), watch_code=watch_code, title=title,
            category=kwargs.get("category"), frequency=kwargs.get("frequency"),
            escalation=kwargs.get("escalation"), status=status,
            next_review=kwargs.get("next_review"),
        )
        self._items[record.id] = record
        return record

    def update_status(self, watch_id, status, *, actor_id, next_review=None):
        current = self._items[watch_id]
        updated = WatchListRecord(
            id=current.id, watch_code=current.watch_code, title=current.title,
            category=current.category, frequency=current.frequency,
            escalation=current.escalation, status=status,
            next_review=next_review or current.next_review,
        )
        self._items[watch_id] = updated
        return updated

    def get(self, watch_id):
        return self._items[watch_id]

    def list_all(self):
        return list(self._items.values())


class FakeExceptionRepository:
    def __init__(self) -> None:
        self._items: dict[str, ExceptionRecord] = {}

    def record(self, exception_type, severity, status, *, actor_id, **kwargs) -> ExceptionRecord:
        record = ExceptionRecord(
            id=str(uuid.uuid4()), run_id=kwargs.get("run_id"), exception_type=exception_type,
            severity=severity, owner_id=kwargs.get("owner_id"), status=status,
            original_preserved=kwargs.get("original_preserved", True), correction_ref=None,
            created_at="2026-08-14T00:00:00+00:00",
        )
        self._items[record.id] = record
        return record

    def correct(self, original_id, exception_type, severity, status, *, actor_id, reason):
        original = self._items[original_id]
        record = ExceptionRecord(
            id=str(uuid.uuid4()), run_id=original.run_id, exception_type=exception_type,
            severity=severity, owner_id=original.owner_id, status=status,
            original_preserved=True, correction_ref=original_id,
            created_at="2026-08-14T01:00:00+00:00",
        )
        self._items[record.id] = record
        return record

    def get(self, exception_id):
        return self._items[exception_id]

    def list_all(self):
        return list(self._items.values())


@pytest.fixture
def action_repo():
    repo = FakeActionRegisterRepository()
    app.dependency_overrides[get_action_register_repository] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_action_register_repository, None)


@pytest.fixture
def watch_repo():
    repo = FakeWatchListRepository()
    app.dependency_overrides[get_watch_list_repository] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_watch_list_repository, None)


@pytest.fixture
def exception_repo():
    repo = FakeExceptionRepository()
    app.dependency_overrides[get_exception_repository] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_exception_repository, None)


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# action-register
# ---------------------------------------------------------------------------

def test_create_action_returns_open(client, action_repo):
    response = client.post(
        "/api/action-register",
        json={"action_code": "ACT-001", "title": "Fix the feed", "status": "Open"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "Open"


def test_create_action_rejects_unknown_field(client, action_repo):
    response = client.post(
        "/api/action-register",
        json={"action_code": "ACT-001", "title": "x", "status": "Open", "surprise": "x"},
    )
    assert response.status_code == 422


def test_close_action_sets_closed_at(client, action_repo):
    action_id = client.post(
        "/api/action-register", json={"action_code": "ACT-001", "title": "x", "status": "Open"}
    ).json()["id"]
    response = client.post(
        f"/api/action-register/{action_id}/status", json={"status": "Closed"}
    )
    assert response.status_code == 200
    assert response.json()["closed_at"] is not None


def test_update_status_on_missing_action_is_404(client, action_repo):
    response = client.post(
        "/api/action-register/00000000-0000-0000-0000-000000000000/status",
        json={"status": "Closed"},
    )
    assert response.status_code == 404


def test_get_missing_action_is_404(client, action_repo):
    response = client.get("/api/action-register/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_list_actions_returns_created(client, action_repo):
    client.post("/api/action-register", json={"action_code": "ACT-001", "title": "x", "status": "Open"})
    client.post("/api/action-register", json={"action_code": "ACT-002", "title": "y", "status": "Open"})
    assert len(client.get("/api/action-register").json()) == 2


# ---------------------------------------------------------------------------
# watch-lists
# ---------------------------------------------------------------------------

def test_create_watch(client, watch_repo):
    response = client.post(
        "/api/watch-lists", json={"watch_code": "WL-001", "title": "Dairy review", "status": "Open"}
    )
    assert response.status_code == 201


def test_update_watch_status(client, watch_repo):
    watch_id = client.post(
        "/api/watch-lists", json={"watch_code": "WL-001", "title": "x", "status": "Open"}
    ).json()["id"]
    response = client.post(f"/api/watch-lists/{watch_id}/status", json={"status": "Closed"})
    assert response.status_code == 200
    assert response.json()["status"] == "Closed"


def test_get_missing_watch_is_404(client, watch_repo):
    response = client.get("/api/watch-lists/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# exceptions
# ---------------------------------------------------------------------------

def test_record_exception(client, exception_repo):
    response = client.post(
        "/api/exceptions",
        json={"exception_type": "Source Inaccessible", "severity": "High", "status": "Open"},
    )
    assert response.status_code == 201
    assert response.json()["correction_ref"] is None


def test_correct_exception_returns_201_and_a_new_id(client, exception_repo):
    original = client.post(
        "/api/exceptions",
        json={"exception_type": "Source Inaccessible", "severity": "High", "status": "Open"},
    ).json()
    response = client.post(
        f"/api/exceptions/{original['id']}/correct",
        json={
            "exception_type": "Source Inaccessible", "severity": "Low",
            "status": "Resolved", "reason": "fallback confirmed",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] != original["id"]
    assert body["correction_ref"] == original["id"]


def test_correcting_a_missing_exception_is_404(client, exception_repo):
    response = client.post(
        "/api/exceptions/00000000-0000-0000-0000-000000000000/correct",
        json={"exception_type": "x", "severity": "Low", "status": "Resolved", "reason": "x"},
    )
    assert response.status_code == 404


def test_correct_rejects_unknown_field(client, exception_repo):
    original = client.post(
        "/api/exceptions",
        json={"exception_type": "x", "severity": "High", "status": "Open"},
    ).json()
    response = client.post(
        f"/api/exceptions/{original['id']}/correct",
        json={
            "exception_type": "x", "severity": "Low", "status": "Resolved",
            "reason": "x", "actor_id": "00000000-0000-0000-0000-000000000ff",
        },
    )
    assert response.status_code == 422
