"""Unit tests for the `/api/source-library` router (#55): HTTP <-> repository mapping only.

Same shape as test_runs_api.py's FakeRunRepository - a fake proves the router calls the
repository and shapes the response correctly; the repository's actual SQL is proven against a
real Postgres in test_source_library.py.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from services.api.main import app
from services.api.source_library import SourceLibraryRow, get_source_library_repository


class FakeSourceLibraryRepository:
    def __init__(self, rows: list[SourceLibraryRow]) -> None:
        self._rows = rows

    def list_sources(self) -> list[SourceLibraryRow]:
        return self._rows


def _client(rows: list[SourceLibraryRow]) -> TestClient:
    app.dependency_overrides[get_source_library_repository] = lambda: FakeSourceLibraryRepository(
        rows
    )
    return TestClient(app)


def test_list_source_library_returns_seeded_rows() -> None:
    rows = [
        SourceLibraryRow(id="1", sip185_code="NZ-OFF-001", name="New Zealand Parliament"),
        SourceLibraryRow(id="2", sip185_code=None, name="Ad-hoc source"),
    ]
    client = _client(rows)
    try:
        response = client.get("/api/source-library")
        assert response.status_code == 200
        assert response.json() == [
            {"id": "1", "sip185_code": "NZ-OFF-001", "name": "New Zealand Parliament"},
            {"id": "2", "sip185_code": None, "name": "Ad-hoc source"},
        ]
    finally:
        app.dependency_overrides.pop(get_source_library_repository, None)


def test_list_source_library_empty_when_unseeded() -> None:
    client = _client([])
    try:
        response = client.get("/api/source-library")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.pop(get_source_library_repository, None)
