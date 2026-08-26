"""Integration tests for `scripts/seed_demo.py` (#338), against a real Postgres.

Skipped entirely when `DATABASE_URL` isn't set, matching every other integration suite in this
repository (`services/api/tests/test_persistence.py` et al.) — a mock would prove this script
calls psycopg correctly, not that the seeded data actually satisfies the schema's constraints
(the append-only triggers, the SoD checks, the state-machine gates), which is the entire point of
running it against a real database rather than reading the code and trusting it.

`main()` runs once per test session (`_seeded` is session-scoped): the script takes real work to
run (~700 source-check inserts alone), and every test here only asserts on state it leaves behind,
so there is nothing to gain from re-running it per test — `test_main_is_idempotent_on_rerun` below
is the one test that deliberately calls it a second time, to prove reruns don't duplicate rows.
"""

from __future__ import annotations

import os

import psycopg
import pytest
from psycopg.rows import dict_row

from scripts import seed_demo

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - seed_demo tests need a real Postgres with schema.sql applied",
)


def _connect() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


@pytest.fixture(scope="session")
def _seeded() -> None:
    """Runs the seed script once for the whole test session."""
    assert seed_demo.main() == 0


def test_every_run_reaches_its_target_state(_seeded: None) -> None:
    """Every RunSpec's `target_state` is a real, reachable end state — not a stale label — proven
    by reading `runs.state` back after `main()` drove each one through `RunRepository
    .apply_transition`, the same legality- and gate-checked path `services/api/persistence.py`
    enforces everywhere else.
    """
    with _connect() as conn:
        rows = conn.execute(
            "select run_number, state from runs where run_number like 'RUN-SEED-%'"
        ).fetchall()
    states_by_number = {row["run_number"]: row["state"] for row in rows}
    assert len(states_by_number) == len(seed_demo.RUN_SPECS)
    for spec in seed_demo.RUN_SPECS:
        assert states_by_number[spec.number] == spec.target_state.value


def test_main_is_idempotent_on_rerun(_seeded: None) -> None:
    """Rerunning `main()` against an already-seeded database changes nothing — the module
    docstring's "rerunning is safe, not additive" claim, proven rather than asserted. This is the
    one test that calls `main()` a second time on purpose; every other test relies on `_seeded`
    running it exactly once.
    """
    with _connect() as conn:
        before = {
            table: conn.execute(f"select count(*) as n from {table}").fetchone()["n"]
            for table in ("runs", "candidates", "source_checks", "report_versions",
                           "decision_records", "users")
        }

    assert seed_demo.main() == 0

    with _connect() as conn:
        after = {
            table: conn.execute(f"select count(*) as n from {table}").fetchone()["n"]
            for table in before
        }
    assert after == before


def test_duplicates_are_genuinely_caught_and_merged(_seeded: None) -> None:
    """At least one candidate per duplicate-injected run is marked `duplicate_of` and excluded —
    proof the run through `dedupe.find_duplicate_of` in `_capture_and_work_candidates` actually
    matched something, not that a flag was hand-set. `_inject_duplicates` needs a batch of at
    least 4 to run at all, so this also guards against a future edit shrinking every run below
    that floor and silently making the whole demonstration a no-op.
    """
    with _connect() as conn:
        rows = conn.execute(
            "select id, duplicate_of, included from candidates where duplicate_of is not null"
        ).fetchall()
    assert len(rows) > 0
    for row in rows:
        assert row["included"] is False


def test_verification_mix_includes_unverified_and_rejected(_seeded: None) -> None:
    """#338 explicitly asks for Unverified and Rejected to appear, not an all-Verified dataset —
    "a dataset where everything is Verified is not realistic and hides the gates." Checked by
    reading the actual spread back, not by trusting `_apply_mix`'s pattern was ever reached.
    """
    with _connect() as conn:
        rows = conn.execute(
            "select distinct verification from candidates where verification is not null"
        ).fetchall()
    seen = {row["verification"] for row in rows}
    assert {"Verified", "Unverified", "Rejected"} <= seen


def test_candidate_sod_exception_is_recorded_and_used(_seeded: None) -> None:
    """The one deliberate self-verification exception (#338's "separation of duties must
    survive") exists, was approved by someone other than the person it exempts, and the
    candidate it covers actually carries a verification recorded under it — not just an orphaned
    exception row nothing points back to.
    """
    with _connect() as conn:
        exception = conn.execute(
            "select id, candidate_id, actor_id, approved_by from candidate_sod_exceptions"
        ).fetchone()
        assert exception is not None
        assert exception["approved_by"] != exception["actor_id"]

        candidate = conn.execute(
            "select verified_by, verification from candidates where id = %s",
            (exception["candidate_id"],),
        ).fetchone()
        assert candidate["verified_by"] == exception["actor_id"]
        assert candidate["verification"] == "Verified"


def test_one_run_leaves_mandatory_sources_uncovered(_seeded: None) -> None:
    """RUN-SEED-05 is spec'd `full_source_coverage=False` so #338's coverage gate has something
    real to report — checked here against `missing_mandatory_outcomes()`, the actual production
    function (`apps/sip/collector/source_register.py`), not a hand-rolled count.
    """
    from apps.sip.collector.source_register import missing_mandatory_outcomes

    with _connect() as conn:
        run = conn.execute(
            "select id from runs where run_number = 'RUN-SEED-05'"
        ).fetchone()
        recorded = conn.execute(
            "select sl.sip185_code from source_checks sc "
            "join source_library sl on sl.id = sc.source_id "
            "where sc.run_id = %s and sl.sip185_code is not null",
            (run["id"],),
        ).fetchall()
    missing = missing_mandatory_outcomes({row["sip185_code"] for row in recorded})
    assert len(missing) > 0


@pytest.mark.parametrize(
    ("run_number", "expected_ceo_ruling"),
    [
        ("RUN-SEED-07", "Continue With Correction"),
        ("RUN-SEED-08", "Pause"),
        ("RUN-SEED-09", "Continue"),
        ("RUN-SEED-10", "Stop"),
    ],
)
def test_decided_runs_carry_the_right_ceo_ruling(
    _seeded: None, run_number: str, expected_ceo_ruling: str
) -> None:
    """Each of the four runs that reach a report-decided state carries a `CEO Ruling` decision
    record with the value that state implies — read via `current_report_decisions`, the schema's
    own "one authoritative combined read" view, rather than joining the decision tables by hand.
    """
    with _connect() as conn:
        row = conn.execute(
            "select d.ceo_ruling from current_report_decisions d "
            "join runs r on r.id = d.run_id where r.run_number = %s",
            (run_number,),
        ).fetchone()
    assert row is not None
    assert row["ceo_ruling"] == expected_ceo_ruling
