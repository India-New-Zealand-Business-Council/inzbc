"""Integration tests for the candidate persistence adapter (#121), against a real Postgres.

Same skip/DATABASE_URL convention as `test_persistence.py`: a mock would prove this module calls
psycopg correctly, not that the verification gate and audit trail actually hold against real
transaction semantics.
"""

from __future__ import annotations

import os
import uuid
from datetime import date

import psycopg
import pytest

from apps.sip.collector.verification import UnverifiedHighSignalError
from apps.sip.pipeline.models import SignalStrength, VerificationState
from services.api.candidate_persistence import (
    CandidateRepository,
    SelfVerificationError,
)
from services.api.tests.role_seed import grant

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - candidate persistence tests need a real Postgres with "
    "schema.sql applied",
)


@pytest.fixture
def repo() -> CandidateRepository:
    return CandidateRepository(DATABASE_URL)


@pytest.fixture
def user_id() -> str:
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "insert into users (name, email) values (%s, %s) returning id",
            (f"Test User {uuid.uuid4()}", f"{uuid.uuid4()}@example.com"),
        ).fetchone()
        grant(conn, row[0], "Analyst")
        conn.commit()
    return str(row[0])


@pytest.fixture
def reviewer_id() -> str:
    """A second person, because verification by the capturer is now refused (BR8).

    Until that check existed, every test here captured and verified as the same user, so the
    suite was exercising exactly the self-verification the control forbids and passing.
    """
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "insert into users (name, email) values (%s, %s) returning id",
            (f"Reviewer {uuid.uuid4()}", f"{uuid.uuid4()}@example.com"),
        ).fetchone()
        grant(conn, row[0], "Reviewer")
        conn.commit()
    return str(row[0])


@pytest.fixture
def run_id(user_id: str) -> str:
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "insert into runs (run_number, prompt_version, coverage_start_utc, "
            "coverage_end_utc, initiated_by) values (%s, %s, %s, %s, %s) returning id",
            (
                f"RUN-TEST-{uuid.uuid4().hex[:12]}",
                "SIP-050 v1.1",
                "2026-07-27T07:00:00+12:00",
                "2026-07-28T07:00:00+12:00",
                user_id,
            ),
        ).fetchone()
        conn.commit()
    return str(row[0])


def test_capture_creates_an_unverified_candidate(
    repo: CandidateRepository, run_id: str, user_id: str
) -> None:
    candidate = repo.capture(
        run_id=run_id,
        headline="Test headline",
        source_id=None,
        url="https://example.test/a",
        summary=None,
        published_at=None,
        in_coverage_window=True,
        actor_id=user_id,
    )
    assert candidate.verification == VerificationState.UNVERIFIED
    assert candidate.run_id == run_id


def test_get_raises_key_error_for_unknown_id(repo: CandidateRepository) -> None:
    with pytest.raises(KeyError):
        repo.get(str(uuid.uuid4()))


def test_list_for_run_only_returns_that_runs_candidates(
    repo: CandidateRepository, run_id: str, user_id: str
) -> None:
    mine = repo.capture(
        run_id=run_id, headline="Mine", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=user_id,
    )
    other_run = repo.capture(
        run_id=run_id, headline="Also mine, same run", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=user_id,
    )

    candidates = repo.list_for_run(run_id)

    ids = {c.id for c in candidates}
    assert {mine.id, other_run.id} <= ids


def test_verify_sets_verification_and_writes_audit_row(
    repo: CandidateRepository, run_id: str, user_id: str, reviewer_id: str
) -> None:
    candidate = repo.capture(
        run_id=run_id, headline="x", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=user_id,
    )

    updated = repo.record_verification(
        candidate.id, VerificationState.VERIFIED, actor_id=reviewer_id,
        reason="checked MFAT source"
    )

    assert updated.verification == VerificationState.VERIFIED
    with psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row) as conn:
        audit_row = conn.execute(
            "select action, reason from audit_log where record_id = %s and action = %s",
            (candidate.id, "candidate.verify"),
        ).fetchone()
    assert audit_row is not None
    assert audit_row["reason"] == "checked MFAT source"


