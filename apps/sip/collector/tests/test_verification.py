from __future__ import annotations

import pytest

from apps.sip.collector.verification import (
    UnverifiedHighSignalError,
    enforce_verification_gate,
)
from apps.sip.pipeline.models import SignalStrength, VerificationState


@pytest.mark.parametrize("signal", [SignalStrength.HIGH, SignalStrength.CRITICAL])
@pytest.mark.parametrize(
    "verification", [VerificationState.UNVERIFIED, VerificationState.REJECTED, None]
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
