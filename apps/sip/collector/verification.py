"""Client-side verification/citation gate for High and Critical signal candidates.

SIP-184 step 7: "High/Critical claims require official or high-confidence verification. Never
build a High/Critical claim on an inaccessible article, a snippet, an unverified social post, or
a single weak secondary source." `docs/sip/SIP_Reference_Config.json`'s
`official_verification_required_for_high`/`_for_critical` confirm this covers both levels, and
schemas/api-contract.md lists "unverified Critical claim" as a fail-closed condition every write
endpoint enforces server-side. This mirrors that rule client-side so a bad submission fails
before a round trip, not instead of the server-side check.
"""

from __future__ import annotations

from apps.sip.pipeline.models import SignalStrength, VerificationState

_SIGNALS_REQUIRING_VERIFICATION = (SignalStrength.HIGH, SignalStrength.CRITICAL)
_BLOCKED_VERIFICATION_STATES = (VerificationState.UNVERIFIED, VerificationState.REJECTED)


class UnverifiedHighSignalError(RuntimeError):
    """Raised when a High/Critical-signal candidate would be submitted without verification."""


def enforce_verification_gate(
    signal: SignalStrength | None, verification: VerificationState | None
) -> None:
    """Raises `UnverifiedHighSignalError` if `signal` is High/Critical and `verification` is
    Unverified, Rejected, or unknown. An unknown verification state is treated as unverified
    (fail closed) rather than assumed safe.
    """
    if signal in _SIGNALS_REQUIRING_VERIFICATION and (
        verification is None or verification in _BLOCKED_VERIFICATION_STATES
    ):
        got = verification.value if verification else "unknown"
        raise UnverifiedHighSignalError(
            f"{signal.value} signal requires a verified source (got verification={got})"
        )
