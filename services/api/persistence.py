"""Postgres persistence adapter for SIP runs, with optimistic concurrency (#117).

`apps.sip.core.orchestrator.Orchestrator` is the in-memory transition engine and owns the human
gates (`HumanDecision`, `is_human_gated`) — this module does not re-implement those. It does,
however, refuse an illegal state jump (`orchestrator.is_legal_transition`) before writing: a
persistence layer that trusts every caller to have already checked legality is a second way to
reach a state the orchestrator would refuse, not a durability concern. This module is the separate
concern of making an accepted transition *durable*, and doing so safely when two reviewers might
act on the same run at the same time.

Optimistic concurrency (not row locking): `runs.version` (`database/schema.sql`) increments on
every committed transition. `apply_transition` writes with `WHERE version = expected_version`; a
0-row result means someone else's transition landed first, and raises rather than silently
overwriting it or blocking on a held lock. A daily-run system with low write volume and occasional
long human-gate pauses (Awaiting CEO Decision can sit for hours) is a poor fit for `SELECT ... FOR
UPDATE`, which would hold a transaction (and a connection) open for however long a human takes to
decide.

No connection pooling here - each method opens and closes its own connection. This module has no
long-lived state; a `RunRepository` instance is safe to construct per request or reuse freely.
Pooling can be added later (e.g. psycopg_pool) without changing this module's public shape.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

from apps.sip.core.orchestrator import IllegalTransition, is_legal_transition
from apps.sip.pipeline.models import RunState


class ConcurrentModificationError(RuntimeError):
    """Raised when `apply_transition`'s `expected_version` no longer matches the stored row.

    The caller must re-fetch the run (`get_run`) and decide whether its intended transition is
    still legal against the run's *current* state - not blindly retry the same write, which could
    silently apply a transition the current state no longer permits.
    """


@dataclass(frozen=True)
class RunRecord:
    """A `runs` row. `version` is required on every write path precisely so a caller cannot
    forget to pass it - `apply_transition` has no "just overwrite" mode.
    """

    id: str
    run_number: str
    state: RunState
    version: int
    prompt_version: str
    coverage_start_utc: str
    coverage_end_utc: str
    initiated_by: str


_SELECT_COLUMNS = (
    "id, run_number, state, version, prompt_version, "
    "coverage_start_utc, coverage_end_utc, initiated_by"
)


def _row_to_record(row: dict) -> RunRecord:
    return RunRecord(
        id=str(row["id"]),
        run_number=row["run_number"],
        state=RunState(row["state"]),
        version=row["version"],
        prompt_version=row["prompt_version"],
        coverage_start_utc=row["coverage_start_utc"].isoformat(),
        coverage_end_utc=row["coverage_end_utc"].isoformat(),
        initiated_by=str(row["initiated_by"]),
    )


class RunRepository:
    """Postgres-backed persistence for `runs`. See module docstring for the concurrency contract."""

    def __init__(self, database_url: str | None = None):
        # Read at construction, not at import time, so tests can point different instances at
        # different databases without environment-variable ordering games.
        self._database_url = database_url or os.environ["DATABASE_URL"]

    def create_run(
        self,
        run_number: str,
        prompt_version: str,
        coverage_start_utc: str,
        coverage_end_utc: str,
        initiated_by: str,
    ) -> RunRecord:
        """Inserts a new run in `Draft` state at `version=0`."""
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                f"insert into runs (run_number, prompt_version, coverage_start_utc, "
                f"coverage_end_utc, initiated_by) values (%s, %s, %s, %s, %s) "
                f"returning {_SELECT_COLUMNS}",
                (run_number, prompt_version, coverage_start_utc, coverage_end_utc, initiated_by),
            ).fetchone()
            conn.commit()
        return _row_to_record(row)

    def get_run(self, run_id: str) -> RunRecord:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                f"select {_SELECT_COLUMNS} from runs where id = %s", (run_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"no run {run_id!r}")
        return _row_to_record(row)

    def apply_transition(
        self, run_id: str, expected_version: int, new_state: RunState
    ) -> RunRecord:
        """Commits `new_state` iff the row is still at `expected_version` (compare-and-swap) AND
        `new_state` is reachable from the row's current state per the state machine
        (`orchestrator.is_legal_transition`, the same table `Orchestrator.advance` enforces).

        The legality check reads the current state, then the CAS write still guards against a
        race: if another transition lands between the read and the write, `version` will have
        moved and the write affects zero rows regardless of what the legality check saw - it
        cannot commit a state built on a stale read. `version` only ever increases, so there is no
        ABA hazard from reusing an old value.

        This exists because `apply_transition` used to trust every caller to have already checked
        legality (`Orchestrator.advance`'s job, per this method's original docstring) - but nothing
        stopped a direct caller from committing an illegal jump like `Draft -> Closed` with no
        state in between, skipping every human gate. Layering the checks does not mean only the
        top layer has to hold; a write path this close to the database still has to refuse what it
        knows is illegal.

        Raises:
            `KeyError` if `run_id` doesn't exist - distinct from `ConcurrentModificationError`
            (a stale version on a row that does exist), so a caller can tell 404 from 409.
            `ConcurrentModificationError` when the row has moved past `expected_version`, checked
            before legality: a stale caller holds an old state too, so judging its move against the
            row's current state answers a question it never asked. Also raised on a 0-row CAS
            result, which is the same conflict seen a moment later - both callers read the same
            version, then Postgres re-evaluates `version = %s` after the winner commits.
            `IllegalTransition` if `new_state` isn't reachable from the current state, checked
            once the caller is known to be current.
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            current = conn.execute(
                f"select {_SELECT_COLUMNS} from runs where id = %s", (run_id,)
            ).fetchone()
            if current is None:
                raise KeyError(f"no run {run_id!r}")

            # Staleness is checked before legality, and the order matters. A caller that lost a
            # race is holding an old state as well as an old version, so judging its transition
            # against the row's *current* state answers a question it never asked. Two threads
            # racing the same legal move is the clearest case: the loser reads the winner's
            # committed state and gets told 'Run Authorised' -> 'Run Authorised' is illegal, when
            # what actually happened is that its version went stale and it should re-read and
            # retry. Checking legality first also made that a timing-dependent test failure,
            # because the answer depended on whether the loser's read landed before or after the
            # winner's commit.
            if current["version"] != expected_version:
                raise ConcurrentModificationError(
                    f"run {run_id!r} was not at version {expected_version} - another transition "
                    "committed first; re-read the run before retrying"
                )

            current_state = RunState(current["state"])
            if not is_legal_transition(current_state, new_state):
                raise IllegalTransition(
                    f"{current_state.value!r} -> {new_state.value!r} is not a legal transition "
                    "per schemas/state-machine.md"
                )

            row = conn.execute(
                f"update runs set state = %s, version = version + 1 "
                f"where id = %s and version = %s "
                f"returning {_SELECT_COLUMNS}",
                (new_state.value, run_id, expected_version),
            ).fetchone()
            conn.commit()
        if row is None:
            raise ConcurrentModificationError(
                f"run {run_id!r} was not at version {expected_version} - another transition "
                "committed first; re-read the run before retrying"
            )
        return _row_to_record(row)
