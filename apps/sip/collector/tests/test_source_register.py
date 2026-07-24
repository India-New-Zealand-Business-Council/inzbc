from __future__ import annotations

import pytest

from apps.sip.collector.source_register import (
    ALL_SOURCES,
    MANDATORY_SOURCES,
    SourceIdUnresolved,
    _parse_mandatory,
    missing_mandatory_outcomes,
    record_source_outcome,
)
from apps.sip.pipeline.models import SourceOutcome

RUN_ID = "11111111-1111-1111-1111-111111111111"
# NZ-OFF-001 (New Zealand Parliament) is a real mandatory source in SIP-185 v1.0.
PARLIAMENT_ID = "NZ-OFF-001"
DB_ID = "22222222-2222-2222-2222-222222222222"
LOOKUP = {PARLIAMENT_ID: DB_ID, "NZ-OFF-002": "33333333-3333-3333-3333-333333333333"}


def test_register_loads_v1_0_counts() -> None:
    # Locks the approved SIP-185 v1.0 register: 176 sources, 112 of them mandatory. If the CSV
    # is re-exported and these change, that is a deliberate register change to review here.
    assert len(ALL_SOURCES) == 176
    assert len(MANDATORY_SOURCES) == 112


def test_source_ids_are_unique() -> None:
    # The coverage gate keys on source id, so ids must be unique (names are not - NZ and India
    # both have a "Ministry of Defence"/"Ministry of Education").
    ids = [s.source_id for s in ALL_SOURCES]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize(
    ("raw", "expected"), [("true", True), ("false", False), (" TRUE ", True), ("False", False)]
)
def test_parse_mandatory_accepts_valid_bools(raw: str, expected: bool) -> None:
    assert _parse_mandatory(raw, "NZ-OFF-001") is expected


@pytest.mark.parametrize("raw", ["", "  ", "mandatory", "yes", "1", "selective"])
def test_parse_mandatory_rejects_anything_else(raw: str) -> None:
    # A blank/typo/garbled value must fail the load, not silently coerce to False and drop the
    # source from the Critical-stop coverage gate (fail-open).
    with pytest.raises(ValueError):
        _parse_mandatory(raw, "NZ-OFF-001")


def test_mandatory_sources_are_all_flagged_mandatory() -> None:
    assert MANDATORY_SOURCES
    assert all(entry.mandatory for entry in MANDATORY_SOURCES)


def test_missing_mandatory_outcomes_reports_every_unrecorded_source() -> None:
    missing = missing_mandatory_outcomes(set())
    assert set(missing) == {entry.source_id for entry in MANDATORY_SOURCES}


def test_missing_mandatory_outcomes_empty_when_all_recorded() -> None:
    all_ids = {entry.source_id for entry in MANDATORY_SOURCES}
    assert missing_mandatory_outcomes(all_ids) == []


def test_missing_mandatory_outcomes_reports_only_the_gap() -> None:
    all_but_one = {entry.source_id for entry in MANDATORY_SOURCES if entry.source_id != PARLIAMENT_ID}
    assert missing_mandatory_outcomes(all_but_one) == [PARLIAMENT_ID]


def test_record_source_outcome_with_no_fallback() -> None:
    check = record_source_outcome(RUN_ID, PARLIAMENT_ID, SourceOutcome.INCLUDED, LOOKUP)

    assert check.run_id == RUN_ID
    assert check.outcome == SourceOutcome.INCLUDED
    assert check.fallback_used is False
    assert check.method is None
    assert check.notes is None
    assert check.source_id == DB_ID


def test_record_source_outcome_raises_when_source_id_unresolved() -> None:
    with pytest.raises(SourceIdUnresolved):
        record_source_outcome(RUN_ID, PARLIAMENT_ID, SourceOutcome.INCLUDED, {})


def test_record_source_outcome_folds_fallback_trail_into_notes() -> None:
    check = record_source_outcome(
        RUN_ID,
        PARLIAMENT_ID,
        SourceOutcome.INACCESSIBLE,
        LOOKUP,
        fallback_attempts=["Direct access", "Search within the source", "RSS or approved feed"],
        access_error="403 on direct fetch",
    )

    assert check.fallback_used is True
    assert check.method == "RSS or approved feed"
    assert check.access_error == "403 on direct fetch"
    assert check.notes == (
        "1. Direct access; 2. Search within the source; 3. RSS or approved feed"
    )


def test_record_source_outcome_single_attempt_is_not_a_fallback() -> None:
    # Only "Direct access" was tried - that succeeded on the first try, not a fallback.
    check = record_source_outcome(
        RUN_ID, PARLIAMENT_ID, SourceOutcome.INCLUDED, LOOKUP, fallback_attempts=["Direct access"]
    )
    assert check.fallback_used is False
    assert check.method == "Direct access"


def test_record_source_outcome_single_non_direct_attempt_is_a_fallback() -> None:
    # Only one attempt was recorded, but it skipped straight past "Direct access" - that's still
    # a fallback, not "no fallback used" (len(fallback_attempts) > 1 alone would miss this).
    check = record_source_outcome(
        RUN_ID,
        PARLIAMENT_ID,
        SourceOutcome.INCLUDED,
        LOOKUP,
        fallback_attempts=["RSS or approved feed"],
    )
    assert check.fallback_used is True
    assert check.method == "RSS or approved feed"


def test_record_source_outcome_combines_trail_and_extra_notes() -> None:
    check = record_source_outcome(
        RUN_ID,
        "NZ-OFF-002",
        SourceOutcome.NO_QUALIFYING_ITEM,
        LOOKUP,
        fallback_attempts=["Direct access", "Indexed site search"],
        notes="Checked for NZ-relevant notifications only.",
    )
    assert check.notes == (
        "1. Direct access; 2. Indexed site search; Checked for NZ-relevant notifications only."
    )
