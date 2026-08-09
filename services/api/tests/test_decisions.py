"""Integration tests for the decision repository (#125), against a real Postgres.

Skipped without `DATABASE_URL`, same as the run-persistence tests: a mock would prove this module
calls psycopg correctly, not that the append-only contract holds against real constraints and real
concurrency, which is the whole point.
"""

from __future__ import annotations

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime

import psycopg
import pytest

from services.api.decisions import (
    CEO_RULING,
    DISTRIBUTION_AUTHORITY,
    REPORT_APPROVAL,
    DecisionConflictError,
    DecisionNotPermittedError,
    DecisionRejected,
    DecisionRepository,
)

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - decision tests need a real Postgres with schema.sql applied",
)

SIP_OWNER_ROLE = 1


@pytest.fixture
def repo() -> DecisionRepository:
    return DecisionRepository(DATABASE_URL)


@pytest.fixture
def seeded() -> dict:
    """A submitted report version plus the actor and permissions needed to decide on it.

    Seeded directly rather than through app code: none of this is the repository's concern, and
    building it through other modules would couple these tests to their bugs.
    """
    with psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row) as conn:
        conn.execute(
            "insert into roles (id, name) values (%s, 'SIP Owner') on conflict do nothing",
            (SIP_OWNER_ROLE,),
        )
        user = conn.execute(
            "insert into users (name, email) values (%s, %s) returning id",
            (f"CEO {uuid.uuid4()}", f"{uuid.uuid4()}@example.test"),
        ).fetchone()
        conn.execute(
            "insert into user_roles (user_id, role_id) values (%s, %s) "
            "on conflict (user_id, role_id) do update set enabled = true",
            (user["id"], SIP_OWNER_ROLE),
        )
        # No row here means nobody may decide, so every kind needs one. Fail-closed by design.
        for kind in (CEO_RULING, REPORT_APPROVAL, DISTRIBUTION_AUTHORITY):
            # `do update`, not `do nothing`: these rows are keyed on (kind, role) and shared
            # across tests, so a test that disables one would leak into every test after it.
            conn.execute(
                "insert into decision_role_permissions (kind, actor_role_id) values (%s, %s) "
                "on conflict (kind, actor_role_id) do update set enabled = true",
                (kind, SIP_OWNER_ROLE),
            )
        run = conn.execute(
            "insert into runs (run_number, coverage_start_utc, coverage_end_utc, prompt_version, "
            "initiated_by) values (%s, %s, %s, %s, %s) returning id",
            (f"RUN-DEC-{uuid.uuid4().hex[:10]}", "2026-07-29T00:00Z", "2026-07-30T00:00Z",
             "SIP-050 v1.1", user["id"]),
        ).fetchone()
        version = conn.execute(
            "insert into report_versions (run_id, version_number, created_by, created_by_role_id, "
            "content_sha256, created_at) values (%s, 1, %s, %s, %s, now()) returning id",
            (run["id"], user["id"], SIP_OWNER_ROLE, "a" * 64),
        ).fetchone()
        conn.commit()
    return {"user_id": str(user["id"]), "report_version_id": str(version["id"])}


def _kwargs(seeded: dict, **overrides) -> dict:
    base = {
        "report_version_id": seeded["report_version_id"],
        "actor_id": seeded["user_id"],
        "actor_role_id": SIP_OWNER_ROLE,
        "reason": "recorded by the integration test",
        "evidence_ref": "SIP-184 s12",
        "owner_id": seeded["user_id"],
        "next_review": date(2026, 9, 1),
        "decided_at": datetime.now(UTC),
        "idempotency_key": uuid.uuid4(),
        "expected_head_revision": 0,
    }
    base.update(overrides)
    return base


def test_submission_opens_three_undecided_streams(repo: DecisionRepository, seeded: dict) -> None:
    current = repo.current(seeded["report_version_id"])
    assert current.ceo_ruling is None
    assert current.report_approval is None
    assert current.distribution_authority is None


def test_an_explicit_refusal_reads_back_differently_from_undecided(
    repo: DecisionRepository, seeded: dict
) -> None:
    """The defect the old mutable `approvals` row could not avoid.

    Its `distribution` column defaulted to `Not Authorised`, so a CEO who said no and a run nobody
    had looked at were the same row.
    """
    before = repo.current(seeded["report_version_id"])
    assert before.distribution_authority is None

    repo.record(**_kwargs(seeded, kind=DISTRIBUTION_AUTHORITY, value="Not Authorised",
                          distribution_recipient="ceo@example.test"))

    after = repo.current(seeded["report_version_id"])
    assert after.distribution_authority == "Not Authorised"


def test_a_correction_supersedes_rather_than_overwriting(
    repo: DecisionRepository, seeded: dict
) -> None:
    first = repo.record(**_kwargs(seeded, kind=CEO_RULING, value="Pause"))
    second = repo.record(**_kwargs(seeded, kind=CEO_RULING, value="Continue",
                                   expected_head_revision=1))

    assert second.stream_revision == first.stream_revision + 1
    assert repo.current(seeded["report_version_id"]).ceo_ruling == "Continue"

    # The superseded record is still there. Append-only means the history survives the correction.
    with psycopg.connect(DATABASE_URL) as conn:
        kept = conn.execute(
            "select value from decision_records where id = %s", (first.id,)
        ).fetchone()
    assert kept is not None and kept[0] == "Pause"


def test_a_value_the_kind_cannot_carry_is_refused(
    repo: DecisionRepository, seeded: dict
) -> None:
    # 'Approved' belongs to the report-approval stream, not the CEO ruling.
    with pytest.raises(DecisionRejected):
        repo.record(**_kwargs(seeded, kind=CEO_RULING, value="Approved"))


