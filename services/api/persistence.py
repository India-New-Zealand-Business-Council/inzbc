"""Postgres persistence adapter for SIP runs, with optimistic concurrency (#117).

`apps.sip.core.orchestrator.Orchestrator` is the in-memory transition engine and defines the
human gates (`HumanDecision`, `is_human_gated`). This module used to leave enforcement to it,
which meant the guarantee held only inside that one process: nothing reaching the database went
through the orchestrator, so `Draft -> Run Authorised` committed with no decision behind it and
the durable record claimed an authorisation that never happened. A gated transition here now
requires `approval_ref` to name a row in `decision_records`, which is append-only, so the
evidence cannot later be edited into saying something else. It also refuses an illegal state jump (`orchestrator.is_legal_transition`) before writing: a
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

from apps.sip.core.orchestrator import IllegalTransition, is_human_gated, is_legal_transition
from apps.sip.pipeline.models import RunState
from services.api.audit import record_audit


# The two human gates that happen before a report version exists, so ADR-0005's decision streams
# (all keyed to `report_version_id`) cannot record them. Launch authority and resumption authority
# have no home in the model yet, so `approval_ref` for these two cannot be verified against
# anything. See #227.
_RUN_LEVEL_GATES: frozenset[tuple[RunState, RunState]] = frozenset(
    {
        (RunState.DRAFT, RunState.RUN_AUTHORISED),
        (RunState.PAUSED, RunState.COVERAGE_LOCKED),
    }
)


class HumanGateNotSatisfied(RuntimeError):
    """Raised when a human-gated transition is attempted with no decision record behind it.

    Fail closed. The in-memory orchestrator has always refused these, but that guarantee lived in
    one process and every durable write went around it.
    """


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
        """Inserts a new run in `Draft` state at `version=0`, with its audit row.

        Creating a run is a state-changing write and was not audited, while `services/api/README.md`
        said every state-changing write is. The trail therefore began at the first transition, so
        the one fact it could never answer was who started the run.
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                f"insert into runs (run_number, prompt_version, coverage_start_utc, "
                f"coverage_end_utc, initiated_by) values (%s, %s, %s, %s, %s) "
                f"returning {_SELECT_COLUMNS}",
                (run_number, prompt_version, coverage_start_utc, coverage_end_utc, initiated_by),
            ).fetchone()
            # Same connection, before the single commit, so the run and its audit row land together
            # or not at all.
            record_audit(
                conn,
                user_id=initiated_by,
                action="run.create",
                record_type="runs",
                record_id=str(row["id"]),
                new_value=RunState.DRAFT.value,
                reason=f"run {run_number} created",
            )
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
        self,
        run_id: str,
        expected_version: int,
        new_state: RunState,
        *,
        actor_id: str,
        reason: str,
        approval_ref: str | None = None,
    ) -> RunRecord:
        """Commits `new_state` iff the row is still at `expected_version` (compare-and-swap) AND
        `new_state` is reachable from the row's current state per the state machine
        (`orchestrator.is_legal_transition`, the same table `Orchestrator.advance` enforces).

        Writes the transition's audit row (`old_value`/`new_value`/`reason`/`approval_ref`, actor
        `actor_id`) inside this same transaction via `record_audit`, so the state change and its
        audit record commit together or not at all (#118) — there is no window in which a run moved
        with no record of who moved it or why. `actor_id` and `reason` are required precisely
        because an audit row without them cannot be reconstructed later. `approval_ref` is required for
        a human-gated transition and must name an existing `decision_records` row; it stays optional
        for the mechanical transitions the agent drives on its own.

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

            # A human-gated move needs evidence a human made it, and the evidence has to be a
            # decision that exists rather than a string somebody typed.
            #
            # This layer used to check legality only. `Draft -> Run Authorised` is legal, so it
            # committed with `approval_ref` left NULL, and the durable record then said the run was
            # authorised with nothing anywhere showing that anyone authorised it. The in-memory
            # orchestrator refuses that, but nothing reaching the database went through the
            # orchestrator, so the guarantee stopped at the boundary of the process that held it.
            if is_human_gated(current_state, new_state):
                if not approval_ref:
                    raise HumanGateNotSatisfied(
                        f"{current_state.value!r} -> {new_state.value!r} is human gated and needs "
                        "approval_ref. A durable state saying the run was authorised, with no "
                        "record of the authorisation, is worse than refusing the move."
                    )
                # Only the report-level gates can be checked against `decision_records`, because
                # that table is keyed to a report version. The run-level gates are launch and
                # resumption authority, which happen before any report version exists, so ADR-0005's
                # three streams have nowhere to record them. That is a real gap in the model rather
                # than something to paper over with a looser check here: until it has a home,
                # approval_ref for those two is unverifiable free text. Tracked as #227.
                if (current_state, new_state) not in _RUN_LEVEL_GATES:
                    # Compared as text, not cast to uuid: `approval_ref` is caller-supplied, and
                    # comparing against a uuid column raises a type error for anything that is not
                    # one. Free text is exactly what this refuses, so it has to come back as a
                    # refusal with a reason rather than an opaque database error.
                    decided = conn.execute(
                        "select 1 from decision_records where id::text = %s", (approval_ref,)
                    ).fetchone()
                    if decided is None:
                        raise HumanGateNotSatisfied(
                            f"approval_ref {approval_ref!r} is not a decision record. Free text "
                            "cannot authorise a gated transition; decision_records is append-only, "
                            "so a reference into it cannot later be edited to say something else."
                        )

            row = conn.execute(
                f"update runs set state = %s, version = version + 1 "
                f"where id = %s and version = %s "
                f"returning {_SELECT_COLUMNS}",
                (new_state.value, run_id, expected_version),
            ).fetchone()
            # Audit only a transition that actually landed. A 0-row CAS result (row is None) means
            # another writer won the race between the version read above and this update; nothing
            # changed, so there is nothing to audit. Written before commit and on this same
            # connection so it shares the update's transaction: if the audit insert fails, the
            # connection context manager rolls back and the state change is undone with it.
            if row is not None:
                record_audit(
                    conn,
                    user_id=actor_id,
                    action="run.transition",
                    record_type="runs",
                    record_id=run_id,
                    old_value=current_state.value,
                    new_value=new_state.value,
                    reason=reason,
                    approval_ref=approval_ref,
                )
            conn.commit()
        if row is None:
            raise ConcurrentModificationError(
                f"run {run_id!r} was not at version {expected_version} - another transition "
                "committed first; re-read the run before retrying"
            )
        return _row_to_record(row)
