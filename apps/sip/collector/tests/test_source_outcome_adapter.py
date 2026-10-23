from __future__ import annotations

import pytest

from apps.sip.collector.source_lookup import SourceIdLookup, SourceNameLookup
from apps.sip.collector.source_outcome_adapter import (
    ConfirmedSourceObservation,
    prepare_confirmed_source_checks,
)
from apps.sip.pipeline.models import SourceOutcome

RUN = "11111111-1111-1111-1111-111111111111"
OTHER = "99999999-9999-9999-9999-999999999999"
LOOKUP = SourceIdLookup({"NZ-OFF-001": "22222222-2222-2222-2222-222222222222"})


def observation(**changes: object) -> ConfirmedSourceObservation:
    props = {
        "run_id": RUN,
        "sip185_code": "NZ-OFF-001",
        "outcome": SourceOutcome.INACCESSIBLE,
        "confirmed_by": "Analyst",
        "evidence_ref": "run-evidence://capture-1",
        "fallback_attempts": ("Direct access", "RSS or approved feed"),
    }
    props.update(changes)
    return ConfirmedSourceObservation(**props)


def test_prepares_source_check_without_io() -> None:
    [check] = prepare_confirmed_source_checks(RUN, [observation()], LOOKUP)
    assert check.run_id == RUN
    assert check.source_id == "22222222-2222-2222-2222-222222222222"
    assert check.outcome is SourceOutcome.INACCESSIBLE
    assert check.fallback_used is True
    assert check.method == "RSS or approved feed"
    assert "Human checked by: Analyst" in (check.notes or "")
    assert "Evidence reference: run-evidence://capture-1" in (check.notes or "")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"run_id": OTHER}, "different run"),
        ({"sip185_code": "NONEXISTENT"}, "unknown SIP-185"),
        ({"confirmed_by": " "}, "checker identity"),
        ({"evidence_ref": ""}, "evidence reference"),
        ({"outcome": "ok"}, "explicit SourceOutcome"),
        ({"outcome": None}, "explicit SourceOutcome"),
        ({"fallback_attempts": ("RSS or approved feed", "Direct access")}, "approved order"),
    ],
)
def test_rejects_unverifiable_source_checks(changes: dict, message: str) -> None:
    with pytest.raises((ValueError, TypeError), match=message):
        prepare_confirmed_source_checks(RUN, [observation(**changes)], LOOKUP)


def test_rejects_duplicate_source_codes_in_same_batch() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        prepare_confirmed_source_checks(RUN, [observation(), observation()], LOOKUP)


def test_rejects_name_lookup_and_missing_database_mapping() -> None:
    with pytest.raises(TypeError, match="SourceIdLookup"):
        prepare_confirmed_source_checks(RUN, [observation()], SourceNameLookup())
    with pytest.raises(RuntimeError, match="no source_library id"):
        prepare_confirmed_source_checks(RUN, [observation()], SourceIdLookup())


def test_empty_batch_is_not_a_claim_of_complete_coverage() -> None:
    assert prepare_confirmed_source_checks(RUN, [], LOOKUP) == []


def test_requires_run_identity() -> None:
    with pytest.raises(ValueError, match="run_id"):
        prepare_confirmed_source_checks("", [observation()], LOOKUP)
