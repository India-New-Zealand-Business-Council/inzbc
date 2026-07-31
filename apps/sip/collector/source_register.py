"""SIP-185 source register: the mandatory source worklist and per-run outcome recording.

Mirrors the approved **SIP-185 Production Source Register v1.0** (176 sources: 112 mandatory,
64 selective). The register data lives in `data/sip185_sources_v1.0.csv`, exported from the
controlling spreadsheet - update that CSV from the approved register, do not hand-edit source
rows in code. That spreadsheet is the controlling reference.

Sources are keyed by their SIP-185 source id (e.g. `NZ-OFF-001`), not by name: v1.0 has
non-unique names across jurisdictions (NZ and India both have a "Ministry of Defence" and a
"Ministry of Education"), so name is not a safe key for a Critical-stop coverage gate.
`source_library` now carries the SIP-185 code (`schemas/api-contract.md`); callers build a
`source_lookup.SourceIdLookup` from `SipPipelineClient.get_source_library()` and pass it to
`record_source_outcome`.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from apps.sip.pipeline.models import SourceCheck, SourceOutcome

from .source_lookup import SourceIdLookup

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
    return tuple(_row_to_entry(row) for row in rows)


def _parse_mandatory(raw: str, source_id: str) -> bool:
    """Strict bool parse. A blank/typo/encoding-garbled `mandatory` cell must fail the load, not
    silently coerce to False - that would drop a source from MANDATORY_SOURCES and let the
    Critical-stop coverage gate pass when it should block (fail-open on a compliance control).
    """
    value = raw.strip().lower()
    if value not in {"true", "false"}:
        raise ValueError(
            f"source {source_id!r} has an invalid `mandatory` value {raw!r}; "
            "expected 'true' or 'false' - refusing to load rather than silently under-count "
            "the mandatory-source coverage gate"
        )
    return value == "true"


def _row_to_entry(row: dict[str, str]) -> SourceRegisterEntry:
    return SourceRegisterEntry(
        source_id=row["source_id"],
        name=row["name"],
        country=row["country"],
        category=row["category"],
        layer=int(row["layer"]),
        mandatory=_parse_mandatory(row["mandatory"], row["source_id"]),
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
    source_id_lookup: SourceIdLookup,
    fallback_attempts: list[str] | None = None,
    access_error: str | None = None,
    notes: str | None = None,
) -> SourceCheck:
    """Builds a SourceCheck for one source's outcome this run.

    `source_id` is the SIP-185 register id (e.g. `NZ-OFF-001`). `source_id_lookup` maps that id to
    its `source_library` db uuid — build it from `apps.sip.pipeline.client.SipPipelineClient
    .get_source_library()` via `source_lookup.build_source_lookups()`.

    `source_id_lookup` must be exactly `SourceIdLookup` (keyed by SIP-185 code) — an exact
    `type() is` check, not `isinstance`: `isinstance` accepts subclasses by design, so a subclass
    overriding `get()` would walk straight through an `isinstance` guard and could resolve to any
    id it likes. `source_checks.source_id` is NOT NULL and jurisdiction-sensitive, which is the
    reason this guard exists at all - accepting only the exact type closes that off, the same fix
    already applied to the orchestrator's human-decision gate after the same vector was found
    there.

    `fallback_attempts` is the ordered trail of steps actually tried (a subsequence of
    FALLBACK_SEQUENCE) when direct access did not suffice - SIP-185 requires retaining every
    fallback attempt and the reason, so the trail is folded into `notes` rather than dropped
    (the source_checks table has no separate attempts column to put it in).
    """
    if type(source_id_lookup) is not SourceIdLookup:
        raise TypeError(
            f"record_source_outcome requires exactly a SourceIdLookup (SIP-185 code -> db id), "
            f"got {type(source_id_lookup).__name__} - source_library.name is not unique across "
            "jurisdictions, so anything other than the exact required type risks silently "
            "resolving a source check to the wrong id instead of failing loudly"
        )

    db_id = source_id_lookup.get(source_id)
    if not db_id:
        raise SourceIdUnresolved(
            f"no source_library id for {source_id!r}; source_checks.source_id is required "
            "(database/schema.sql) and source_id_lookup did not resolve it - the source may not "
            "be seeded in source_library yet, or its sip185_code doesn't match the v1.0 register"
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