def test_score_refuses_critical_signal_without_verification(
    repo: CandidateRepository, run_id: str, user_id: str
) -> None:
    """The security-critical property #121 exists for: a candidate must not carry a Critical
    signal while still Unverified, whether that combination arrives via score-then-verify or
    verify-then-score. This is the score-sets-signal-first direction.
    """
    candidate = repo.capture(
        run_id=run_id, headline="x", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=user_id,
    )

    with pytest.raises(UnverifiedHighSignalError):
        repo.record_score(
            candidate.id,
            nz_relevance=5, india_relevance=5, member_relevance=5,
            signal=SignalStrength.CRITICAL, confidence=None,
            actor_id=user_id, reason="looks critical",
        )

    # The refused write must not have landed.
    assert repo.get(candidate.id).signal is None


def test_verify_refuses_downgrade_on_an_already_critical_candidate(
    repo: CandidateRepository, run_id: str, user_id: str, reviewer_id: str
) -> None:
    """The other direction: signal set to Critical first (with the verified state a score-then-
    verify workflow would have required at the time), then a later verify call tries to downgrade
    verification while the candidate is still Critical. Because this module always reads the
    live row, it always knows the current signal - this is exactly the gap
    `apps/sip/collector/assessment.py`'s `MissingCurrentSignalError` exists to refuse when the
    caller *doesn't* have a live read.
    """
    candidate = repo.capture(
        run_id=run_id, headline="x", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=user_id,
    )
    repo.record_verification(
        candidate.id, VerificationState.VERIFIED, actor_id=reviewer_id,
        reason="initially verified"
    )
    repo.record_score(
        candidate.id,
        nz_relevance=5, india_relevance=5, member_relevance=5,
        signal=SignalStrength.CRITICAL, confidence=None,
        actor_id=user_id, reason="now scored critical",
    )

    with pytest.raises(UnverifiedHighSignalError):
        repo.record_verification(
            candidate.id, VerificationState.UNVERIFIED, actor_id=reviewer_id, reason="oops"
        )

    assert repo.get(candidate.id).verification == VerificationState.VERIFIED


def test_route_sets_proposed_routing(
    repo: CandidateRepository, run_id: str, user_id: str
) -> None:
    candidate = repo.capture(
        run_id=run_id, headline="x", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=user_id,
    )

    updated = repo.record_routing(
        candidate.id, proposed_routing="Daily Intelligence", included=True,
        actor_id=user_id, reason="relevant",
    )

    assert updated.proposed_routing == "Daily Intelligence"
    assert updated.included is True


def test_merge_sets_duplicate_of_and_excludes(
    repo: CandidateRepository, run_id: str, user_id: str
) -> None:
    original = repo.capture(
        run_id=run_id, headline="Original", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=user_id,
    )
    duplicate = repo.capture(
        run_id=run_id, headline="Same story, later capture", source_id=None, url=None,
        summary=None, published_at=None, in_coverage_window=None, actor_id=user_id,
    )

    updated = repo.merge(
        duplicate.id, original.id, actor_id=user_id, reason="same story"
    )

    assert updated.duplicate_of == original.id
    assert updated.included is False


def test_merge_refuses_self_merge(
    repo: CandidateRepository, run_id: str, user_id: str
) -> None:
    candidate = repo.capture(
        run_id=run_id, headline="x", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=user_id,
    )
    with pytest.raises(ValueError):
        repo.merge(candidate.id, candidate.id, actor_id=user_id, reason="n/a")


def test_merge_raises_key_error_for_an_unknown_target(
    repo: CandidateRepository, run_id: str, user_id: str
) -> None:
    candidate = repo.capture(
        run_id=run_id, headline="x", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=user_id,
    )
    with pytest.raises(KeyError):
        repo.merge(candidate.id, str(uuid.uuid4()), actor_id=user_id, reason="n/a")


