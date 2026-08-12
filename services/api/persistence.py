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

from apps.sip.core.orchestrator import (
    CorruptHistory,
    HumanDecision,
    IllegalTransition,
    Orchestrator,
    TransitionRecord,
    is_human_gated,
    is_legal_transition,
)
from apps.sip.pipeline.models import RunState
from services.api.audit import record_audit


# The two human gates that happen before a report version exists, so ADR-0005's decision streams
# (all keyed to `report_version_id`) cannot record them. They are verified against
# `run_authorisations`, which is keyed to the run, and this maps each gate to the kind of authority
# that covers it (#227).
#
# A mapping rather than a set, because knowing a transition is run-level is not enough: the check
# has to require the *right* kind. A resumption authorisation cited to authorise a launch would
# otherwise pass, and "somebody authorised something about this run" is not the claim the state
# change makes.
_RUN_LEVEL_GATES: dict[tuple[RunState, RunState], str] = {
    (RunState.DRAFT, RunState.RUN_AUTHORISED): "Launch",
    (RunState.PAUSED, RunState.COVERAGE_LOCKED): "Resumption",
}


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

    def list_runs(self) -> list[RunRecord]:
        """Every run, most recently created first.

        No filter/pagination yet - the UI's only current need (#120) is a full list to render.
        Add both once a caller actually needs to page or filter by state, rather than guessing
        the shape now.
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            rows = conn.execute(
                f"select {_SELECT_COLUMNS} from runs order by created_at desc"
            ).fetchall()
        return [_row_to_record(row) for row in rows]

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
                # Two tables, because the two kinds of gate happen at different points in the run.
                #
                # The report-level gates are checked against `decision_records`, which is keyed to
                # a report version. The run-level gates are launch and resumption authority, which
                # happen before any report version exists, so they are checked against
                # `run_authorisations` instead (#227). Until that table existed, `approval_ref` for
                # those two was unverifiable free text: the only two gates deciding whether a run
                # may run at all accepted anything a caller typed.
                #
                # Both comparisons are made as text, not cast to uuid. `approval_ref` is
                # caller-supplied, and comparing it against a uuid column raises a type error for
                # anything that is not one. Free text is exactly what this refuses, so it has to
                # come back as a refusal with a reason rather than an opaque database error.
                gate = _RUN_LEVEL_GATES.get((current_state, new_state))
                if gate is not None:
                    # Matched on run and kind as well as id, so an authorisation belonging to
                    # another run, or a resumption cited to authorise a launch, does not count. An
                    # authorisation covers one act, not a category - the same rule the
                    # separation-of-duties exceptions follow.
                    authorised = conn.execute(
                        "select 1 from run_authorisations "
                        "where id::text = %s and run_id = %s and kind = %s",
                        (approval_ref, run_id, gate),
                    ).fetchone()
                    if authorised is None:
                        raise HumanGateNotSatisfied(
                            f"approval_ref {approval_ref!r} is not a {gate.lower()} authorisation "
                            f"for run {run_id}. Free text cannot authorise a gated transition, and "
                            "an authorisation for another run or another gate is not an "
                            "authorisation for this one. run_authorisations is append-only, so a "
                            "reference into it cannot later be edited to say something else."
                        )
                else:
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


@dataclass(frozen=True)
class AuditEntry:
    """One `audit_log` row, as the read endpoint returns it.

    `at` is an ISO-8601 string rather than a `datetime` for the same reason `RunRecord` stringifies
    its coverage window: this crosses an HTTP boundary, and one conversion in the adapter beats one
    in every caller.
    """

    id: int
    at: str
    user_id: str | None
    action: str
    record_type: str | None
    record_id: str | None
    old_value: str | None
    new_value: str | None
    reason: str | None
    approval_ref: str | None


_AUDIT_COLUMNS = (
    "id, at, user_id, action, record_type, record_id, old_value, new_value, reason, approval_ref"
)


class AuditRepository:
    """Read access to `audit_log`. Reads only: this class has no write method by design.

    Writes go through `services/api/audit.py`'s `record_audit`, which takes the caller's open
    connection so the audit row and the mutation it describes share one transaction. A write method
    here would open its own, which is exactly the thing that must not happen.
    """

    def __init__(self, database_url: str | None = None):
        self._database_url = database_url or os.environ["DATABASE_URL"]

    def for_run(self, run_id: str, *, limit: int = 100, before_id: int | None = None
                ) -> list[AuditEntry]:
        """The audit trail for one run, newest first.

        **Ordered by `id`, not by `at`.** `at` defaults to `now()`, which in Postgres is the
        transaction start time, so two rows written in the same transaction share a timestamp and
        their relative order is undefined. `id` is a `bigserial`, so it is unique and monotonic,
        and the one question this endpoint exists to answer is what happened in what order.

        **Keyset pagination, not OFFSET.** The trail is append-only, so nothing is inserted between
        existing rows and a cursor stays valid: `before_id` is the last id the caller saw. OFFSET
        would be correct here too, but it re-scans on every page and it teaches a pattern that
        breaks on a table where rows can appear mid-sequence.

        Filtered on `record_id` and `record_type = 'runs'`. `record_id` is text and holds ids from
        several tables, so matching on it alone would return a candidate that happened to share a
        uuid string.
        """
        # Bounded server-side. A caller asking for everything gets the maximum rather than an
        # unbounded scan, because the honest failure of an unbounded read is a timeout under the
        # exact conditions that make the trail worth reading.
        limit = max(1, min(limit, 500))
        clauses = ["record_type = 'runs'", "record_id = %s"]
        params: list[object] = [run_id]
        if before_id is not None:
            clauses.append("id < %s")
            params.append(before_id)
        params.append(limit)

        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            rows = conn.execute(
                f"select {_AUDIT_COLUMNS} from audit_log where {' and '.join(clauses)} "
                f"order by id desc limit %s",
                tuple(params),
            ).fetchall()
        return [
            AuditEntry(
                id=row["id"],
                at=row["at"].isoformat(),
                user_id=str(row["user_id"]) if row["user_id"] else None,
                action=row["action"],
                record_type=row["record_type"],
                record_id=row["record_id"],
                old_value=row["old_value"],
                new_value=row["new_value"],
                reason=row["reason"],
                approval_ref=row["approval_ref"],
            )
            for row in rows
        ]

    def rehydrate(self, run_id: str) -> Orchestrator:
        """Rebuilds the run's orchestrator from its stored transitions (#116).

        This is what makes `Orchestrator.from_history` reachable rather than a function with no
        caller. The database is the source of truth; the orchestrator is the in-memory view of it,
        and a restart should reconstruct that view from the record rather than trusting
        `runs.state`.

        **Why not read `runs.state` and construct at it.** That column says where the run *is*,
        with no evidence it legally arrived. Replaying the transitions checks every step against
        the same rules `advance` enforces live, so a run whose stored trail does not describe a
        journey it could have made is refused rather than resumed. That is the difference between
        restoring a state and restoring a *run*.

        **The gate decisions are not reconstructed, and this is a real limit.** `approval_ref`
        names where the decision lives; it does not carry who approved what, and this method does
        not follow it. A gated row missing it is refused rather than replayed, so the reference is
        checked for presence and not for meaning: nothing here confirms it still resolves to a live
        row in `decision_records` or `run_authorisations`, only that `apply_transition` verified it
        when the transition was made. Rebuilding a faithful `HumanDecision` means joining those
        tables per transition. Until that exists, a gated transition replays with a decision
        carrying the recorded actor and the approval reference, which is
        enough to satisfy the gate and honest about being a summary of the real record rather than
        the record itself.

        Ordered oldest first, because replay runs forwards. Raises `KeyError` for an unknown run,
        matching `get_run`, and `CorruptHistory` when the stored trail does not describe a journey
        the run could have made.
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            # The run has to exist before its history means anything. Without this, an unknown id
            # replayed to an empty history and came back as a perfectly valid Draft orchestrator,
            # so a typo produced a run rather than an error. `create_run` writes the row and its
            # `run.create` audit entry in one transaction, so a run that exists always has one.
            known = conn.execute(
                "select 1 from runs where id = %s", (run_id,)
            ).fetchone()
            if known is None:
                raise KeyError(f"no run {run_id!r}")
            rows = conn.execute(
                "select user_id, at, old_value, new_value, reason, approval_ref from audit_log "
                "where record_type = 'runs' and record_id = %s and action = 'run.transition' "
                "order by id asc",
                (run_id,),
            ).fetchall()

        records = []
        for row in rows:
            from_state = RunState(row["old_value"])
            to_state = RunState(row["new_value"])
            decision = None
            if is_human_gated(from_state, to_state):
                # Refuse rather than fabricate. `apply_transition` will not commit a gated
                # transition without an `approval_ref` it has verified against `decision_records`
                # or `run_authorisations`, so a stored row missing one was not written by that
                # path. Filling the gap with a placeholder would manufacture the decision the gate
                # exists to require, and replay would then wave through exactly the history that
                # proves something went wrong.
                if not row["approval_ref"] or not row["user_id"]:
                    raise CorruptHistory(
                        f"the recorded {from_state.value} -> {to_state.value} transition on run "
                        f"{run_id!r} is human gated but names no approval reference or actor. A "
                        "gated transition cannot be replayed from a row that does not say who "
                        "authorised it."
                    )
                decision = HumanDecision(
                    approver=str(row["user_id"]),
                    decision=str(row["approval_ref"]),
                    note=row["reason"],
                )
            records.append(
                TransitionRecord(
                    from_state=from_state,
                    to_state=to_state,
                    actor=str(row["user_id"]) if row["user_id"] else "unknown",
                    at=row["at"],
                    human_decision=decision,
                )
            )
        return Orchestrator.from_history(records, run_id=run_id)


