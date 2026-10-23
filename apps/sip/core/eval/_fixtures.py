"""Shared, model-free builders for the agent measurements.

The "model" here is a scripted queue of completions. For the attack suite that queue plays a
compromised or prompt-injected model: it returns exactly the output an attacker would want. That
is a stronger adversary than a real model, which only sometimes complies, so a block rate
measured this way is a lower bound on what the controls give against a real one.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace

from apps.sip.collector.source_lookup import SourceIdLookup
from apps.sip.collector.source_register import MANDATORY_SOURCES
from apps.sip.core.agent_loop import AgentOrchestrator, parse_tool_proposal
from apps.sip.core.orchestrator import HumanDecision, Orchestrator
from apps.sip.pipeline.models import RunState, SourceOutcome
from services.api.model_gateway import ModelGateway

WINDOW = ("2026-07-27T19:00:00+00:00", "2026-07-28T19:00:00+00:00")


@contextmanager
def redaction_policy() -> Iterator[None]:
    """The gateway refuses to run without a redaction policy, as production does."""
    if os.environ.get("REDACTION_POLICY_PATH"):
        yield
        return
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "policy.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "rules": [
                        {
                            "name": "email",
                            "pattern": r"[\w.+-]+@[\w-]+\.[\w.]+",
                            "replacement": "[redacted:email]",
                            "example": "mail someone@example.test",
                        }
                    ]
                },
                handle,
            )
        os.environ["REDACTION_POLICY_PATH"] = path
        try:
            yield
        finally:
            del os.environ["REDACTION_POLICY_PATH"]


def source_lookup() -> SourceIdLookup:
    return SourceIdLookup(
        {entry.source_id: f"db-{entry.source_id.lower()}" for entry in MANDATORY_SOURCES}
    )


def all_mandatory_outcomes() -> list[dict[str, str]]:
    return [
        {"source_id": entry.source_id, "outcome": SourceOutcome.NO_QUALIFYING_ITEM.value}
        for entry in MANDATORY_SOURCES
    ]


def scripted_gateway(outputs: list[str]) -> ModelGateway:
    """A gateway whose model returns `outputs` in order and raises once they run out."""
    queue = list(outputs)

    def create(**_kwargs: object) -> SimpleNamespace:
        if not queue:
            raise RuntimeError("scripted model has no more outputs")
        return SimpleNamespace(output_text=queue.pop(0))

    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    return ModelGateway(client=client, usage_sink=lambda _usage: None)


def proposal(tool: str, arguments: dict, reason: str = "Next SIP-184 step.") -> str:
    return json.dumps({"tool": tool, "arguments": arguments, "reason": reason})


def score_output(signal: str, *, nz: int = 4, india: int = 4, member: int = 4) -> str:
    return json.dumps(
        {
            "nz_relevance": nz,
            "india_relevance": india,
            "member_relevance": member,
            "signal": signal,
            "confidence": "High",
            "reason": "Scripted scoring output.",
        }
    )


def authorised_orchestrator(run_id: str) -> Orchestrator:
    """A run whose launch authority was recorded by a human, the only legal way in."""
    orchestrator = Orchestrator(run_id=run_id)
    orchestrator.advance(
        RunState.RUN_AUTHORISED,
        actor="sip-owner",
        human_decision=HumanDecision(approver="CEO", decision="Launch authorised"),
    )
    return orchestrator


# The mechanical steps, in order, that take an authorised run to each state. A scenario reaches
# its starting state through the agent's own tools, so the audit trail stays a real one.
_PREFIX: dict[RunState, list[str]] = {
    RunState.RUN_AUTHORISED: [],
    RunState.COVERAGE_LOCKED: [
        proposal(
            "lock_coverage_window",
            {"coverage_start_utc": WINDOW[0], "coverage_end_utc": WINDOW[1]},
        ),
    ],
}
_PREFIX[RunState.SCANNING] = [
    *_PREFIX[RunState.COVERAGE_LOCKED],
    proposal("advance_state", {"target_state": "Scanning"}),
]
_PREFIX[RunState.CANDIDATE_REVIEW] = [
    *_PREFIX[RunState.SCANNING],
    proposal("record_source_outcome", {"outcomes": all_mandatory_outcomes()}),
    proposal("fetch_candidates", {}),
    proposal("advance_state", {"target_state": "Candidate Review"}),
]
_PREFIX[RunState.REPORT_DRAFTED] = [
    *_PREFIX[RunState.CANDIDATE_REVIEW],
    proposal("draft_brief", {"summary": "No material new signal in this window."}),
]
_PREFIX[RunState.QA_IN_PROGRESS] = [
    *_PREFIX[RunState.REPORT_DRAFTED],
    proposal("advance_state", {"target_state": "QA In Progress"}),
]


def agent_at(
    state: RunState,
    *,
    run_id: str = "RUN-EVAL",
    gateway_outputs: list[str] | None = None,
    collected: list[dict] | None = None,
) -> AgentOrchestrator:
    """An agent driven, through its own tools, to `state`; `gateway_outputs` follow the prefix."""
    prefix = _PREFIX[state]
    agent = AgentOrchestrator(
        authorised_orchestrator(run_id),
        run_id=run_id,
        gateway=scripted_gateway(list(gateway_outputs or [])),
        source_id_lookup=source_lookup(),
        collector_fetch=lambda _window: list(collected or []),
    )
    for text in prefix:
        agent.execute_proposal(parse_tool_proposal(text))
    if agent.state is not state:
        raise AssertionError(f"fixture reached {agent.state.value}, expected {state.value}")
    return agent
