"""Prepare explicit, evidence-backed SIP-185 source outcomes for the existing API.

This is an offline validation boundary, not an autonomous collector or a write path. Source
fetch-health states (ok/no_recent/partial/error) never imply a SIP-185 outcome. A human must
supply an explicit outcome with an evidence reference before this adapter can construct a
SourceCheck. Only the separately authorised caller may send it via SipPipelineClient.
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.sip.pipeline.models import SourceCheck, SourceOutcome

from .source_lookup import SourceIdLookup
from .source_register import ALL_SOURCES, record_source_outcome

KNOWN_CODES = frozenset(entry.source_id for entry in ALL_SOURCES)


@dataclass(frozen=True)
class ConfirmedSourceObservation:
    """One run-scoped source determination, not a raw fetch-health observation."""

    run_id: str
    sip185_code: str
    outcome: SourceOutcome
    confirmed_by: str
    evidence_ref: str
    fallback_attempts: tuple[str, ...] = ()
    access_error: str | None = None


def prepare_confirmed_source_checks(
    run_id: str,
    observations: list[ConfirmedSourceObservation],
    source_id_lookup: SourceIdLookup,
) -> list[SourceCheck]:
    """Fail atomically on malformed evidence; return checks but never POST them.

    Callers must obtain run authorization and enforce actor roles through the existing API.
    Construct all checks first so an invalid later row cannot cause partial remote writes.
    """
    if not run_id.strip():
        raise ValueError("run_id is required")
    if type(source_id_lookup) is not SourceIdLookup:
        raise TypeError("source_id_lookup must be exactly SourceIdLookup")
    seen: set[str] = set()
    checks: list[SourceCheck] = []
    for observation in observations:
        if observation.run_id != run_id:
            raise ValueError("source observation belongs to a different run")
        if observation.sip185_code not in KNOWN_CODES:
            raise ValueError(f"unknown SIP-185 source code {observation.sip185_code!r}")
        if observation.sip185_code in seen:
            raise ValueError(f"duplicate source observation {observation.sip185_code!r}")
        if not observation.confirmed_by.strip():
            raise ValueError("explicit checker identity is required")
        if not observation.evidence_ref.strip():
            raise ValueError("evidence reference is required")
        if type(observation.outcome) is not SourceOutcome:
            raise TypeError("outcome must be an explicit SourceOutcome; fetch health is not enough")
        # The fallback trail (unknown, repeated or reordered steps) is validated by
        # record_source_outcome itself (#444), so every caller gets the same check.
        seen.add(observation.sip185_code)
        checks.append(
            record_source_outcome(
                run_id=run_id,
                source_id=observation.sip185_code,
                outcome=observation.outcome,
                source_id_lookup=source_id_lookup,
                fallback_attempts=list(observation.fallback_attempts),
                access_error=observation.access_error,
                notes=(
                    f"Human checked by: {observation.confirmed_by.strip()}; "
                    f"Evidence reference: {observation.evidence_ref.strip()}"
                ),
            )
        )
    return checks
