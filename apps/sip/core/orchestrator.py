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
        if not self.approver or not self.approver.strip():
            raise ValueError("HumanDecision requires a non-blank approver")
        if not self.decision or not self.decision.strip():
            raise ValueError("HumanDecision requires a non-blank decision")


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
    """

    def __init__(self, state: RunState = RunState.DRAFT) -> None:
        # Name-mangled so state only changes through advance(); a holder of the object cannot
        # assign a new state or splice history to bypass the transition guards.
        self.__state = _as_state(state)
        self.__history: list[TransitionRecord] = []

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
        allowed = _LEGAL.get(current, frozenset())
        if not allowed:
            raise RunTerminated(f"{current.value} is terminal; no transition to {target.value}")
        if target not in allowed:
            raise IllegalTransition(
                f"{current.value} -> {target.value} is not an allowed transition"
            )
        if (current, target) in _HUMAN_GATED and human_decision is None:
            raise HumanGateRequired(
                f"{current.value} -> {target.value} requires a recorded human decision"
            )

        record = TransitionRecord(
            from_state=current,
            to_state=target,
            actor=actor,
            at=datetime.now(timezone.utc),
            human_decision=human_decision,
        )
        self.__history.append(record)
        self.__state = target
        return record


def is_human_gated(from_state: RunState, to_state: RunState) -> bool:
    """True if this transition needs a recorded human decision. Exposed so an agent planner can
    tell, before proposing, whether it may act alone or must hand off to a human.
    """
    return (from_state, to_state) in _HUMAN_GATED
