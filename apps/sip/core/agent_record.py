"""Store an agent audit log as JSON and read it back exactly, so a stored trail can be re-verified.

The app keeps each agent rehearsal's `AgentRunAuditLog` in Postgres (`agent_rehearsals.audit`).
Showing a stored trail is only worth something if it can be checked again later: re-sealed, and
replayed through `replay_agent_audit` without a model call. That needs a lossless round trip, which
is what this module gives. `audit_from_json(audit_to_json(a))` has the same `audit_chain_head` as
`a`, which covers every field of the log, so any loss would show up as a seal that no longer
verifies rather than as a silently different trail.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from apps.sip.core.agent_loop import AgentRunAuditLog, BriefDraftRecord, ToolAuditRecord
from apps.sip.core.orchestrator import HumanDecision, TransitionRecord
from apps.sip.pipeline.models import Candidate, RunState, SourceCheck

FORMAT = "inzbc.sip.agent-audit.json.v1"


class AuditRecordFormatError(ValueError):
    """The stored JSON is not an agent audit log this module wrote."""


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def audit_to_json(audit: AgentRunAuditLog) -> dict:
    brief = audit.brief_draft
    return {
        "format": FORMAT,
        "run_id": audit.run_id,
        "production_enabled": audit.production_enabled,
        "coverage_window": None if audit.coverage_window is None else list(audit.coverage_window),
        "transitions": [
            {
                "from_state": t.from_state.value,
                "to_state": t.to_state.value,
                "actor": t.actor,
                "at": t.at.isoformat(),
                "human_decision": None if t.human_decision is None else {
                    "approver": t.human_decision.approver,
                    "decision": t.human_decision.decision,
                    "note": t.human_decision.note,
                    "signature": t.human_decision.signature,
                },
            }
            for t in audit.transitions
        ],
        "tool_records": [
            {
                "sequence": r.sequence,
                "tool": r.tool,
                "arguments": _plain(r.arguments),
                "reason": r.reason,
                "state_before": r.state_before.value,
                "state_after": r.state_after.value,
                "outcome": r.outcome,
                "detail": r.detail,
                "actor": r.actor,
                "at": r.at.isoformat(),
            }
            for r in audit.tool_records
        ],
        "source_checks": [c.model_dump(mode="json") for c in audit.source_checks],
        "candidates": [c.model_dump(mode="json") for c in audit.candidates],
        "brief_draft": None if brief is None else {
            "summary": brief.summary,
            "included_candidate_ids": list(brief.included_candidate_ids),
            "no_material_new_signal": brief.no_material_new_signal,
            "content_sha256": brief.content_sha256,
            "created_at": brief.created_at.isoformat(),
        },
    }


def audit_from_json(data: Mapping[str, object]) -> AgentRunAuditLog:
    if not isinstance(data, Mapping) or data.get("format") != FORMAT:
        raise AuditRecordFormatError(f"not a {FORMAT} document")
    try:
        window = data["coverage_window"]
        brief = data["brief_draft"]
        return AgentRunAuditLog(
            run_id=data["run_id"],
            production_enabled=data["production_enabled"],
            coverage_window=None if window is None else (window[0], window[1]),
            transitions=tuple(
                TransitionRecord(
                    from_state=RunState(t["from_state"]),
                    to_state=RunState(t["to_state"]),
                    actor=t["actor"],
                    at=datetime.fromisoformat(t["at"]),
                    human_decision=None if t["human_decision"] is None else HumanDecision(
                        **t["human_decision"]
                    ),
                )
                for t in data["transitions"]
            ),
            tool_records=tuple(
                ToolAuditRecord(
                    sequence=r["sequence"],
                    tool=r["tool"],
                    arguments=r["arguments"],
                    reason=r["reason"],
                    state_before=RunState(r["state_before"]),
                    state_after=RunState(r["state_after"]),
                    outcome=r["outcome"],
                    detail=r["detail"],
                    actor=r["actor"],
                    at=datetime.fromisoformat(r["at"]),
                )
                for r in data["tool_records"]
            ),
            source_checks=tuple(SourceCheck.model_validate(c) for c in data["source_checks"]),
            candidates=tuple(Candidate.model_validate(c) for c in data["candidates"]),
            brief_draft=None if brief is None else BriefDraftRecord(
                summary=brief["summary"],
                included_candidate_ids=tuple(brief["included_candidate_ids"]),
                no_material_new_signal=brief["no_material_new_signal"],
                content_sha256=brief["content_sha256"],
                created_at=datetime.fromisoformat(brief["created_at"]),
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise AuditRecordFormatError(f"malformed agent audit document: {error}") from error
