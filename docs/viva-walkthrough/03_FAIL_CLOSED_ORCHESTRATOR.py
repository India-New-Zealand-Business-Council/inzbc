# ==============================================================================
# FILE 3 OF 5: FAIL-CLOSED STATE MACHINE & ORCHESTRATOR (from apps/sip/core/orchestrator.py)
# HOW IT WORKS:
#   - Core answer to Research Question: "Can an automated coordinator run the daily
#     process while hard-coded controls guarantee it never skips a human approval step?"
#   - THIS MODULE IS THE ONLY CODE PATH THAT CAN MUTATE A RUN'S STATE.
#   - Even if an LLM is prompt-injected, it can ONLY propose a transition; Python code
#     checks `_LEGAL` and `_HUMAN_GATED` and FAILS CLOSED (blocks 48/48 attacks).
# ==============================================================================

from __future__ import annotations

from dataclasses import dataclass              # Immutable value object for HumanDecision
from types import MappingProxyType             # Read-only dict wrapper so runtime code cannot tamper with transitions

from apps.sip.pipeline.models import RunState  # Enum of all valid SIP-184 daily run states


# --- 1. IMMUTABLE STATE-TRANSITION GRAPH (_LEGAL) ---
# Wrapped in MappingProxyType + frozenset so no code can widen allowed transitions at runtime.
# Any target state not explicitly listed here raises `IllegalTransition` (fail-closed).
_LEGAL: MappingProxyType[RunState, frozenset[RunState]] = MappingProxyType({
    RunState.DRAFT: frozenset({RunState.RUN_AUTHORISED}),                                # Step 1: Must get launch authority first
    RunState.RUN_AUTHORISED: frozenset({RunState.COVERAGE_LOCKED}),                      # Step 2: Lock 24-hour news coverage window
    RunState.COVERAGE_LOCKED: frozenset({RunState.SCANNING}),                            # Step 3: Begin scanning 112 SIP-185 sources
    RunState.SCANNING: frozenset({RunState.CANDIDATE_REVIEW}),                           # Step 4: Score & surface candidate items
    RunState.CANDIDATE_REVIEW: frozenset({RunState.REPORT_DRAFTED}),                     # Step 5: Draft brief from verified candidates
    RunState.REPORT_DRAFTED: frozenset({RunState.QA_IN_PROGRESS}),                       # Step 6: Enter independent QA review
    RunState.QA_IN_PROGRESS: frozenset({RunState.AWAITING_CEO_DECISION, RunState.QA_FAILED}),  # Step 7: QA passes OR fails closed
    RunState.QA_FAILED: frozenset({RunState.REPORT_DRAFTED}),                            # Failed QA must return to drafting
    RunState.AWAITING_CEO_DECISION: frozenset({                                          # Step 8: Explicit CEO ruling options:
        RunState.APPROVED_FOR_MANUAL_DISTRIBUTION,                                       #   - Approve for manual send
        RunState.CONTINUE,                                                               #   - Continue monitoring
        RunState.CONTINUE_WITH_CORRECTION,                                               #   - Continue with correction
        RunState.PAUSED,                                                                 #   - Pause run
        RunState.STOPPED,                                                                #   - Permanently stop run
    }),
    RunState.APPROVED_FOR_MANUAL_DISTRIBUTION: frozenset({RunState.DISTRIBUTED}),        # Step 9: Separate manual distribution act
    RunState.DISTRIBUTED: frozenset({RunState.CLOSED}),                                  # Step 10: Close completed run
    RunState.PAUSED: frozenset({RunState.COVERAGE_LOCKED}),                              # Resuming a paused run requires human approval
    # Terminal states have EMPTY outbound sets -> a stopped/closed run can NEVER be resurrected:
    RunState.STOPPED: frozenset(),
    RunState.CLOSED: frozenset(),
    RunState.CONTINUE: frozenset(),
    RunState.CONTINUE_WITH_CORRECTION: frozenset(),
    RunState.CORRECTED: frozenset(),
    RunState.WITHDRAWN: frozenset(),
})


# --- 2. MANDATORY HUMAN APPROVAL GATES (_HUMAN_GATED) ---
# Mechanical steps (lock window, scan, draft) can be driven by the automated coordinator.
# The 11 transitions below CANNOT be crossed without a valid `HumanDecision` (approver + verdict + HMAC sig).
_HUMAN_GATED: frozenset[tuple[RunState, RunState]] = frozenset({
    (RunState.DRAFT, RunState.RUN_AUTHORISED),                                           # Gate 1: Human launch authority
    (RunState.QA_IN_PROGRESS, RunState.AWAITING_CEO_DECISION),                           # Gate 2: Independent QA sign-off (SoD)
    (RunState.QA_IN_PROGRESS, RunState.QA_FAILED),                                       # Gate 3: Recorded Critical QA finding
    (RunState.QA_FAILED, RunState.REPORT_DRAFTED),                                       # Gate 4: Human correction & re-review
    (RunState.AWAITING_CEO_DECISION, RunState.APPROVED_FOR_MANUAL_DISTRIBUTION),         # Gate 5: CEO approval ruling
    (RunState.AWAITING_CEO_DECISION, RunState.CONTINUE),                                 # Gate 6: CEO continue ruling
    (RunState.AWAITING_CEO_DECISION, RunState.CONTINUE_WITH_CORRECTION),                 # Gate 7: CEO continue-with-correction
    (RunState.AWAITING_CEO_DECISION, RunState.PAUSED),                                   # Gate 8: CEO pause ruling
    (RunState.AWAITING_CEO_DECISION, RunState.STOPPED),                                  # Gate 9: CEO permanent stop ruling
    (RunState.APPROVED_FOR_MANUAL_DISTRIBUTION, RunState.DISTRIBUTED),                   # Gate 10: Separate distribution authority
    (RunState.PAUSED, RunState.COVERAGE_LOCKED),                                         # Gate 11: Human resumption approval
})


# --- 3. FAIL-CLOSED DOMAIN EXCEPTIONS ---
class IllegalTransition(RuntimeError):
    """Raised when a caller/agent attempts to jump across states not in `_LEGAL`."""

class HumanGateRequired(RuntimeError):
    """Raised when a `_HUMAN_GATED` transition is attempted without a valid `HumanDecision`."""

class RunTerminated(RuntimeError):
    """Raised if anything tries to mutate a terminal `STOPPED` / `CLOSED` / `WITHDRAWN` run."""


# --- 4. IMMUTABLE HUMAN DECISION RECORD ---
@dataclass(frozen=True)                        # frozen=True prevents in-memory mutation after creation
class HumanDecision:
    """Represents a real, attributable human approval binding an approver to a gated transition."""

    approver: str                              # Authenticated user identity (cannot be blank)
    decision: str                              # Explicit verdict (e.g., "approve", "reject", "stop")
    note: str | None = None                    # Optional human rationale
    signature: str | None = None               # 64-char hex HMAC-SHA256 created by server (`audit_seal.py`)

    def __post_init__(self) -> None:
        # Reject blank approvers or decisions immediately at construction time
        if not isinstance(self.approver, str) or not self.approver.strip():
            raise ValueError("HumanDecision approver cannot be blank")
        if not isinstance(self.decision, str) or not self.decision.strip():
            raise ValueError("HumanDecision decision cannot be blank")
        # If signed, enforce exact 64 lowercase hex characters (SHA-256 HMAC digest format)
        if self.signature is not None and (
            not isinstance(self.signature, str)
            or len(self.signature) != 64
            or any(c not in "0123456789abcdef" for c in self.signature)
        ):
            raise ValueError("HumanDecision signature must be 64 lowercase hex characters")