def test_distribution_authority_requires_a_recipient(
    repo: DecisionRepository, seeded: dict
) -> None:
    # Both yes and no are decisions about a concrete recipient. Without one there is no way to say
    # what was authorised, or refused, and to whom.
    with pytest.raises(DecisionRejected):
        repo.record(**_kwargs(seeded, kind=DISTRIBUTION_AUTHORITY, value="Authorised"))


def test_an_unpermitted_role_cannot_decide(repo: DecisionRepository, seeded: dict) -> None:
    """No `decision_role_permissions` row means nobody may act in that capacity.

    This used to surface as a foreign-key violation, which refused the write but only as a side
    effect of the constraint. The writer now checks first and says why, so the refusal is the
    control rather than a collision with one.
    """
    with psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row) as conn:
        conn.execute("insert into roles (id, name) values (9, 'Board Viewer') on conflict do nothing")
        conn.execute(
            "insert into user_roles (user_id, role_id) values (%s, 9) on conflict do nothing",
            (seeded["user_id"],),
        )
        conn.commit()

    with pytest.raises(DecisionNotPermittedError):
        repo.record(**_kwargs(seeded, kind=CEO_RULING, value="Continue", actor_role_id=9))


def test_two_concurrent_decisions_on_one_stream_cannot_both_commit(
    repo: DecisionRepository, seeded: dict
) -> None:
    """The acceptance property: a decision built on a head that has since moved must not land.

    Both threads target the same stream and the same legal value, released together by a barrier,
    so neither can win by simply starting first. One commits; the other must be told the stream
    moved, not silently applied on top of a ruling it never read.
    """
    start = threading.Barrier(2)

    read_at = repo.current(seeded["report_version_id"]).revisions[CEO_RULING]

    def decide() -> object:
        thread_repo = DecisionRepository(DATABASE_URL)
        start.wait()  # both decided against `read_at`; only one may land
        try:
            return thread_repo.record(**_kwargs(seeded, kind=CEO_RULING, value="Continue",
                                                expected_head_revision=read_at))
        except DecisionConflictError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = [f.result() for f in [pool.submit(decide), pool.submit(decide)]]

    conflicts = [o for o in outcomes if isinstance(o, DecisionConflictError)]
    committed = [o for o in outcomes if not isinstance(o, Exception)]
    assert len(committed) == 1, f"expected exactly one to commit, got {outcomes}"
    assert len(conflicts) == 1

    # And exactly one record is current, at revision 1.
    with psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row) as conn:
        heads = conn.execute(
            "select head_revision from decision_streams ds "
            "join report_versions rv on rv.id = ds.report_version_id "
            "where rv.id = %s and ds.kind = %s",
            (seeded["report_version_id"], CEO_RULING),
        ).fetchone()
    assert heads["head_revision"] == 1


def test_deciding_on_an_unsubmitted_version_raises_key_error(repo: DecisionRepository) -> None:
    with pytest.raises(KeyError):
        repo.current(str(uuid.uuid4()))


def test_a_disabled_permission_refuses_the_decision(repo, seeded) -> None:
    """`enabled = false` must actually revoke.

    The foreign key on decision_records matches `(kind, actor_role_id)` only, so it proves a
    permission row exists and never looks at `enabled`. `database/schema.sql` says as much and says
    the writing command must check it. It did not, so revoking a permission the documented way
    changed nothing at all and the decision still landed.
    """
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "update decision_role_permissions set enabled = false "
            "where kind = %s and actor_role_id = %s",
            (CEO_RULING, SIP_OWNER_ROLE),
        )
        conn.commit()

    with pytest.raises(DecisionNotPermittedError):
        repo.record(**_kwargs(seeded, kind=CEO_RULING, value="Continue",
                              expected_head_revision=0))


def test_a_disabled_role_assignment_refuses_the_decision(repo, seeded) -> None:
    """Holding the role once is not holding it now."""
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "update user_roles set enabled = false where user_id = %s and role_id = %s",
            (seeded["user_id"], SIP_OWNER_ROLE),
        )
        conn.commit()

    with pytest.raises(DecisionNotPermittedError):
        repo.record(**_kwargs(seeded, kind=CEO_RULING, value="Continue",
                              expected_head_revision=0))


def test_an_inactive_account_refuses_the_decision(repo, seeded) -> None:
    """A departed staff member's account must not still be able to authorise a release."""
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("update users set active = false where id = %s", (seeded["user_id"],))
        conn.commit()

    with pytest.raises(DecisionNotPermittedError):
        repo.record(**_kwargs(seeded, kind=CEO_RULING, value="Continue",
                              expected_head_revision=0))


def test_current_pairs_each_value_with_the_revision_it_was_read_at(repo, seeded) -> None:
    """The revision has to describe the value returned beside it.

    Values and head revisions used to be read in two statements. Under READ COMMITTED each takes
    its own snapshot, so a decision committing between them returned the ruling from before the
    write paired with the revision from after it. Passing that revision back satisfied the
    compare-and-swap, and the correction superseded a ruling nobody had seen.

    One statement cannot disagree with itself, so this asserts the pairing directly.
    """
    repo.record(**_kwargs(seeded, kind=CEO_RULING, value="Continue", expected_head_revision=0))

    first = repo.current(seeded["report_version_id"])
    assert first.ceo_ruling == "Continue"
    assert first.revisions[CEO_RULING] == 1

    repo.record(**_kwargs(seeded, kind=CEO_RULING, value="Pause",
                          expected_head_revision=first.revisions[CEO_RULING]))

    second = repo.current(seeded["report_version_id"])
    assert second.ceo_ruling == "Pause"
    assert second.revisions[CEO_RULING] == 2
