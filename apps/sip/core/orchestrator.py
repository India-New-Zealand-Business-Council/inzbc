"""SIP-184 run orchestrator: the fail-closed core of the agentic daily run.

The daily run is a fixed SOP with a strict state machine (schemas/state-machine.md) and mandatory
human gates. This module is the *only* path that mutates run state. An LLM agent may propose the
next action, but it proposes through `Orchestrator.advance` - it cannot bypass it. Legality, the
human gates, and the terminal `Stopped` state are enforced here in code, not by the model, so no
model output (or prompt injection) can skip a gate, distribute without a decision, or resurrect a
stopped run.

This first slice is the transition engine + audit trail. The LLM tool-use loop (scan, score,
verify) layers on top: each tool runs, then the agent proposes a transition that this engine
accepts or refuses. Every accepted transition appends an immutable `TransitionRecord`, so a run
is deterministically replayable from its audit log.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType

from apps.sip.pipeline.models import RunState

# Legal transitions, transcribed from schemas/state-machine.md. A target not listed for the
# current state is rejected - there is no implicit "skip a gate" path. Wrapped read-only
# (MappingProxyType) so in-process code cannot widen the table after import.
_LEGAL: MappingProxyType[RunState, frozenset[RunState]] = MappingProxyType({
    RunState.DRAFT: frozenset({RunState.RUN_AUTHORISED}),
    RunState.RUN_AUTHORISED: frozenset({RunState.COVERAGE_LOCKED}),
    RunState.COVERAGE_LOCKED: frozenset({RunState.SCANNING}),
    RunState.SCANNING: frozenset({RunState.CANDIDATE_REVIEW}),
    RunState.CANDIDATE_REVIEW: frozenset({RunState.REPORT_DRAFTED}),
    RunState.REPORT_DRAFTED: frozenset({RunState.QA_IN_PROGRESS}),
    RunState.QA_IN_PROGRESS: frozenset({RunState.AWAITING_CEO_DECISION, RunState.QA_FAILED}),
    RunState.QA_FAILED: frozenset({RunState.REPORT_DRAFTED}),
    RunState.AWAITING_CEO_DECISION: frozenset(
        {
            RunState.APPROVED_FOR_MANUAL_DISTRIBUTION,
            RunState.CONTINUE,
            RunState.CONTINUE_WITH_CORRECTION,
            RunState.PAUSED,
            RunState.STOPPED,
        }
    ),
    RunState.APPROVED_FOR_MANUAL_DISTRIBUTION: frozenset({RunState.DISTRIBUTED}),
    RunState.DISTRIBUTED: frozenset({RunState.CLOSED}),
    RunState.PAUSED: frozenset({RunState.COVERAGE_LOCKED}),
    # Terminal / no outbound transitions in this slice.
    RunState.STOPPED: frozenset(),
    RunState.CLOSED: frozenset(),
    RunState.CONTINUE: frozenset(),
    RunState.CONTINUE_WITH_CORRECTION: frozenset(),
    RunState.CORRECTED: frozenset(),
    RunState.WITHDRAWN: frozenset(),
})

# Transitions that require a recorded human decision. The agent can drive the mechanical
# collection steps on its own, but it can never cross one of these gates: the caller must supply a
# `HumanDecision` (an approver + the decision), or the transition fails closed.
_HUMAN_GATED: frozenset[tuple[RunState, RunState]] = frozenset(
    {
        (RunState.DRAFT, RunState.RUN_AUTHORISED),  # launch authority + version check
        (RunState.QA_IN_PROGRESS, RunState.AWAITING_CEO_DECISION),  # QA sign-off
        (RunState.QA_IN_PROGRESS, RunState.QA_FAILED),  # recorded Critical finding
        (RunState.QA_FAILED, RunState.REPORT_DRAFTED),  # correction + re-review only (spec)
        (RunState.AWAITING_CEO_DECISION, RunState.APPROVED_FOR_MANUAL_DISTRIBUTION),  # CEO decision
        (RunState.AWAITING_CEO_DECISION, RunState.CONTINUE),
        (RunState.AWAITING_CEO_DECISION, RunState.CONTINUE_WITH_CORRECTION),
        (RunState.AWAITING_CEO_DECISION, RunState.PAUSED),
        (RunState.AWAITING_CEO_DECISION, RunState.STOPPED),
        (RunState.APPROVED_FOR_MANUAL_DISTRIBUTION, RunState.DISTRIBUTED),  # manual send recorded
        (RunState.PAUSED, RunState.COVERAGE_LOCKED),  # recorded resumption approval
    }
)


def _as_state(value: RunState | str) -> RunState:
    """Coerce to a `RunState`. An unknown value is an illegal transition target, not a crash."""
    try:
        return RunState(value)
    except ValueError as error:
        raise IllegalTransition(f"unknown run state {value!r}") from error


class IllegalTransition(RuntimeError):
    """The proposed target is not reachable from the current state (schemas/state-machine.md)."""


class HumanGateRequired(RuntimeError):
    """A human-gated transition was attempted without a recorded decision. Fails closed rather
    than letting the agent cross a gate on its own.
    """


class RunTerminated(RuntimeError):
    """A transition was attempted from a terminal state (Stopped is terminal for that run id;
    Closed/Withdrawn are end states). Never resurrect a stopped run under the same id.
    """


@dataclass(frozen=True)
class HumanDecision:
    """A recorded human action authorising a gated transition. Validated at construction so a
    blank/placeholder decision cannot exist and then satisfy a gate: the gate checks presence, so
    presence must mean a real, attributable decision.
    """

    approver: str
    decision: str
    note: str | None = None

    def __post_init__(self) -> None:
        _require_non_blank(self)


def _require_non_blank(decision: HumanDecision) -> None:
    """Raise if approver or decision is blank/missing. Used both at construction and again at the
    gate, so a decision built by bypassing __init__ still cannot satisfy a gate with empty fields.
    """
    approver = decision.approver
    verdict = decision.decision
    if not isinstance(approver, str) or not approver.strip():
        raise ValueError("HumanDecision requires a non-blank approver")
    if not isinstance(verdict, str) or not verdict.strip():
        raise ValueError("HumanDecision requires a non-blank decision")


def _check_transition(
    current: RunState, target: RunState, human_decision: HumanDecision | None
) -> None:
    """Every rule a transition must satisfy, in one place.

    Shared by `advance` and `from_history` deliberately. Replay that re-implemented these checks
    would be a second opinion about the state machine, and the two would drift: a history could
    then be accepted on resume that `advance` would have refused live, which is precisely the hole
    rehydration must not open.
    """
    if human_decision is not None:
        # A gate is satisfied by presence, so presence must mean a real, validated decision.
        # Exact-type (not isinstance): a subclass could override __post_init__ to skip the
        # blank-field validation and still pass the gate.
        if type(human_decision) is not HumanDecision:
            raise TypeError("human_decision must be a HumanDecision")
        # Re-validate the fields at the point of use, not just at construction: a decision built
        # by bypassing __init__ (object.__new__ + object.__setattr__) would carry blank fields;
        # checking here means a blank decision is refused however it was made.
        _require_non_blank(human_decision)
    allowed = _LEGAL.get(current, frozenset())
    if not allowed:
        raise RunTerminated(f"{current.value} is terminal; no transition to {target.value}")
    if target not in allowed:
        raise IllegalTransition(f"{current.value} -> {target.value} is not an allowed transition")
    if (current, target) in _HUMAN_GATED and human_decision is None:
        raise HumanGateRequired(
            f"{current.value} -> {target.value} requires a recorded human decision"
        )


class CorruptHistory(RuntimeError):
    """A persisted history could not be replayed, so the run's state cannot be established.

    Its own type because the caller's options differ from a live transition failure. An
    `IllegalTransition` during normal operation means the caller asked for the wrong thing and can
    ask again; this means the stored record of what happened does not describe a run that could
    have happened, and no retry fixes that.
    """


@dataclass(frozen=True)
class TransitionRecord:
    """One immutable audit entry. The ordered list of these is the run's replayable history."""

    from_state: RunState
    to_state: RunState
    actor: str
    at: datetime
    human_decision: HumanDecision | None = None


