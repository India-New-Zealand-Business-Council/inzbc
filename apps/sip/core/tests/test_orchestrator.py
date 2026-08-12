"""Fail-closed guarantees of the SIP-184 run orchestrator.

These lock the properties that must hold no matter what an agent proposes: no gate-skipping, no
crossing a human gate without a recorded decision, and no resurrecting a stopped run.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from apps.sip.core.orchestrator import (
    CorruptHistory,
    HumanDecision,
    HumanGateRequired,
    IllegalTransition,
    Orchestrator,
    RunTerminated,
    TransitionRecord,
    is_human_gated,
    is_legal_transition,
)
from apps.sip.pipeline.models import RunState

CEO = HumanDecision(approver="CEO", decision="Approved for manual distribution")


def _authorised_run() -> Orchestrator:
    orch = Orchestrator()
    orch.advance(RunState.RUN_AUTHORISED, actor="operator", human_decision=HumanDecision("CEO", "authorise"))
    return orch


def test_agent_can_drive_the_mechanical_collection_steps() -> None:
    orch = _authorised_run()
    for target in [
        RunState.COVERAGE_LOCKED,
        RunState.SCANNING,
        RunState.CANDIDATE_REVIEW,
        RunState.REPORT_DRAFTED,
        RunState.QA_IN_PROGRESS,
    ]:
        orch.advance(target, actor="agent")
    assert orch.state is RunState.QA_IN_PROGRESS
    assert len(orch.history) == 6


def test_illegal_transition_is_rejected() -> None:
    orch = Orchestrator()
    with pytest.raises(IllegalTransition):
        orch.advance(RunState.DISTRIBUTED, actor="agent")  # Draft -> Distributed skips every gate
    assert orch.state is RunState.DRAFT  # unchanged


def test_authority_gate_requires_a_human_decision() -> None:
    orch = Orchestrator()
    with pytest.raises(HumanGateRequired):
        orch.advance(RunState.RUN_AUTHORISED, actor="agent")  # no decision supplied
    assert orch.state is RunState.DRAFT


def test_agent_cannot_cross_the_ceo_distribution_gate_alone() -> None:
    orch = _authorised_run()
    for target in [
        RunState.COVERAGE_LOCKED,
        RunState.SCANNING,
        RunState.CANDIDATE_REVIEW,
        RunState.REPORT_DRAFTED,
        RunState.QA_IN_PROGRESS,
    ]:
        orch.advance(target, actor="agent")
    orch.advance(RunState.AWAITING_CEO_DECISION, actor="qa", human_decision=HumanDecision("Reviewer", "QA pass"))
    # The agent tries to authorise distribution itself.
    with pytest.raises(HumanGateRequired):
        orch.advance(RunState.APPROVED_FOR_MANUAL_DISTRIBUTION, actor="agent")
    assert orch.state is RunState.AWAITING_CEO_DECISION
    # With a recorded CEO decision it is allowed.
    orch.advance(RunState.APPROVED_FOR_MANUAL_DISTRIBUTION, actor="operator", human_decision=CEO)
    assert orch.state is RunState.APPROVED_FOR_MANUAL_DISTRIBUTION


def test_stopped_run_is_terminal() -> None:
    orch = _authorised_run()
    for target in [
        RunState.COVERAGE_LOCKED,
        RunState.SCANNING,
        RunState.CANDIDATE_REVIEW,
        RunState.REPORT_DRAFTED,
        RunState.QA_IN_PROGRESS,
    ]:
        orch.advance(target, actor="agent")
    orch.advance(RunState.AWAITING_CEO_DECISION, actor="qa", human_decision=HumanDecision("Reviewer", "QA pass"))
    orch.advance(RunState.STOPPED, actor="operator", human_decision=HumanDecision("CEO", "Stop"))
    with pytest.raises(RunTerminated):
        orch.advance(RunState.COVERAGE_LOCKED, actor="agent")  # cannot resurrect
    assert orch.state is RunState.STOPPED


def test_qa_failed_routes_back_to_report_drafted_not_distribution() -> None:
    orch = _authorised_run()
    for target in [
        RunState.COVERAGE_LOCKED,
        RunState.SCANNING,
        RunState.CANDIDATE_REVIEW,
        RunState.REPORT_DRAFTED,
        RunState.QA_IN_PROGRESS,
    ]:
        orch.advance(target, actor="agent")
    orch.advance(RunState.QA_FAILED, actor="qa", human_decision=HumanDecision("Reviewer", "Critical finding"))
    # A QA-failed run cannot jump to distribution; it must go back for correction.
    with pytest.raises(IllegalTransition):
        orch.advance(RunState.APPROVED_FOR_MANUAL_DISTRIBUTION, actor="agent")
    # And the agent cannot loop it back to Report Drafted alone - that needs a recorded re-review.
    with pytest.raises(HumanGateRequired):
        orch.advance(RunState.REPORT_DRAFTED, actor="agent")
    orch.advance(RunState.REPORT_DRAFTED, actor="reviewer", human_decision=HumanDecision("Reviewer", "Re-review after correction"))
    assert orch.state is RunState.REPORT_DRAFTED


def test_history_is_append_only_and_replayable() -> None:
    orch = _authorised_run()
    orch.advance(RunState.COVERAGE_LOCKED, actor="agent")
    states = [r.to_state for r in orch.history]
    assert states == [RunState.RUN_AUTHORISED, RunState.COVERAGE_LOCKED]
    # Replaying the recorded transitions reproduces the same final state.
    replay = Orchestrator()
    for rec in orch.history:
        replay.advance(rec.to_state, actor=rec.actor, human_decision=rec.human_decision)
    assert replay.state is orch.state


def test_is_human_gated_reports_gates() -> None:
    assert is_human_gated(RunState.DRAFT, RunState.RUN_AUTHORISED)
    assert is_human_gated(RunState.APPROVED_FOR_MANUAL_DISTRIBUTION, RunState.DISTRIBUTED)
    assert is_human_gated(RunState.QA_FAILED, RunState.REPORT_DRAFTED)
    assert not is_human_gated(RunState.COVERAGE_LOCKED, RunState.SCANNING)


def test_is_legal_transition_reports_the_state_machine_table() -> None:
    assert is_legal_transition(RunState.DRAFT, RunState.RUN_AUTHORISED)
    assert is_legal_transition(RunState.QA_IN_PROGRESS, RunState.AWAITING_CEO_DECISION)
    assert is_legal_transition(RunState.QA_IN_PROGRESS, RunState.QA_FAILED)
    # The exact case a caller writing runs.state directly (services/api/persistence.py) must
    # refuse: skipping straight to Closed with no CEO decision, approval, QA or distribution
    # record in between.
    assert not is_legal_transition(RunState.DRAFT, RunState.CLOSED)
    assert not is_legal_transition(RunState.STOPPED, RunState.RUN_AUTHORISED)  # terminal state


def test_is_legal_transition_returns_false_for_a_terminal_states_empty_set() -> None:
    # RunState.CLOSED's entry in _LEGAL is an explicit empty frozenset() (a terminal state, no
    # outbound transitions in this slice) - confirms the empty-set case reports False rather than
    # raising, distinct from a state missing from the table entirely (which .get() also handles).
    assert not is_legal_transition(RunState.CLOSED, RunState.CORRECTED)


@pytest.mark.parametrize("approver,decision", [("", "d"), ("   ", "d"), ("CEO", ""), ("CEO", "  ")])
def test_blank_human_decision_cannot_be_constructed(approver: str, decision: str) -> None:
    # A gate checks for a HumanDecision's presence, so a blank/placeholder one must not exist.
    with pytest.raises(ValueError):
        HumanDecision(approver=approver, decision=decision)


@pytest.mark.parametrize(
    "gate",
    [
        (RunState.DRAFT, RunState.RUN_AUTHORISED),
        (RunState.QA_IN_PROGRESS, RunState.AWAITING_CEO_DECISION),
        (RunState.QA_IN_PROGRESS, RunState.QA_FAILED),
        (RunState.QA_FAILED, RunState.REPORT_DRAFTED),
        (RunState.AWAITING_CEO_DECISION, RunState.APPROVED_FOR_MANUAL_DISTRIBUTION),
        (RunState.AWAITING_CEO_DECISION, RunState.CONTINUE),
        (RunState.AWAITING_CEO_DECISION, RunState.CONTINUE_WITH_CORRECTION),
        (RunState.AWAITING_CEO_DECISION, RunState.PAUSED),
        (RunState.AWAITING_CEO_DECISION, RunState.STOPPED),
        (RunState.APPROVED_FOR_MANUAL_DISTRIBUTION, RunState.DISTRIBUTED),
        (RunState.PAUSED, RunState.COVERAGE_LOCKED),
    ],
)
def test_every_human_gate_fails_closed_without_a_decision(gate: tuple[RunState, RunState]) -> None:
    frm, to = gate
    orch = Orchestrator(state=frm)
    with pytest.raises(HumanGateRequired):
        orch.advance(to, actor="agent")
    assert orch.state is frm


def test_state_cannot_be_mutated_outside_advance() -> None:
    # Name-mangling means there is no plain _state/_history to reassign; the guarded path is the
    # only way to change state.
    orch = Orchestrator()
    assert not hasattr(orch, "_state")
    assert not hasattr(orch, "_history")


def test_unknown_target_raises_illegal_not_typeerror() -> None:
    orch = Orchestrator()
    with pytest.raises(IllegalTransition):
        orch.advance("Not A State", actor="agent")  # type: ignore[arg-type]
    assert orch.state is RunState.DRAFT


class _FakeDecision:
    """A truthy object that is not a HumanDecision - must never satisfy a gate."""

    approver = "CEO"
    decision = "approve"


def test_fake_decision_object_cannot_satisfy_a_gate() -> None:
    orch = Orchestrator()
    with pytest.raises(TypeError):
        orch.advance(RunState.RUN_AUTHORISED, actor="agent", human_decision=_FakeDecision())  # type: ignore[arg-type]
    assert orch.state is RunState.DRAFT


def test_human_decision_subclass_that_skips_validation_is_refused() -> None:
    # A subclass could override __post_init__ to skip the blank-field checks; the exact-type gate
    # refuses it, so validation cannot be bypassed by subclassing.
    class _Sneaky(HumanDecision):
        def __post_init__(self) -> None:  # skips the blank-field validation
            pass

    sneaky = _Sneaky(approver="", decision="")
    orch = Orchestrator()
    with pytest.raises(TypeError):
        orch.advance(RunState.RUN_AUTHORISED, actor="agent", human_decision=sneaky)
    assert orch.state is RunState.DRAFT


def test_ungated_transition_advances_without_a_decision() -> None:
    # Guard against over-gating: Distributed -> Closed is not a human gate, so the agent advances
    # it with no decision.
    orch = Orchestrator(state=RunState.DISTRIBUTED)
    orch.advance(RunState.CLOSED, actor="agent")
    assert orch.state is RunState.CLOSED


def test_bypass_constructed_blank_decision_is_refused_at_the_gate() -> None:
    # A decision built by skipping __init__ (object.__new__ + object.__setattr__) carries blank
    # fields but is the exact HumanDecision type. The gate re-validates fields, so it is refused.
    sneaky = object.__new__(HumanDecision)
    object.__setattr__(sneaky, "approver", "")
    object.__setattr__(sneaky, "decision", "")
    object.__setattr__(sneaky, "note", None)
    orch = Orchestrator()
    with pytest.raises(ValueError):
        orch.advance(RunState.RUN_AUTHORISED, actor="agent", human_decision=sneaky)
    assert orch.state is RunState.DRAFT


def test_setattr_seal_blocks_direct_state_write() -> None:
    orch = Orchestrator()
    with pytest.raises(AttributeError):
        orch.state = RunState.DISTRIBUTED  # type: ignore[misc]
    with pytest.raises(AttributeError):
        orch._Orchestrator__state = RunState.DISTRIBUTED  # the mangled name is sealed too
    assert orch.state is RunState.DRAFT


def test_legal_table_is_read_only() -> None:
    from apps.sip.core import orchestrator as orch_mod

    with pytest.raises(TypeError):
        orch_mod._LEGAL[RunState.DRAFT] = frozenset({RunState.DISTRIBUTED})  # type: ignore[index]


def test_history_property_is_a_copy() -> None:
    orch = _authorised_run()
    snapshot = orch.history
    orch.advance(RunState.COVERAGE_LOCKED, actor="agent")
    # Mutating after the snapshot does not change the earlier tuple.
    assert len(snapshot) == 1
    assert len(orch.history) == 2


# ---------- rehydration (#116) ----------


def _replayable() -> Orchestrator:
    """A run that reached Coverage Locked through a gate, so replay has something to check."""
    orch = _authorised_run()
    orch.advance(RunState.COVERAGE_LOCKED, actor="agent")
    return orch


def test_from_history_rebuilds_the_state() -> None:
    original = _replayable()

    resumed = Orchestrator.from_history(original.history, run_id="RUN-1")

    assert resumed.state is original.state
    assert resumed.run_id == "RUN-1"


def test_from_history_keeps_the_original_records_rather_than_restamping_them() -> None:
    """The reason replay cannot just call `advance`.

    `advance` stamps `datetime.now()`, so replaying through it would relabel every transition as
    having happened at boot. A history whose timestamps change on reload is not evidence of
    anything, and this is a trail whose entire purpose is answering when something happened.
    """
    original = _replayable()

    resumed = Orchestrator.from_history(original.history)

    assert resumed.history == original.history
    assert [r.at for r in resumed.history] == [r.at for r in original.history]
    assert [r.actor for r in resumed.history] == [r.actor for r in original.history]
    assert resumed.history[0].human_decision == original.history[0].human_decision


def test_from_history_refuses_a_chain_that_does_not_join_up() -> None:
    """The check that catches a reordered or missing entry.

    Each record must start where its predecessor left the run. Without this, a history missing its
    middle would replay as though the run had jumped.
    """
    original = _replayable()
    reordered = tuple(reversed(original.history))

    with pytest.raises(CorruptHistory, match="does not join up"):
        Orchestrator.from_history(reordered)


def test_from_history_refuses_a_history_that_does_not_start_at_draft() -> None:
    """Every run begins at Draft, so a history starting elsewhere is missing its beginning."""
    original = _replayable()

    with pytest.raises(CorruptHistory):
        Orchestrator.from_history(original.history[1:])


def test_from_history_refuses_a_gated_transition_with_no_recorded_decision() -> None:
    """The property that makes replay a control rather than a formality.

    A restart must not be a way to arrive at a gated state without the decision that authorises
    it. `Orchestrator(state=...)` would allow exactly that, which is why resuming goes through
    here instead.
    """
    ungated = TransitionRecord(
        from_state=RunState.DRAFT,
        to_state=RunState.RUN_AUTHORISED,
        actor="agent",
        at=datetime(2026, 8, 13, tzinfo=timezone.utc),
        human_decision=None,
    )

    with pytest.raises(CorruptHistory, match="could have made"):
        Orchestrator.from_history([ungated])


def test_from_history_refuses_an_illegal_jump() -> None:
    """Draft straight to Distributed skips every gate in between."""
    jump = TransitionRecord(
        from_state=RunState.DRAFT,
        to_state=RunState.DISTRIBUTED,
        actor="agent",
        at=datetime(2026, 8, 13, tzinfo=timezone.utc),
        human_decision=CEO,
    )

    with pytest.raises(CorruptHistory, match="could have made"):
        Orchestrator.from_history([jump])


def test_from_history_refuses_something_that_is_not_a_transition_record() -> None:
    """Exact-type, for the same reason `advance` checks `HumanDecision` that way: a subclass could
    override validation and satisfy a check it should not."""
    with pytest.raises(CorruptHistory, match="TransitionRecord"):
        Orchestrator.from_history([{"from_state": "Draft", "to_state": "Run Authorised"}])


def test_an_empty_history_is_a_draft_run() -> None:
    """Not an error. A run created and not yet moved has no transitions, and refusing that would
    make the first resume after creation fail."""
    resumed = Orchestrator.from_history([])

    assert resumed.state is RunState.DRAFT
    assert resumed.history == ()


def test_a_rehydrated_run_can_still_advance() -> None:
    """Resume has to produce a working orchestrator, not a read-only snapshot."""
    resumed = Orchestrator.from_history(_replayable().history)

    resumed.advance(RunState.SCANNING, actor="agent")

    assert resumed.state is RunState.SCANNING
    assert len(resumed.history) == 3
