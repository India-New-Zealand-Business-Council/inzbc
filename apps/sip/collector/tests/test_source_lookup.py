from __future__ import annotations

from apps.sip.collector.source_lookup import (
    SourceIdLookup,
    SourceNameLookup,
    build_source_lookups,
)

_RECORDS = [
    {"id": "db-1", "sip185_code": "NZ-OFF-001", "name": "New Zealand Parliament"},
    {"id": "db-2", "sip185_code": "IN-OFF-001", "name": "Ministry of Commerce & Industry / PIB"},
    # source_library.sip185_code is nullable - a non-register source has no code.
    {"id": "db-3", "sip185_code": None, "name": "Some Ad-Hoc Blog"},
]


def test_build_source_lookups_splits_one_response_into_both_lookups() -> None:
    name_lookup, id_lookup = build_source_lookups(_RECORDS)

    assert isinstance(name_lookup, SourceNameLookup)
    assert isinstance(id_lookup, SourceIdLookup)
    assert name_lookup.get("New Zealand Parliament") == "db-1"
    assert id_lookup.get("NZ-OFF-001") == "db-1"


def test_build_source_lookups_omits_null_code_from_id_lookup() -> None:
    _name_lookup, id_lookup = build_source_lookups(_RECORDS)
    assert id_lookup.get("Some Ad-Hoc Blog") is None


def test_build_source_lookups_handles_empty_response() -> None:
    name_lookup, id_lookup = build_source_lookups([])
    assert name_lookup.get("anything") is None
    assert id_lookup.get("anything") is None


def test_source_name_lookup_and_source_id_lookup_are_distinct_types() -> None:
    # The whole point of two dataclasses instead of two dicts: a type checker (and this test)
    # can catch a caller passing one where the other belongs, which a bare dict could not.
    name_lookup = SourceNameLookup({"RNZ Business": "db-1"})
    id_lookup = SourceIdLookup({"NZ-OFF-001": "db-1"})
    assert type(name_lookup) is not type(id_lookup)