class Orchestrator:
    """Holds a run's current state and its append-only transition history. `advance` is the only
    mutation. Construct at `Draft` (or resume by replaying recorded transitions).

    Threat model: this enforces the state machine against its *callers* - the agent proposing a
    structured transition, and eventually the HTTP layer. It does not, and cannot, defend against
    arbitrary code running in the same Python process: such code can reach the mangled attributes
    (`_Orchestrator__state`) via `object.__setattr__`, `ctypes`, or the gc, and could equally call
    the model client or read the environment directly - at that point the whole process is
    compromised regardless of this class. Defence against untrusted in-process code is process
    isolation plus the append-only persistence/audit layer (the DB is the real source of truth),
    not an in-language guard. What this class guarantees is that no *legitimate call path* - no
    proposal an agent can make through `advance` - can skip a gate. The `__setattr__` seal below
    stops the casual `orch._Orchestrator__state = ...` write; it is a speed bump, not the boundary.
    """

    __slots__ = (
        "_Orchestrator__history",
        "_Orchestrator__run_id",
        "_Orchestrator__sealed",
        "_Orchestrator__state",
    )

    def __init__(self, state: RunState = RunState.DRAFT, *, run_id: str | None = None) -> None:
        object.__setattr__(self, "_Orchestrator__state", _as_state(state))
        object.__setattr__(self, "_Orchestrator__history", [])
        object.__setattr__(self, "_Orchestrator__run_id", run_id)
        object.__setattr__(self, "_Orchestrator__sealed", True)

    @classmethod
    def from_history(
        cls, records: Iterable[TransitionRecord], *, run_id: str | None = None
    ) -> Orchestrator:
        """Rebuilds a run from its persisted transitions, or refuses (#116).

        **Why this is not `Orchestrator(state=X)`.** That constructor drops the run at a state with
        no evidence it legally arrived there, which is fine for a test fixture and wrong for
        resuming a real run: a process restart would otherwise be a way to place a run in any state
        at all, gates included. Replay is the check. The class docstring already promised "resume
        by replaying recorded transitions" and nothing implemented it.

        **The original records are kept, not re-derived.** Replaying through `advance` would work
        and would stamp `datetime.now()` on every entry, silently rewriting when each transition
        happened, so a restart would relabel the whole trail as having occurred at boot. Actors and
        human decisions carry across for the same reason: the history is evidence, and evidence
        that changes on reload is not evidence.

        **What it refuses**, each raising `CorruptHistory`:

        - A chain that does not join up. Every record's `from_state` must equal the state its
          predecessor left the run in, which is what catches a reordered or missing entry.
        - A first record that does not start at `Draft`. Every run begins there, so a history
          starting anywhere else is missing its beginning rather than describing a different run.
        - Any transition the state machine would refuse live, including a gated one with no
          recorded decision. The rules come from `_check_transition`, the same function `advance`
          uses, so a history cannot be accepted on resume that would have been refused at the time.
        """
        orchestrator = cls(run_id=run_id)
        for index, record in enumerate(records):
            if type(record) is not TransitionRecord:
                raise CorruptHistory(
                    f"history entry {index} is a {type(record).__name__}, not a TransitionRecord"
                )
            current = orchestrator.state
            if record.from_state is not current:
                raise CorruptHistory(
                    f"history entry {index} starts at {record.from_state.value!r} but the run is "
                    f"at {current.value!r}. The chain does not join up, so the record is missing "
                    "an entry or its entries are out of order."
                )
            try:
                _check_transition(current, record.to_state, record.human_decision)
            except (IllegalTransition, HumanGateRequired, RunTerminated, TypeError) as error:
                raise CorruptHistory(
                    f"history entry {index} ({record.from_state.value} -> "
                    f"{record.to_state.value}) is not a transition this run could have made: "
                    f"{error}"
                ) from error
            orchestrator.__history.append(record)
            object.__setattr__(orchestrator, "_Orchestrator__state", record.to_state)
        return orchestrator

    @property
    def run_id(self) -> str | None:
        """Which run this is, when it was rehydrated from one. `None` for a fresh in-memory run."""
        return self.__run_id

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(
            "Orchestrator state is sealed; use advance() to change it, not attribute assignment"
        )

    @property
    def state(self) -> RunState:
        return self.__state

    @property
    def history(self) -> tuple[TransitionRecord, ...]:
        return tuple(self.__history)

    def advance(
        self,
        target: RunState,
        *,
        actor: str,
        human_decision: HumanDecision | None = None,
    ) -> TransitionRecord:
        """Move to `target` if legal and (when gated) a `human_decision` is present. Appends and
        returns the audit record. Raises `RunTerminated`, `IllegalTransition`, or
        `HumanGateRequired` and leaves the state unchanged otherwise. `target` is coerced to a
        `RunState`; an unknown value raises `IllegalTransition`, never a stray type error.
        """
        target = _as_state(target)
        current = self.__state
        _check_transition(current, target, human_decision)

        record = TransitionRecord(
            from_state=current,
            to_state=target,
            actor=actor,
            at=datetime.now(timezone.utc),
            human_decision=human_decision,
        )
        # __history is mutated in place (list.append), not reassigned, so the __setattr__ seal is
        # not involved. __state is reassigned via object.__setattr__ because the seal blocks the
        # normal `self.__state = ...` path (that block is what stops external writes).
        self.__history.append(record)
        object.__setattr__(self, "_Orchestrator__state", target)
        return record


def is_human_gated(from_state: RunState, to_state: RunState) -> bool:
    """True if this transition needs a recorded human decision. Exposed so an agent planner can
    tell, before proposing, whether it may act alone or must hand off to a human.
    """
    return (from_state, to_state) in _HUMAN_GATED


def is_legal_transition(from_state: RunState, to_state: RunState) -> bool:
    """True if `to_state` is reachable from `from_state` per the state machine
    (`schemas/state-machine.md`). Exposed so any caller that writes `runs.state` directly - not
    only `Orchestrator.advance` - can refuse an illegal jump against the one table this module
    already maintains, instead of re-deriving or duplicating it (`services/api/persistence.py`'s
    `apply_transition` is the first such caller: a persistence layer must not become a second way
    to reach a state the orchestrator itself would refuse).
    """
    return to_state in _LEGAL.get(from_state, frozenset())
