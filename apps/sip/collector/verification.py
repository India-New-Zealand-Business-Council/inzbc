"""Client-side verification/citation gate for High and Critical signal candidates.

SIP-050 section 14 (Claim Verification): "Use official or high-confidence evidence for High and
Critical claims where reasonably available... Do not turn inference, event-wide figures or
secondary reporting into a New Zealand-specific fact without evidence." Section 27 (Critical
Fail-Closed Controls) lists "Unverified Critical claim" as one of the conditions that must never
be downgraded to a warning. This mirrors that rule client-side so a bad submission fails before a
round trip, not instead of the server-side check in schemas/api-contract.md.

Verification is an allowlist, not a blocklist: only Verified and Partially Verified pass for a
High/Critical signal. `VerificationState.NOT_REQUIRED` is not in that allowlist on purpose - "not
required" is self-contradictory for a claim that SIP-050 says needs official/high-confidence
evidence, so it fails closed the same as Unverified or Rejected.
"""

from __future__ import annotations

from apps.sip.pipeline.models import SignalStrength, VerificationState

_SIGNALS_REQUIRING_VERIFICATION = (SignalStrength.HIGH, SignalStrength.CRITICAL)
_VERIFIED_STATES = (VerificationState.VERIFIED, VerificationState.PARTIALLY_VERIFIED)


class UnverifiedHighSignalError(RuntimeError):
    """Raised when a High/Critical-signal candidate would be submitted without verification."""


def enforce_verification_gate(
    signal: SignalStrength | None, verification: VerificationState | None
) -> None:
    """Raises `UnverifiedHighSignalError` if `signal` is High/Critical and `verification` is
    anything other than Verified or Partially Verified. Unverified, Rejected, Not Required, and
    unknown (None) are all blocked - an unknown state is treated as unverified (fail closed)
    rather than assumed safe.
    """
    if signal in _SIGNALS_REQUIRING_VERIFICATION and verification not in _VERIFIED_STATES:
        got = verification.value if verification else "unknown"
        raise UnverifiedHighSignalError(
            f"{signal.value} signal requires a verified source (got verification={got})"
        )
