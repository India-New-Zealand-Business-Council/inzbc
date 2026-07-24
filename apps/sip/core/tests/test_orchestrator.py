"""Fail-closed guarantees of the SIP-184 run orchestrator.

These lock the properties that must hold no matter what an agent proposes: no gate-skipping, no
crossing a human gate without a recorded decision, and no resurrecting a stopped run.
"""

from __future__ import annotations

import pytest

from apps.sip.core.orchestrator import (
    HumanDecision,
    HumanGateRequired,
    IllegalTransition,
    Orchestrator,
    RunTerminated,
    is_human_gated,
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
    orch.advance(RunState.REPORT_DRAFTED, actor="agent")
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
    assert not is_human_gated(RunState.COVERAGE_LOCKED, RunState.SCANNING)
