"""SIP-185 source register: the mandatory source worklist and per-run outcome recording.

Mirrors docs/sip/launch/SIP-185_source_register_v0.9.md exactly - do not add or drop a source
without updating that doc first, it is the controlling reference.
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.sip.pipeline.models import SourceCheck, SourceOutcome

FALLBACK_SEQUENCE: tuple[str, ...] = (
    "Direct access",
    "Search within the source",
    "Indexed site search",
    "Recognised news / document index",
    "RSS or approved feed",
    "Controlled keyword search",
    "Secondary discovery source",
    "Primary-source verification before material use",
)


@dataclass(frozen=True)
class SourceRegisterEntry:
    name: str
    category: str  # "NZ Official" | "India Official" | "Bilateral" | "NZ media" | "Controlled-access"
    layer: int  # 1 Official .. 5 Other, per SIP-050
    mandatory: bool


MANDATORY_SOURCES: tuple[SourceRegisterEntry, ...] = (
    # Official (Layer 1) - NZ
    SourceRegisterEntry("MFAT", "NZ Official", 1, True),
    SourceRegisterEntry("Beehive / ministerial releases", "NZ Official", 1, True),
    SourceRegisterEntry("NZ Parliament", "NZ Official", 1, True),
    SourceRegisterEntry("NZ Customs", "NZ Official", 1, True),
    SourceRegisterEntry("RBNZ", "NZ Official", 1, True),
    SourceRegisterEntry("Stats NZ", "NZ Official", 1, True),
    SourceRegisterEntry("NZTE", "NZ Official", 1, True),
    # Official (Layer 1) - India
    SourceRegisterEntry("Ministry of Commerce & Industry / PIB", "India Official", 1, True),
    SourceRegisterEntry("Department of Commerce", "India Official", 1, True),
    SourceRegisterEntry("MEA", "India Official", 1, True),
    SourceRegisterEntry("PMIndia", "India Official", 1, True),
    SourceRegisterEntry("RBI", "India Official", 1, True),
    SourceRegisterEntry("DGFT", "India Official", 1, True),
    # Bilateral
    SourceRegisterEntry("NZ-India FTA official pages", "Bilateral", 1, True),
    SourceRegisterEntry("High Commission releases (NZ)", "Bilateral", 1, True),
    SourceRegisterEntry("High Commission releases (India)", "Bilateral", 1, True),
    # NZ media (mandatory scan)
    SourceRegisterEntry("NZ Herald", "NZ media", 4, True),
    SourceRegisterEntry("RNZ", "NZ media", 4, True),
    SourceRegisterEntry("1News", "NZ media", 4, True),
    SourceRegisterEntry("Stuff", "NZ media", 4, True),
    SourceRegisterEntry("Newsroom", "NZ media", 4, True),
    SourceRegisterEntry("BusinessDesk", "NZ media", 4, True),
    SourceRegisterEntry("Newstalk ZB", "NZ media", 4, True),
    SourceRegisterEntry("Rural News", "NZ media", 4, True),
    SourceRegisterEntry("Farmers Weekly", "NZ media", 4, True),
    SourceRegisterEntry("Relevant NZ Indian media", "NZ media", 4, True),
    # Controlled-access mandatory (known limitations - see SIP-185)
    SourceRegisterEntry("Stuff (controlled access)", "Controlled-access", 4, True),
    SourceRegisterEntry("The Hindu BusinessLine", "Controlled-access", 4, True),
)


def missing_mandatory_outcomes(recorded_names: set[str]) -> list[str]:
    """Mandatory sources with no recorded outcome yet. A non-empty result is a Critical stop
    (SIP-184 step 4 / step 11) - never submit a run for QA while this is non-empty.
    """
    return [entry.name for entry in MANDATORY_SOURCES if entry.mandatory and entry.name not in recorded_names]


class SourceIdUnresolved(RuntimeError):
    """Raised when `source_lookup` has no id for a source. `source_checks.source_id` is NOT
    NULL in database/schema.sql - there is no such thing as a source check without one, so this
    fails loud rather than sending pydantic's generic validation error up to the caller.
    """


def record_source_outcome(
    run_id: str,
    name: str,
    outcome: SourceOutcome,
    source_lookup: dict[str, str],
    fallback_attempts: list[str] | None = None,
    access_error: str | None = None,
    notes: str | None = None,
) -> SourceCheck:
    """Builds a SourceCheck for one source's outcome this run.

    `fallback_attempts` is the ordered trail of steps actually tried (a subsequence of
    FALLBACK_SEQUENCE) when direct access did not suffice - SIP-185 requires retaining every
    fallback attempt and the reason, so the trail is folded into `notes` rather than dropped
    (the source_checks table has no separate attempts column to put it in).

    `source_lookup` must resolve `name` to a source_library id - a `GET /api/source-library`
    endpoint exists (PR #25) to build this map; wiring it into this module's callers is tracked
    in docs/workstreams/roshan.md, not done by this function itself.
    """
    source_id = source_lookup.get(name)
    if not source_id:
        raise SourceIdUnresolved(
            f"no source_library id for {name!r}; source_checks.source_id is required "
            "(database/schema.sql) and source_lookup did not resolve it - see "
            "docs/workstreams/roshan.md for wiring GET /api/source-library into the caller"
        )

    # A fallback happened if the final method actually tried isn't the first step in the
    # sequence - a single recorded attempt that skipped straight to a later step (e.g. only
    # "RSS or approved feed" was tried) is still a fallback, not "no fallback used".
    fallback_used = bool(fallback_attempts) and fallback_attempts[-1] != FALLBACK_SEQUENCE[0]
    method = fallback_attempts[-1] if fallback_attempts else None

    trail_note = None
    if fallback_attempts:
        trail_note = "; ".join(f"{i}. {step}" for i, step in enumerate(fallback_attempts, start=1))

    combined_notes = "; ".join(part for part in (trail_note, notes) if part) or None

    return SourceCheck(
        run_id=run_id,
        source_id=source_id,
        outcome=outcome,
        method=method,
        fallback_used=fallback_used,
        access_error=access_error,
        notes=combined_notes,
    )
