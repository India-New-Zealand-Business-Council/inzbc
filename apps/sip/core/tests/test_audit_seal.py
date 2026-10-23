"""Signed human decisions and the sealed agent audit log (Studio 6 W6 change)."""

from __future__ import annotations

import dataclasses
from datetime import timedelta

import pytest

from apps.sip.core.agent_loop import replay_agent_audit
from apps.sip.core.audit_seal import (
    SigningKeyError,
    audit_chain_head,
    decision_signature_valid,
    seal_audit,
    seal_valid,
    sign_decision,
    signing_key_from_env,
)
from apps.sip.core.eval._fixtures import (
    MEASUREMENT_KEY,
    agent_at,
    redaction_policy,
    source_lookup,
)
from apps.sip.core.eval.replay_fidelity import execute, generate
from apps.sip.core.orchestrator import CorruptHistory, HumanDecision, TransitionRecord
from apps.sip.pipeline.models import RunState

KEY = MEASUREMENT_KEY
QA, CEO = RunState.QA_IN_PROGRESS, RunState.AWAITING_CEO_DECISION


def _sig(**overrides: object) -> str:
    fields = {"run_id": "RUN-1", "from_state": QA, "to_state": CEO, "approver": "qa-lead",
              "decision": "QA pass", "note": None, **overrides}
    return sign_decision(KEY, **fields)  # type: ignore[arg-type]


def test_a_signature_verifies_only_for_its_own_run_transition_and_decision() -> None:
    signature = _sig()
    good = {"run_id": "RUN-1", "from_state": QA, "to_state": CEO, "approver": "qa-lead",
            "decision": "QA pass"}
    assert decision_signature_valid(KEY, signature, **good)
    for change in ({"run_id": "RUN-2"}, {"to_state": RunState.QA_FAILED},
                   {"approver": "someone-else"}, {"decision": "QA fail"}, {"note": "edited"}):
        assert not decision_signature_valid(KEY, signature, **{**good, **change})
    assert not decision_signature_valid(b"x" * 32, signature, **good)
    assert not decision_signature_valid(KEY, None, **good)


def test_keys_must_be_long_enough(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SigningKeyError):
        sign_decision(b"short", run_id="R", from_state=QA, to_state=CEO, approver="a",
                      decision="d")
    monkeypatch.delenv("SIP_DECISION_SIGNING_KEY", raising=False)
    assert signing_key_from_env() is None
    monkeypatch.setenv("SIP_DECISION_SIGNING_KEY", "too-short")
    with pytest.raises(SigningKeyError):
        signing_key_from_env()


def test_human_decision_refuses_a_malformed_signature() -> None:
    with pytest.raises(ValueError, match="64 lowercase hex"):
        HumanDecision(approver="CEO", decision="ok", signature="not-hex")
    HumanDecision(approver="CEO", decision="ok", signature=_sig())


def _sealed_run():
    agent = execute(generate(5, 1), key=KEY)
    audit, seal = agent.sealed_audit_log(KEY)
    return audit, seal


def test_a_sealed_signed_run_replays_with_the_key() -> None:
    with redaction_policy():
        audit, seal = _sealed_run()
        replayed = replay_agent_audit(audit, source_id_lookup=source_lookup(), signing_key=KEY,
                                      seal=seal)
    assert replayed.state is QA
    assert seal_valid(audit, seal, KEY)


def test_any_edit_changes_the_chain_head_including_metadata() -> None:
    with redaction_policy():
        audit, seal = _sealed_run()
    head = audit_chain_head(audit)
    edited = dataclasses.replace(
        audit, tool_records=(dataclasses.replace(audit.tool_records[0], reason="edited"),
                             *audit.tool_records[1:]))
    assert audit_chain_head(edited) != head
    assert not seal_valid(edited, seal, KEY)
    assert seal_audit(audit, KEY) == seal


@pytest.mark.parametrize("case", ["forged-with-decision", "reused-launch-signature",
                                  "missing-seal", "unsigned-launch"])
def test_keyed_replay_refuses_forged_or_unsealed_logs(case: str) -> None:
    with redaction_policy():
        audit, seal = _sealed_run()
        last = audit.transitions[-1]
        if case in {"forged-with-decision", "reused-launch-signature"}:
            decision = (audit.transitions[0].human_decision if case == "reused-launch-signature"
                        else HumanDecision(approver="CEO", decision="QA pass"))
            forged = TransitionRecord(from_state=QA, to_state=CEO, actor="sip-agent",
                                      at=last.at + timedelta(seconds=1), human_decision=decision)
            audit = dataclasses.replace(audit, transitions=(*audit.transitions, forged))
            # Even an attacker who could re-seal (they cannot without the key) is stopped by the
            # decision signature check that follows the seal.
            seal = seal_audit(audit, KEY)
        elif case == "missing-seal":
            seal = None
        else:
            unsigned = execute(generate(5, 1))  # launch decision recorded without a signature
            audit, seal = unsigned.audit_log(), seal_audit(unsigned.audit_log(), KEY)
        with pytest.raises(CorruptHistory):
            replay_agent_audit(audit, source_id_lookup=source_lookup(), signing_key=KEY,
                               seal=seal)


def test_the_agent_still_cannot_cross_a_gate_when_signing_is_on() -> None:
    # Signing changes what a forged log can get past replay, not what the agent can do: it holds
    # no key and never builds a HumanDecision.
    with redaction_policy():
        agent = agent_at(QA)
        from apps.sip.core.agent_loop import parse_tool_proposal
        from apps.sip.core.eval._fixtures import proposal
        with pytest.raises(Exception):  # noqa: B017 - any refusal; the state is what matters
            agent.execute_proposal(parse_tool_proposal(
                proposal("advance_state", {"target_state": "Awaiting CEO Decision"})))
    assert agent.state is QA
