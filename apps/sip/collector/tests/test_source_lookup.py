from __future__ import annotations

import pytest

from apps.sip.collector.source_lookup import (
    DuplicateSip185Code,
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
    # Asserting on the record's own name/id would still pass if the bug reappeared as a literal
    # `None` key (`id_lookup.get(None)` wrongly returning something) - assert on the thing the
    # nullable-code case actually means: looking up `None` itself must never resolve.
    assert id_lookup.get(None) is None


def test_build_source_lookups_omits_a_name_shared_by_two_records() -> None:
    # Real case: data/sip185_sources_v1.0.csv has "Ministry of Defence" once for NZ and once for
    # India. A single-pass dict would let the second record silently overwrite the first, turning
    # an ambiguous name into a wrong-jurisdiction resolution instead of an unset one.
    records = [
        {"id": "nz-uuid", "sip185_code": "NZ-OFF-014", "name": "Ministry of Defence"},
        {"id": "in-uuid", "sip185_code": "IN-OFF-021", "name": "Ministry of Defence"},
    ]
    name_lookup, id_lookup = build_source_lookups(records)

    assert name_lookup.get("Ministry of Defence") is None
    # The id lookup is unaffected - sip185_code is unique per record even when name collides.
    assert id_lookup.get("NZ-OFF-014") == "nz-uuid"
    assert id_lookup.get("IN-OFF-021") == "in-uuid"


def test_build_source_lookups_treats_whitespace_variants_as_the_same_name() -> None:
    # mapping.map_article strips the article's source name before looking it up. Deduping on the
    # raw name would let "Ministry of Defence" and "Ministry of Defence " both look unique and
    # survive, then a stripped query would silently resolve to whichever raw key matched.
    records = [
        {"id": "nz-uuid", "sip185_code": "NZ-OFF-014", "name": "Ministry of Defence"},
        {"id": "in-uuid", "sip185_code": "IN-OFF-021", "name": "Ministry of Defence "},
    ]
    name_lookup, _id_lookup = build_source_lookups(records)

    assert name_lookup.get("Ministry of Defence") is None
    assert name_lookup.get("Ministry of Defence ") is None


def test_source_name_lookup_strips_its_own_argument() -> None:
    # Keys are stored stripped; a caller passing an unstripped query must still match, since
    # mapping.map_article always strips before calling .get().
    lookup = SourceNameLookup({"RNZ Business": "db-1"})
    assert lookup.get("RNZ Business ") == "db-1"
    assert lookup.get(" RNZ Business") == "db-1"


def test_build_source_lookups_raises_on_a_duplicate_sip185_code() -> None:
    # sip185_code is declared unique in database/schema.sql - two records sharing one can only
    # mean malformed endpoint data, and this lookup resolves a NOT NULL column, so this must fail
    # loudly rather than silently keep whichever record came last.
    records = [
        {"id": "2222", "sip185_code": "NZ-OFF-001", "name": "NZ Parliament"},
        {"id": "3333", "sip185_code": "NZ-OFF-001", "name": "Wrong duplicate"},
    ]
    with pytest.raises(DuplicateSip185Code):
        build_source_lookups(records)


def test_source_id_lookup_is_not_mutable_through_the_constructor_argument() -> None:
    # frozen=True only stops _by_code being rebound, not the dict it points at being mutated in
    # place - __post_init__ must copy so a caller's later mutation of the dict they passed in
    # cannot silently change an already-built lookup.
    data = {"NZ-OFF-001": "2222"}
    lookup = SourceIdLookup(data)
    data["NZ-OFF-001"] = "3333"
    assert lookup.get("NZ-OFF-001") == "2222"


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
