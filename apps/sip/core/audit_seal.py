"""Bind human decisions to their authors, and seal the agent's audit log (Studio 6, W6 change).

The replay baseline (`docs/research/agent-safety-baseline.md`) found one safety-relevant gap: a
forged transition carrying a `HumanDecision` replays as valid, because a decision records *that*
someone approved but nothing proves *who* did. Metadata (actors, timestamps, free-text reasons)
was not bound either. Schneier and Kelsey (1999) describe the fix this module applies:

- **Decision signatures.** When an authenticated person records a gated decision, the server
  signs it with HMAC-SHA256 over the run, the exact transition, the approver and the decision. A
  signature cannot be moved to another run or another gate, and cannot be made without the key.
- **An audit seal.** The whole agent audit log is folded into a SHA-256 hash chain, and the
  chain's head is MACed with the same key. Changing, dropping, reordering or appending any record
  (metadata included) changes the head, and a new seal cannot be made without the key.

The key is server-held (`SIP_DECISION_SIGNING_KEY`, at least 32 bytes). It never reaches a model,
and the agent loop has no access to it: the agent cannot sign, so it still cannot cross a gate.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.sip.core.agent_loop import AgentRunAuditLog
    from apps.sip.pipeline.models import RunState

SIGNING_KEY_ENV = "SIP_DECISION_SIGNING_KEY"
REQUIRE_SIGNED_ENV = "SIP_REQUIRE_SIGNED_DECISIONS"
MIN_KEY_BYTES = 32
_DECISION_DOMAIN = b"inzbc.sip.human-decision.v1"
_AUDIT_DOMAIN = b"inzbc.sip.agent-audit.v1"


class SigningKeyError(RuntimeError):
    """The signing key is missing or too short to be safe."""


def require_key(key: bytes) -> bytes:
    if not isinstance(key, bytes) or len(key) < MIN_KEY_BYTES:
        raise SigningKeyError(f"a decision signing key must be at least {MIN_KEY_BYTES} bytes")
    return key


def signing_key_from_env() -> bytes | None:
    """The configured key, or None when signing is not configured in this environment."""
    raw = os.environ.get(SIGNING_KEY_ENV, "")
    if not raw:
        return None
    return require_key(raw.encode("utf-8"))


def signed_decisions_required() -> bool:
    """When on, a gated transition without a valid signature is refused, legacy rows included."""
    return os.environ.get(REQUIRE_SIGNED_ENV, "").strip().lower() in {"1", "true", "yes"}


def _decision_payload(
    run_id: str, from_state: RunState, to_state: RunState, approver: str, decision: str,
    note: str | None,
) -> bytes:
    fields = [run_id, from_state.value, to_state.value, approver, decision, note]
    return _DECISION_DOMAIN + b"\x00" + json.dumps(fields, ensure_ascii=True).encode("ascii")


def sign_decision(
    key: bytes, *, run_id: str, from_state: RunState, to_state: RunState, approver: str,
    decision: str, note: str | None = None,
) -> str:
    """The signature the server stores with a human decision when a person records it."""
    payload = _decision_payload(run_id, from_state, to_state, approver, decision, note)
    return hmac.new(require_key(key), payload, hashlib.sha256).hexdigest()


def decision_signature_valid(
    key: bytes, signature: str | None, *, run_id: str, from_state: RunState, to_state: RunState,
    approver: str, decision: str, note: str | None = None,
) -> bool:
    if not isinstance(signature, str):
        return False
    expected = sign_decision(key, run_id=run_id, from_state=from_state, to_state=to_state,
                             approver=approver, decision=decision, note=note)
    return hmac.compare_digest(expected, signature)


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if hasattr(value, "value") and type(value).__module__.startswith("apps."):
        return value.value  # enums
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _records(audit: AgentRunAuditLog) -> list[object]:
    """Every field of the log, in a fixed order, as plain JSON values."""
    records: list[object] = [
        ["header", audit.run_id, audit.production_enabled, _plain(audit.coverage_window)],
    ]
    for t in audit.transitions:
        decision = t.human_decision
        records.append(["transition", t.from_state.value, t.to_state.value, t.actor,
                        t.at.isoformat(),
                        None if decision is None else [decision.approver, decision.decision,
                                                       decision.note, decision.signature]])
    for r in audit.tool_records:
        records.append(["tool", r.sequence, r.tool, _plain(r.arguments), r.reason,
                        r.state_before.value, r.state_after.value, r.outcome, r.detail, r.actor,
                        r.at.isoformat()])
    for check in audit.source_checks:
        records.append(["source_check", check.model_dump(mode="json")])
    for candidate in audit.candidates:
        records.append(["candidate", candidate.model_dump(mode="json")])
    brief = audit.brief_draft
    records.append(["brief", None if brief is None else [
        brief.summary, list(brief.included_candidate_ids), brief.no_material_new_signal,
        brief.content_sha256, brief.created_at.isoformat()]])
    return records


def audit_chain_head(audit: AgentRunAuditLog) -> str:
    """SHA-256 hash chain over every record of the log: each link hashes the one before it."""
    head = hashlib.sha256(_AUDIT_DOMAIN).digest()
    for record in _records(audit):
        encoded = json.dumps(record, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        head = hashlib.sha256(head + encoded.encode("ascii")).digest()
    return head.hex()


def seal_audit(audit: AgentRunAuditLog, key: bytes) -> str:
    """The MAC over the chain head, stored alongside the log."""
    return hmac.new(require_key(key), bytes.fromhex(audit_chain_head(audit)),
                    hashlib.sha256).hexdigest()


def seal_valid(audit: AgentRunAuditLog, seal: str | None, key: bytes) -> bool:
    if not isinstance(seal, str):
        return False
    return hmac.compare_digest(seal_audit(audit, key), seal)
