"""SIP-185 source register: the mandatory source worklist and per-run outcome recording.

Mirrors the approved **SIP-185 Production Source Register v1.0** (176 sources: 112 mandatory,
64 selective). The register data lives in `data/sip185_sources_v1.0.csv`, exported from the
controlling spreadsheet - update that CSV from the approved register, do not hand-edit source
rows in code. That spreadsheet is the controlling reference.

Sources are keyed by their SIP-185 source id (e.g. `NZ-OFF-001`), not by name: v1.0 has
non-unique names across jurisdictions (NZ and India both have a "Ministry of Defence" and a
"Ministry of Education"), so name is not a safe key for a Critical-stop coverage gate. Resolving
a source id to a `source_library` db uuid needs `source_library` to carry the SIP-185 code;
until it does, callers supply `source_id_lookup` (see docs/workstreams/roshan.md).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

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

_REGISTER_CSV = Path(__file__).parent / "data" / "sip185_sources_v1.0.csv"


@dataclass(frozen=True)
class SourceRegisterEntry:
    source_id: str  # SIP-185 register id, e.g. "NZ-OFF-001" - the stable, unique key
    name: str
    country: str  # "New Zealand" | "India" | "International"
    category: str
    layer: int  # 1 Official .. 4 Media, per SIP-050
    mandatory: bool


def _load_register() -> tuple[SourceRegisterEntry, ...]:
    with _REGISTER_CSV.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return tuple(
        SourceRegisterEntry(
            source_id=row["source_id"],
            name=row["name"],
            country=row["country"],
            category=row["category"],
            layer=int(row["layer"]),
            mandatory=row["mandatory"].strip().lower() == "true",
        )
        for row in rows
    )


ALL_SOURCES: tuple[SourceRegisterEntry, ...] = _load_register()
MANDATORY_SOURCES: tuple[SourceRegisterEntry, ...] = tuple(s for s in ALL_SOURCES if s.mandatory)


def missing_mandatory_outcomes(recorded_source_ids: set[str]) -> list[str]:
    """SIP-185 source ids of mandatory sources with no recorded outcome yet. A non-empty result
    is a Critical stop (SIP-184 step 4 / step 11) - never submit a run for QA while it is
    non-empty. Keyed on source id, not name, because two register names are non-unique across
    NZ/India (see module docstring).
    """
    return [s.source_id for s in MANDATORY_SOURCES if s.source_id not in recorded_source_ids]


class SourceIdUnresolved(RuntimeError):
    """Raised when `source_id_lookup` has no db id for a source. `source_checks.source_id` is NOT
    NULL in database/schema.sql - there is no such thing as a source check without one, so this
    fails loud rather than sending pydantic's generic validation error up to the caller.
    """


def record_source_outcome(
    run_id: str,
    source_id: str,
    outcome: SourceOutcome,
    source_id_lookup: dict[str, str],
    fallback_attempts: list[str] | None = None,
    access_error: str | None = None,
    notes: str | None = None,
) -> SourceCheck:
    """Builds a SourceCheck for one source's outcome this run.

    `source_id` is the SIP-185 register id (e.g. `NZ-OFF-001`). `source_id_lookup` maps that id to
    its `source_library` db uuid - a `GET /api/source-library` endpoint exists (PR #25) to build
    the map once `source_library` carries the SIP-185 code; wiring it into this module's callers
    is tracked in docs/workstreams/roshan.md, not done by this function itself.

    `fallback_attempts` is the ordered trail of steps actually tried (a subsequence of
    FALLBACK_SEQUENCE) when direct access did not suffice - SIP-185 requires retaining every
    fallback attempt and the reason, so the trail is folded into `notes` rather than dropped
    (the source_checks table has no separate attempts column to put it in).
    """
    db_id = source_id_lookup.get(source_id)
    if not db_id:
        raise SourceIdUnresolved(
            f"no source_library id for {source_id!r}; source_checks.source_id is required "
            "(database/schema.sql) and source_id_lookup did not resolve it - see "
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
        source_id=db_id,
        outcome=outcome,
        method=method,
        fallback_used=fallback_used,
        access_error=access_error,
        notes=combined_notes,
    )