@dataclass(frozen=True)
class OpenAction:
    """One `action_register` row the dashboard shows. Read-only, like everything on that screen."""

    action_code: str
    title: str
    owner: str | None
    priority: str | None
    due_date: str | None
    status: str
    overdue: bool


@dataclass(frozen=True)
class DashboardSummary:
    """Everything the executive dashboard reads, in one shape (#47).

    `run` is `None` when no run exists, which is a real state the UI renders rather than an error.

    `by_verification` always carries every verification state, including the ones at zero. A state
    absent from the map would force the UI to know the full enum to render the panel, which is the
    coupling this endpoint exists to remove.
    """

    run: RunRecord | None
    total_candidates: int
    included_candidates: int
    by_verification: dict[str, int]
    open_actions: list[OpenAction]


# Every verification state, from `database/schema.sql`. Listed so a state with no candidates is
# reported as 0 rather than omitted: `GROUP BY` returns no row for a value nothing matches, and a
# missing key and a zero mean different things to the panel reading them.
VERIFICATION_STATES = (
    "Verified",
    "Partially Verified",
    "Unverified",
    "Not Required",
    "Rejected",
)


class DashboardRepository:
    """Read-only aggregate for the executive dashboard. No write method, by design."""

    def __init__(self, database_url: str | None = None):
        self._database_url = database_url or os.environ["DATABASE_URL"]

    def summary(self) -> DashboardSummary:
        """The current run, its candidate coverage, and the open actions.

        **Counted in SQL rather than in Python.** The dashboard already did this client-side by
        fetching every candidate over HTTP and tallying them; doing the same thing server-side
        would move the waste rather than remove it. A run with two thousand candidates should cost
        one aggregate, not two thousand rows.

        **The current run is the most recently created**, matching `list_runs`. That is a
        convention rather than a fact about the domain: there is no `is_current` column, and if two
        runs are ever open at once this picks one of them silently. Worth a real answer before the
        dashboard is used to make a decision.

        **Overdue is computed by the database**, not by the caller, so a client with a wrong clock
        cannot make an action look on time.
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            run_row = conn.execute(
                f"select {_SELECT_COLUMNS} from runs order by created_at desc limit 1"
            ).fetchone()

            counts = {state: 0 for state in VERIFICATION_STATES}
            total = 0
            included = 0
            if run_row is not None:
                for row in conn.execute(
                    "select verification::text as verification, count(*) as n, "
                    "count(*) filter (where included) as included "
                    "from candidates where run_id = %s group by verification",
                    (run_row["id"],),
                ).fetchall():
                    # A verification value outside the enum cannot occur (the column is the enum
                    # type), so an unexpected key here would mean the enum changed without this
                    # list. Recorded rather than silently dropped.
                    counts[row["verification"]] = row["n"]
                    total += row["n"]
                    included += row["included"]

            action_rows = conn.execute(
                "select a.action_code, a.title, a.priority, a.due_date, a.status, "
                "       coalesce(u.name, a.owner_text) as owner, "
                "       (a.due_date is not null and a.due_date < current_date) as overdue "
                "from action_register a left join users u on u.id = a.owner_id "
                "where a.closed_at is null "
                # Overdue first, then by due date, nulls last: an action with no due date is not
                # more urgent than one that is late, and ordering by due_date alone puts nulls
                # first in Postgres.
                "order by overdue desc, a.due_date asc nulls last, a.action_code asc"
            ).fetchall()

        return DashboardSummary(
            run=_row_to_record(run_row) if run_row is not None else None,
            total_candidates=total,
            included_candidates=included,
            by_verification=counts,
            open_actions=[
                OpenAction(
                    action_code=row["action_code"],
                    title=row["title"],
                    owner=row["owner"],
                    priority=row["priority"],
                    due_date=row["due_date"].isoformat() if row["due_date"] else None,
                    status=row["status"],
                    overdue=row["overdue"],
                )
                for row in action_rows
            ],
        )
