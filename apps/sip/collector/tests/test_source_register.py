from __future__ import annotations

import pytest

from apps.sip.collector.source_register import (
    MANDATORY_SOURCES,
    SourceIdUnresolved,
    missing_mandatory_outcomes,
    record_source_outcome,
)
from apps.sip.pipeline.models import SourceOutcome

RUN_ID = "11111111-1111-1111-1111-111111111111"
MFAT_ID = "22222222-2222-2222-2222-222222222222"
LOOKUP = {"MFAT": MFAT_ID, "DGFT": "33333333-3333-3333-3333-333333333333"}


def test_mandatory_sources_are_all_flagged_mandatory() -> None:
    # This register only lists SIP-185's mandatory worklist; nothing in it should be optional.
    assert MANDATORY_SOURCES
    assert all(entry.mandatory for entry in MANDATORY_SOURCES)


def test_missing_mandatory_outcomes_reports_every_unrecorded_source() -> None:
    missing = missing_mandatory_outcomes(set())
    assert set(missing) == {entry.name for entry in MANDATORY_SOURCES}


def test_missing_mandatory_outcomes_empty_when_all_recorded() -> None:
    all_names = {entry.name for entry in MANDATORY_SOURCES}
    assert missing_mandatory_outcomes(all_names) == []


def test_missing_mandatory_outcomes_reports_only_the_gap() -> None:
    all_but_one = {entry.name for entry in MANDATORY_SOURCES if entry.name != "MFAT"}
    assert missing_mandatory_outcomes(all_but_one) == ["MFAT"]


def test_record_source_outcome_with_no_fallback() -> None:
    check = record_source_outcome(RUN_ID, "MFAT", SourceOutcome.INCLUDED, LOOKUP)

    assert check.run_id == RUN_ID
    assert check.outcome == SourceOutcome.INCLUDED
    assert check.fallback_used is False
    assert check.method is None
    assert check.notes is None
    assert check.source_id == MFAT_ID


def test_record_source_outcome_raises_when_source_id_unresolved() -> None:
    with pytest.raises(SourceIdUnresolved):
        record_source_outcome(RUN_ID, "MFAT", SourceOutcome.INCLUDED, {})


def test_record_source_outcome_folds_fallback_trail_into_notes() -> None:
    check = record_source_outcome(
        RUN_ID,
        "Stuff (controlled access)",
        SourceOutcome.INACCESSIBLE,
        {"Stuff (controlled access)": "44444444-4444-4444-4444-444444444444"},
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
        RUN_ID, "MFAT", SourceOutcome.INCLUDED, LOOKUP, fallback_attempts=["Direct access"]
    )
    assert check.fallback_used is False
    assert check.method == "Direct access"


def test_record_source_outcome_single_non_direct_attempt_is_a_fallback() -> None:
    # Only one attempt was recorded, but it skipped straight past "Direct access" - that's still
    # a fallback, not "no fallback used" (len(fallback_attempts) > 1 alone would miss this).
    check = record_source_outcome(
        RUN_ID,
        "MFAT",
        SourceOutcome.INCLUDED,
        LOOKUP,
        fallback_attempts=["RSS or approved feed"],
    )
    assert check.fallback_used is True
    assert check.method == "RSS or approved feed"


def test_record_source_outcome_combines_trail_and_extra_notes() -> None:
    check = record_source_outcome(
        RUN_ID,
        "DGFT",
        SourceOutcome.NO_QUALIFYING_ITEM,
        LOOKUP,
        fallback_attempts=["Direct access", "Indexed site search"],
        notes="Checked for NZ-relevant notifications only.",
    )
    assert check.notes == (
        "1. Direct access; 2. Indexed site search; Checked for NZ-relevant notifications only."
    )