def test_the_capturer_cannot_verify_their_own_candidate(
    repo: CandidateRepository, run_id: str, user_id: str
) -> None:
    """BR8. Until this existed, one principal could carry a candidate from capture to verified.

    A role check cannot catch it: `require_roles` is an OR over the roles held, and the schema
    says the steady state after the placement is one person holding every role, so anyone with
    both Analyst and Reviewer passed both gates.
    """
    candidate = repo.capture(
        run_id=run_id, headline="Self-verified", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=user_id,
    )
    with pytest.raises(SelfVerificationError, match="captured this candidate"):
        repo.record_verification(
            candidate.id, VerificationState.VERIFIED, actor_id=user_id, reason="looks fine to me"
        )


def test_the_assessor_cannot_verify_their_own_candidate(
    repo: CandidateRepository, run_id: str, user_id: str, reviewer_id: str
) -> None:
    """Scoring is an act of judgement too. Someone who set the relevance scores and signal is
    checking their own assessment, even if a different person captured the item."""
    candidate = repo.capture(
        run_id=run_id, headline="Assessed then verified", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=reviewer_id,
    )
    repo.record_score(
        candidate.id, nz_relevance=4, india_relevance=4, member_relevance=3,
        signal=None, confidence=None, actor_id=user_id, reason="scored",
    )
    with pytest.raises(SelfVerificationError, match="assessed this candidate"):
        repo.record_verification(
            candidate.id, VerificationState.VERIFIED, actor_id=user_id, reason="mine looks right"
        )


def test_holding_every_role_does_not_exempt_anyone(
    repo: CandidateRepository, run_id: str, user_id: str
) -> None:
    """The exemption that matters. An exemption the most senior person can grant themselves is
    not a control, so SIP Owner does not bypass this and neither does holding all seven roles."""
    with psycopg.connect(DATABASE_URL) as conn:
        grant(conn, user_id, "SIP Owner", "Reviewer", "Analyst")
        conn.commit()

    candidate = repo.capture(
        run_id=run_id, headline="Omnipotent", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=user_id,
    )
    with pytest.raises(SelfVerificationError):
        repo.record_verification(
            candidate.id, VerificationState.VERIFIED, actor_id=user_id, reason="I am the owner"
        )


def test_a_second_person_may_verify(
    repo: CandidateRepository, run_id: str, user_id: str, reviewer_id: str
) -> None:
    """The other half: this refuses self-verification, not verification."""
    candidate = repo.capture(
        run_id=run_id, headline="Properly reviewed", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=user_id,
    )
    updated = repo.record_verification(
        candidate.id, VerificationState.VERIFIED, actor_id=reviewer_id, reason="checked the source"
    )
    assert updated.verification == VerificationState.VERIFIED


def test_unknown_provenance_is_currently_permitted(
    repo: CandidateRepository, run_id: str, reviewer_id: str
) -> None:
    """Rows predating provenance have null `captured_by`, and verification of them is permitted.

    Named for what it asserts. An earlier version of this test was called
    `test_unknown_provenance_refuses_rather_than_permits` and its docstring said unknown
    authorship "must not" be treated as permission, while the body asserted the verification
    succeeded. A test whose name contradicts its assertion is worse than no test: it reads as
    evidence of a control that does not exist.

    The behaviour is a deliberate trade-off, not an oversight. A row with no recorded capturer
    cannot be verified by anyone if null refuses, which would strand every candidate captured
    before this column existed. Recorded here so that changing it is a decision rather than an
    accident.
    """
    with psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row) as conn:
        row = conn.execute(
            "insert into candidates (run_id, headline) values (%s, %s) returning id",
            (run_id, "Legacy row with no recorded capturer"),
        ).fetchone()
        conn.commit()

    # Permitted today: a null capturer is not equal to the verifier, so this is the documented
    # current behaviour rather than a claim that unknown provenance is safe. Recorded here so a
    # change to it is deliberate.
    updated = repo.record_verification(
        str(row["id"]), VerificationState.VERIFIED, actor_id=reviewer_id, reason="legacy"
    )
    assert updated.verification == VerificationState.VERIFIED


