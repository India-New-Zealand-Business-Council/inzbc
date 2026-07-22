from __future__ import annotations

import pytest
from pydantic import ValidationError

from apps.sip.collector.assessment import CandidateAssessment, apply_candidate_assessment
from apps.sip.collector.verification import UnverifiedHighSignalError
from apps.sip.pipeline.models import SignalStrength, SourceConfidence, VerificationState

CANDIDATE_ID = "11111111-1111-1111-1111-111111111111"


class _FakeClient:
    def __init__(self) -> None:
        self.patched: list[tuple[str, dict]] = []

    def patch_candidate(self, candidate_id: str, fields: dict) -> dict:
        self.patched.append((candidate_id, fields))
        return {"id": candidate_id, **fields}


def test_assessment_rejects_relevance_out_of_range() -> None:
    with pytest.raises(ValidationError):
        CandidateAssessment(nz_relevance=6)


def test_apply_candidate_assessment_sends_only_set_fields() -> None:
    client = _FakeClient()
    assessment = CandidateAssessment(
        nz_relevance=4,
        signal=SignalStrength.HIGH,
        confidence=SourceConfidence.HIGH,
        verification=VerificationState.VERIFIED,
    )

    result = apply_candidate_assessment(client, CANDIDATE_ID, assessment)

    assert client.patched == [
        (
            CANDIDATE_ID,
            {
                "nz_relevance": 4,
                "signal": "High",
                "confidence": "High",
                "verification": "Verified",
            },
        )
    ]
    assert result["id"] == CANDIDATE_ID


def test_apply_candidate_assessment_can_mark_duplicate() -> None:
    client = _FakeClient()
    assessment = CandidateAssessment(duplicate_of="22222222-2222-2222-2222-222222222222")

    apply_candidate_assessment(client, CANDIDATE_ID, assessment)

    assert client.patched == [
        (CANDIDATE_ID, {"duplicate_of": "22222222-2222-2222-2222-222222222222"})
    ]


def test_apply_candidate_assessment_can_set_included_false() -> None:
    client = _FakeClient()
    assessment = CandidateAssessment(included=False, reason="Duplicate of an earlier item")

    apply_candidate_assessment(client, CANDIDATE_ID, assessment)

    assert client.patched == [
        (CANDIDATE_ID, {"included": False, "reason": "Duplicate of an earlier item"})
    ]


def test_apply_candidate_assessment_blocks_critical_without_verification() -> None:
    client = _FakeClient()
    assessment = CandidateAssessment(signal=SignalStrength.CRITICAL)

    with pytest.raises(UnverifiedHighSignalError):
        apply_candidate_assessment(client, CANDIDATE_ID, assessment)

    assert client.patched == []


def test_apply_candidate_assessment_allows_critical_using_current_verification() -> None:
    client = _FakeClient()
    assessment = CandidateAssessment(signal=SignalStrength.CRITICAL, reason="Confirmed by MFAT")

    apply_candidate_assessment(
        client,
        CANDIDATE_ID,
        assessment,
        current_verification=VerificationState.VERIFIED,
    )

    assert client.patched == [
        (CANDIDATE_ID, {"signal": "Critical", "reason": "Confirmed by MFAT"})
    ]


def test_apply_candidate_assessment_blocks_verification_downgrade_on_existing_critical() -> None:
    # The candidate is already Critical (current_signal); this assessment only touches
    # verification, downgrading it to Unverified. That must be caught even though this
    # particular PATCH never sets `signal` itself.
    client = _FakeClient()
    assessment = CandidateAssessment(verification=VerificationState.UNVERIFIED)

    with pytest.raises(UnverifiedHighSignalError):
        apply_candidate_assessment(
            client,
            CANDIDATE_ID,
            assessment,
            current_signal=SignalStrength.CRITICAL,
        )

    assert client.patched == []


def test_apply_candidate_assessment_allows_unrelated_patch_on_existing_critical_verified() -> None:
    # The candidate is already Critical and Verified (both passed as "current_*"); a patch that
    # only sets an unrelated field shouldn't be blocked just because signal/verification aren't
    # touched in this call.
    client = _FakeClient()
    assessment = CandidateAssessment(proposed_routing="Daily Brief")

    apply_candidate_assessment(
        client,
        CANDIDATE_ID,
        assessment,
        current_signal=SignalStrength.CRITICAL,
        current_verification=VerificationState.VERIFIED,
    )

    assert client.patched == [(CANDIDATE_ID, {"proposed_routing": "Daily Brief"})]
