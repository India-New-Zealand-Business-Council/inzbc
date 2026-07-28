"""End-to-end integration tests for the collector's fail-closed behaviour (#56).

Each unit test elsewhere in this package checks one module in isolation against a stub. These
tests instead run a whole slice of the SIP-184 flow - capture, dedupe, verification gate,
mandatory-source coverage - through `FakeSipApi`, an in-memory stand-in for the real API that
actually stores state across calls the way the server would. The point is to catch a regression
where each module still passes its own unit tests but the fail-closed behaviour breaks at the
seam between them (e.g. `apply_candidate_assessment` calling the gate with the wrong effective
signal because of how `ingest_articles` and `dedupe` populated the candidate first).

Uses the real SIP-185 v1.0 register (`source_register.MANDATORY_SOURCES`, 112 real mandatory
sources) for the coverage-gate tests rather than a handful of fixture sources - a suite that only
ever tests 2-3 sources would not catch a gate that only works for small inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from apps.sip.collector.assessment import (
    CandidateAssessment,
    MissingCurrentSignalError,
    apply_candidate_assessment,
)
from apps.sip.collector.dedupe import find_duplicate_of
from apps.sip.collector.ingest import ingest_articles
from apps.sip.collector.source_lookup import SourceIdLookup
from apps.sip.collector.source_register import (
    MANDATORY_SOURCES,
    SourceIdUnresolved,
    missing_mandatory_outcomes,
    record_source_outcome,
)
from apps.sip.collector.verification import UnverifiedHighSignalError
from apps.sip.pipeline.client import SipApiError
from apps.sip.pipeline.models import SignalStrength, SourceOutcome, VerificationState

RUN_ID = "11111111-1111-1111-1111-111111111111"


@dataclass
class FakeSipApi:
    """In-memory stand-in for the real API surface `client.py` calls, keyed like the real
    tables would be - a candidate/source-check written here is visible to a later call in the
    same test, unlike a stub that only records what it was asked to do.
    """

    candidates: dict[str, dict] = field(default_factory=dict)
    source_checks: list[dict] = field(default_factory=list)
    _next_id: int = 0

    def _new_id(self, prefix: str) -> str:
        self._next_id += 1
        return f"{prefix}-{self._next_id}"

    # ---------- the subset of SipPipelineClient's surface this suite exercises ----------

    def create_candidate(self, candidate) -> dict:  # noqa: ANN001 - duck-typed fake
        payload = candidate.model_dump(mode="json", exclude_none=True)
        payload["id"] = self._new_id("cand")
        self.candidates[payload["id"]] = payload
        return payload

    def list_candidates(self, run_id: str) -> list[dict]:
        return [c for c in self.candidates.values() if c["run_id"] == run_id]

    def patch_candidate(self, candidate_id: str, fields: dict) -> dict:
        if candidate_id not in self.candidates:
            raise SipApiError(404, f"no candidate {candidate_id!r}")
        self.candidates[candidate_id].update(fields)
        return self.candidates[candidate_id]

    def record_source_check(self, run_id: str, source_check) -> dict:  # noqa: ANN001
        payload = source_check.model_dump(mode="json", exclude_none=True)
        payload["id"] = self._new_id("check")
        self.source_checks.append(payload)
        return payload


def _article(**overrides: object) -> dict:
    base = {
        "title": "India, NZ discuss FTA next steps",
        "description": "Officials met to progress trade talks.",
        "url": "https://example.com/fta-talks",
        "source": "RNZ Business",
        "published": "2026-07-28 09:00:00+00:00",
        "score": 40,
        "nz_relevance_score": 20,
        "sectors": "Trade and FTA",
    }
    base.update(overrides)
    return base


# ---------- capture -> dedupe ----------


def test_full_run_captures_then_flags_a_cross_run_duplicate_by_url() -> None:
    api = FakeSipApi()

    # A prior run already captured this story.
    ingest_articles(api, RUN_ID, [_article(title="FTA talks continue")])
    [existing] = api.list_candidates(RUN_ID)

    # Today's fetch turns up the same url again (a later run, same story recirculating).
    today_run = "22222222-2222-2222-2222-222222222222"
    todays_article = _article(title="FTA talks continue (updated)")
    result = ingest_articles(api, today_run, [todays_article])
    assert result.failed == []
    [new_candidate] = api.list_candidates(today_run)

    duplicate_of = find_duplicate_of(todays_article, api.list_candidates(RUN_ID))
    assert duplicate_of == existing["id"]

    apply_candidate_assessment(
        api, new_candidate["id"], CandidateAssessment(duplicate_of=duplicate_of)
    )
    assert api.candidates[new_candidate["id"]]["duplicate_of"] == existing["id"]


def test_a_malformed_article_does_not_block_capture_or_dedupe_of_the_rest() -> None:
    api = FakeSipApi()
    malformed = _article()
    del malformed["title"]  # Candidate.headline is required - this article can't map.
    articles = [_article(title="First"), malformed, _article(title="Second", url="")]

    result = ingest_articles(api, RUN_ID, articles)

    assert len(result.failed) == 1
    assert {c["headline"] for c in api.list_candidates(RUN_ID)} == {"First", "Second"}


# ---------- verification gate, end to end through apply_candidate_assessment ----------


def test_verification_gate_blocks_an_unverified_high_signal_patch_end_to_end() -> None:
    api = FakeSipApi()
    ingest_articles(api, RUN_ID, [_article()])
    [candidate] = api.list_candidates(RUN_ID)
    before = dict(api.candidates[candidate["id"]])

    with pytest.raises(UnverifiedHighSignalError):
        apply_candidate_assessment(
            api,
            candidate["id"],
            CandidateAssessment(
                signal=SignalStrength.HIGH, verification=VerificationState.UNVERIFIED
            ),
        )

    # The gate must refuse before the PATCH is sent - a failed gate must not still write.
    assert api.candidates[candidate["id"]] == before


def test_verification_gate_allows_a_verified_high_signal_patch_end_to_end() -> None:
    api = FakeSipApi()
    ingest_articles(api, RUN_ID, [_article()])
    [candidate] = api.list_candidates(RUN_ID)

    apply_candidate_assessment(
        api,
        candidate["id"],
        CandidateAssessment(
            signal=SignalStrength.HIGH, verification=VerificationState.VERIFIED
        ),
    )

    assert api.candidates[candidate["id"]]["signal"] == SignalStrength.HIGH.value
    assert api.candidates[candidate["id"]]["verification"] == VerificationState.VERIFIED.value


def test_verification_downgrade_on_an_already_high_candidate_is_blocked_end_to_end() -> None:
    api = FakeSipApi()
    ingest_articles(api, RUN_ID, [_article()])
    [candidate] = api.list_candidates(RUN_ID)
    apply_candidate_assessment(
        api,
        candidate["id"],
        CandidateAssessment(
            signal=SignalStrength.CRITICAL, verification=VerificationState.VERIFIED
        ),
    )

    # A later patch touches only verification. Without current_signal this must refuse rather
    # than silently treat the already-Critical candidate as safe to downgrade.
    with pytest.raises(MissingCurrentSignalError):
        apply_candidate_assessment(
            api,
            candidate["id"],
            CandidateAssessment(verification=VerificationState.UNVERIFIED),
        )
    assert api.candidates[candidate["id"]]["verification"] == VerificationState.VERIFIED.value


# ---------- mandatory-source Critical stop, against the real v1.0 register ----------


def _fake_id_lookup() -> SourceIdLookup:
    return SourceIdLookup({s.source_id: f"db-{s.source_id}" for s in MANDATORY_SOURCES})


def test_mandatory_source_coverage_gate_reports_the_real_gap() -> None:
    # Record every mandatory source except one, against the real 112-source v1.0 register - a
    # suite that only ever exercises a handful of fixture sources would not catch a gate that
    # only works for small inputs.
    id_lookup = _fake_id_lookup()
    api = FakeSipApi()
    skip = MANDATORY_SOURCES[-1]

    for source in MANDATORY_SOURCES:
        if source is skip:
            continue
        check = record_source_outcome(RUN_ID, source.source_id, SourceOutcome.INCLUDED, id_lookup)
        api.record_source_check(RUN_ID, check)

    recorded_ids = {c["source_id"] for c in api.source_checks}
    # The gate itself is keyed on SIP-185 source id, not the db uuid that ended up on the check.
    recorded_source_ids = {s.source_id for s in MANDATORY_SOURCES if s is not skip}
    missing = missing_mandatory_outcomes(recorded_source_ids)

    assert missing == [skip.source_id]
    assert len(recorded_ids) == len(MANDATORY_SOURCES) - 1


def test_mandatory_source_coverage_gate_clears_when_every_source_is_recorded() -> None:
    id_lookup = _fake_id_lookup()
    api = FakeSipApi()

    for source in MANDATORY_SOURCES:
        check = record_source_outcome(RUN_ID, source.source_id, SourceOutcome.INCLUDED, id_lookup)
        api.record_source_check(RUN_ID, check)

    recorded_source_ids = {s.source_id for s in MANDATORY_SOURCES}
    assert missing_mandatory_outcomes(recorded_source_ids) == []
    assert len(api.source_checks) == len(MANDATORY_SOURCES)


def test_recording_a_source_outcome_for_an_unseeded_source_fails_loudly() -> None:
    # A source missing from the fake source_library (e.g. not seeded yet) must raise rather than
    # silently write a source check with no db id - source_checks.source_id is NOT NULL.
    empty_lookup = SourceIdLookup()
    with pytest.raises(SourceIdUnresolved):
        record_source_outcome(
            RUN_ID, MANDATORY_SOURCES[0].source_id, SourceOutcome.INCLUDED, empty_lookup
        )