def _candidate_exception(
    candidate_id: str, actor_id: str, *, approved_by: str, review_date: date | None = None
) -> str:
    with psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row) as conn:
        row = conn.execute(
            "insert into candidate_sod_exceptions (candidate_id, actor_id, approved_by, reason, "
            "review_date) values (%s, %s, %s, %s, %s) returning id",
            (candidate_id, actor_id, approved_by,
             "single operator; no second reviewer available", review_date or date(2099, 1, 1)),
        ).fetchone()
        conn.commit()
    return str(row["id"])


def test_a_recorded_exception_permits_the_capturer_to_verify(
    repo: CandidateRepository, run_id: str, user_id: str, reviewer_id: str
) -> None:
    """The path that makes this control usable at all.

    INZBC is one person holding every role. Refusing outright would make verification impossible
    for the only operator there is, and a control that blocks all legitimate work gets switched
    off. Recording the exception keeps the audit trail honest instead: it says one person carried
    this candidate end to end, and who authorised that.
    """
    candidate = repo.capture(
        run_id=run_id, headline="Single operator", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=user_id,
    )
    exception = _candidate_exception(candidate.id, user_id, approved_by=reviewer_id)

    updated = repo.record_verification(
        candidate.id, VerificationState.VERIFIED, actor_id=user_id,
        reason="verified under a recorded exception", sod_exception_id=exception,
    )
    assert updated.verification == VerificationState.VERIFIED


def test_a_self_approved_exception_is_refused(
    repo: CandidateRepository, run_id: str, user_id: str
) -> None:
    """`approved_by` is a plain foreign key, so nothing in the schema stops an actor recording an
    exception permitting themselves. That is self-approval with an extra step."""
    candidate = repo.capture(
        run_id=run_id, headline="Self-approved exception", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=user_id,
    )
    exception = _candidate_exception(candidate.id, user_id, approved_by=user_id)

    with pytest.raises(SelfVerificationError, match="approved by the same person"):
        repo.record_verification(
            candidate.id, VerificationState.VERIFIED, actor_id=user_id,
            reason="mine", sod_exception_id=exception,
        )


def test_a_lapsed_exception_does_not_authorise_verification(
    repo: CandidateRepository, run_id: str, user_id: str, reviewer_id: str
) -> None:
    candidate = repo.capture(
        run_id=run_id, headline="Lapsed", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=user_id,
    )
    exception = _candidate_exception(
        candidate.id, user_id, approved_by=reviewer_id, review_date=date(2020, 1, 1)
    )

    with pytest.raises(SelfVerificationError, match="lapsed"):
        repo.record_verification(
            candidate.id, VerificationState.VERIFIED, actor_id=user_id,
            reason="stale", sod_exception_id=exception,
        )


def test_an_exception_for_another_candidate_does_not_transfer(
    repo: CandidateRepository, run_id: str, user_id: str, reviewer_id: str
) -> None:
    """An exception authorises one act. Cited against a different candidate it must refuse rather
    than becoming a standing permission to self-verify."""
    first = repo.capture(
        run_id=run_id, headline="Has an exception", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=user_id,
    )
    second = repo.capture(
        run_id=run_id, headline="Does not", source_id=None, url=None, summary=None,
        published_at=None, in_coverage_window=None, actor_id=user_id,
    )
    exception = _candidate_exception(first.id, user_id, approved_by=reviewer_id)

    with pytest.raises(SelfVerificationError, match="does not cover"):
        repo.record_verification(
            second.id, VerificationState.VERIFIED, actor_id=user_id,
            reason="reusing", sod_exception_id=exception,
        )
