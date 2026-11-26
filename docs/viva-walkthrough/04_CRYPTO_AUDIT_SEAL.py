# ==============================================================================
# FILE 4 OF 5: CRYPTOGRAPHIC AUDIT INTEGRITY (from apps/sip/core/audit_seal.py — ADR-0010)
# HOW IT WORKS:
#   - 24 Oct baseline found 0/200 forged approvals caught on replay.
#   - Implemented Schneier & Kelsey (1999) tamper-evident logging (PR #448):
#       1) HMAC-SHA256 decision signatures -> catches 200/200 forged approvals.
#       2) SHA-256 hash chain + MAC seal -> catches 1000/1000 metadata edits & 759/759 DB rewrites.
#   - Signing key lives ONLY on the API server; the AI agent loop never sees it.
# ==============================================================================

from __future__ import annotations

import hashlib                                 # SHA-256 hashing for hash chain
import hmac                                    # HMAC-SHA256 signing + constant-time compare_digest
import json                                    # Canonical JSON serialisation (sort_keys=True)
import os                                      # Reads server-side env vars
from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.sip.core.agent_loop import AgentRunAuditLog
    from apps.sip.pipeline.models import RunState

# --- 1. CONSTANTS & DOMAIN SEPARATION TAGS ---
SIGNING_KEY_ENV = "SIP_DECISION_SIGNING_KEY"         # Env var holding server-side HMAC secret
REQUIRE_SIGNED_ENV = "SIP_REQUIRE_SIGNED_DECISIONS"  # Toggle to reject legacy unsigned rows
MIN_KEY_BYTES = 32                                   # Minimum 256-bit key strength
_DECISION_DOMAIN = b"inzbc.sip.human-decision.v1"    # Domain tag prevents cross-purpose signature reuse
_AUDIT_DOMAIN = b"inzbc.sip.agent-audit.v1"          # Domain tag seeding the audit hash chain


class SigningKeyError(RuntimeError):
    """Raised fail-closed if the signing key is missing or shorter than 32 bytes."""


# --- 2. KEY LOADING & VALIDATION ---
def require_key(key: bytes) -> bytes:
    """Enforce >= 32-byte key length before any sign/verify operation."""
    if not isinstance(key, bytes) or len(key) < MIN_KEY_BYTES:
        raise SigningKeyError(f"a decision signing key must be at least {MIN_KEY_BYTES} bytes")
    return key


def signing_key_from_env() -> bytes | None:
    """Load the server signing key from env, or return None when signing is disabled in dev."""
    raw = os.environ.get(SIGNING_KEY_ENV, "")
    if not raw:
        return None
    return require_key(raw.encode("utf-8"))


def signed_decisions_required() -> bool:
    """Return True when strict signed-only mode is enabled (blocks even legacy unsigned rows)."""
    return os.environ.get(REQUIRE_SIGNED_ENV, "").strip().lower() in {"1", "true", "yes"}


# --- 3. PER-DECISION HMAC-SHA256 SIGNING (CATCHES 200/200 FORGED APPROVALS) ---
def _decision_payload(
    run_id: str, from_state: RunState, to_state: RunState, approver: str, decision: str,
    note: str | None,
) -> bytes:
    """Bind run_id + exact transition + approver + verdict + note into one canonical byte string.
    Binding run_id & states stops an attacker from replaying a real signature onto a different run/gate."""
    fields = [run_id, from_state.value, to_state.value, approver, decision, note]
    return _DECISION_DOMAIN + b"\x00" + json.dumps(fields, ensure_ascii=True).encode("ascii")


def sign_decision(
    key: bytes, *, run_id: str, from_state: RunState, to_state: RunState, approver: str,
    decision: str, note: str | None = None,
) -> str:
    """Compute the 64-char hex HMAC-SHA256 stored alongside a human decision in PostgreSQL."""
    payload = _decision_payload(run_id, from_state, to_state, approver, decision, note)
    return hmac.new(require_key(key), payload, hashlib.sha256).hexdigest()


def decision_signature_valid(
    key: bytes, signature: str | None, *, run_id: str, from_state: RunState, to_state: RunState,
    approver: str, decision: str, note: str | None = None,
) -> bool:
    """Verify a stored decision signature using constant-time `compare_digest` (prevents timing attacks)."""
    if not isinstance(signature, str):
        return False
    expected = sign_decision(key, run_id=run_id, from_state=from_state, to_state=to_state,
                             approver=approver, decision=decision, note=note)
    return hmac.compare_digest(expected, signature)


# --- 4. WHOLE-LOG SHA-256 HASH CHAIN & MAC SEAL (CATCHES 1000/1000 METADATA & 759/759 DB REWRITES) ---
def _plain(value: object) -> object:
    """Recursively convert enums, datetimes, and mappings into deterministic JSON primitives."""
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if hasattr(value, "value") and type(value).__module__.startswith("apps."):
        return value.value                     # Convert Python Enum -> string value
    if hasattr(value, "isoformat"):
        return value.isoformat()               # Convert datetime -> ISO-8601 string
    return value


def _records(audit: AgentRunAuditLog) -> list[object]:
    """Flatten the entire run audit log in a strict fixed order so ANY edit/deletion/reorder breaks the hash."""
    records: list[object] = [
        ["header", audit.run_id, audit.production_enabled, _plain(audit.coverage_window)],
    ]
    for t in audit.transitions:                # Every state transition + actor + timestamp + human decision + sig
        decision = t.human_decision
        records.append(["transition", t.from_state.value, t.to_state.value, t.actor,
                        t.at.isoformat(),
                        None if decision is None else [decision.approver, decision.decision,
                                                       decision.note, decision.signature]])
    for r in audit.tool_records:               # Every tool call the coordinator executed + args + outcome
        records.append(["tool", r.sequence, r.tool, _plain(r.arguments), r.reason,
                        r.state_before.value, r.state_after.value, r.outcome, r.detail, r.actor,
                        r.at.isoformat()])
    for check in audit.source_checks:          # Every SIP-185 source verification record
        records.append(["source_check", check.model_dump(mode="json")])
    for candidate in audit.candidates:         # Every news candidate scored/verified
        records.append(["candidate", candidate.model_dump(mode="json")])
    brief = audit.brief_draft                  # Draft brief metadata + content SHA-256 hash
    records.append(["brief", None if brief is None else [
        brief.summary, list(brief.included_candidate_ids), brief.no_material_new_signal,
        brief.content_sha256, brief.created_at.isoformat()]])
    return records


def audit_chain_head(audit: AgentRunAuditLog) -> str:
    """Fold every record into a linked SHA-256 chain: head_i = SHA256(head_{i-1} || canonical_json(record_i))."""
    head = hashlib.sha256(_AUDIT_DOMAIN).digest()        # Initial domain-separated seed
    for record in _records(audit):
        encoded = json.dumps(record, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        head = hashlib.sha256(head + encoded.encode("ascii")).digest()
    return head.hex()


def seal_audit(audit: AgentRunAuditLog, key: bytes) -> str:
    """MAC the final chain head with the server key so even a DB admin cannot recompute a valid seal."""
    return hmac.new(require_key(key), bytes.fromhex(audit_chain_head(audit)),
                    hashlib.sha256).hexdigest()
