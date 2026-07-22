from __future__ import annotations

from apps.sip.collector.source_lookup import build_source_lookup, fetch_source_lookup


def _row(**overrides: object) -> dict:
    base = {
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "MFAT",
        "layer": 1,
        "mandatory": True,
        "active": True,
    }
    base.update(overrides)
    return base


def test_build_source_lookup_maps_name_to_id() -> None:
    rows = [_row(), _row(id="22222222-2222-2222-2222-222222222222", name="Beehive")]
    lookup = build_source_lookup(rows)

    assert lookup == {
        "MFAT": "11111111-1111-1111-1111-111111111111",
        "Beehive": "22222222-2222-2222-2222-222222222222",
    }


def test_build_source_lookup_excludes_inactive_rows() -> None:
    rows = [_row(active=True), _row(id="33333333-3333-3333-3333-333333333333", name="Old Feed", active=False)]
    lookup = build_source_lookup(rows)

    assert "Old Feed" not in lookup
    assert lookup == {"MFAT": "11111111-1111-1111-1111-111111111111"}


def test_build_source_lookup_empty_for_no_rows() -> None:
    assert build_source_lookup([]) == {}


class _FakeClient:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def list_source_library(self) -> list[dict]:
        return self._rows


def test_fetch_source_lookup_calls_client_and_builds_map() -> None:
    client = _FakeClient([_row()])
    assert fetch_source_lookup(client) == {"MFAT": "11111111-1111-1111-1111-111111111111"}
