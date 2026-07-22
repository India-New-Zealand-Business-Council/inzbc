from __future__ import annotations

import pytest

from apps.sip.collector.verification import (
    UnverifiedHighSignalError,
    enforce_verification_gate,
)
from apps.sip.pipeline.models import SignalStrength, VerificationState


@pytest.mark.parametrize("signal", [SignalStrength.HIGH, SignalStrength.CRITICAL])
@pytest.mark.parametrize(
    "verification",
    [
        VerificationState.UNVERIFIED,
        VerificationState.REJECTED,
        VerificationState.NOT_REQUIRED,
        None,
    ],
)
def test_gate_blocks_high_and_critical_without_verification(signal, verification) -> None:
    with pytest.raises(UnverifiedHighSignalError):
        enforce_verification_gate(signal, verification)


@pytest.mark.parametrize("signal", [SignalStrength.HIGH, SignalStrength.CRITICAL])
@pytest.mark.parametrize(
    "verification", [VerificationState.VERIFIED, VerificationState.PARTIALLY_VERIFIED]
)
def test_gate_allows_high_and_critical_when_verified(signal, verification) -> None:
    enforce_verification_gate(signal, verification)  # should not raise


@pytest.mark.parametrize("signal", [SignalStrength.LOW, SignalStrength.MEDIUM, None])
def test_gate_allows_low_and_medium_signal_regardless_of_verification(signal) -> None:
    enforce_verification_gate(signal, VerificationState.UNVERIFIED)  # should not raise
    enforce_verification_gate(signal, None)  # should not raise


@pytest.mark.parametrize("signal", [SignalStrength.HIGH, SignalStrength.CRITICAL])
def test_gate_blocks_not_required_verification_on_high_and_critical(signal) -> None:
    # "Not required" is self-contradictory for a claim SIP-050 says needs official/high-
    # confidence evidence - it must fail closed the same as Unverified or Rejected.
    with pytest.raises(UnverifiedHighSignalError):
        enforce_verification_gate(signal, VerificationState.NOT_REQUIRED)
