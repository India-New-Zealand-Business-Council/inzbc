"""Builds the two `GET /api/source-library` lookups the collector needs.

`schemas/api-contract.md`: the endpoint returns `id`, `sip185_code`, `name` rows.
`sip185_code` is authoritative for source-check resolution; `name` is display/candidate-capture
only and is NOT unique (both NZ and India have a "Ministry of Defence") — never resolve a
source-check by name. `SourceNameLookup`/`SourceIdLookup` are distinct types, not interchangeable
dicts, precisely so a caller can't pass a name-keyed map into the id-keyed coverage gate: the two
keyspaces only rarely collide, so that mistake would silently look like most mandatory sources are
missing rather than fail loudly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class SourceNameLookup:
    """Article source name (`article["source"]`, e.g. "RNZ Business") -> `source_library.id`.

    For `mapping.map_article`/`map_articles` and `ingest.ingest_articles`. `name` is not unique
    across jurisdictions, so this is only safe for candidate capture (`candidates.source_id` is
    nullable — an unmatched or ambiguous name degrades to unset, not a wrong source).

    Keys are stored and looked up stripped, matching `mapping.map_article`'s
    `str(article.get("source", "")).strip()` - a lookup built from unstripped keys would let two
    whitespace-differing rows both survive `build_source_lookups`' dedup (they compare unequal) and
    then resolve a stripped query to whichever raw key happened to match, silently reintroducing
    the wrong-jurisdiction bug the dedup exists to prevent.

    `frozen=True` only stops `_by_name` being rebound to a different dict, not the dict's contents
    being mutated through a caller's reference to the same object - `__post_init__` stores a copy
    so `SourceNameLookup(shared_dict)` can't be mutated out from under it later.
    """

    _by_name: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_by_name", dict(self._by_name))

    def get(self, name: str) -> str | None:
        return self._by_name.get(name.strip())


class DuplicateSip185Code(ValueError):
    """Raised when a `GET /api/source-library` response has two rows with the same
    `sip185_code`. `source_library.sip185_code` is declared `unique` (`database/schema.sql`), so a
    healthy database cannot produce this - it only happens on malformed endpoint data, and since
    this code resolves a NOT NULL, jurisdiction-sensitive column (`source_checks.source_id`),
    silently keeping one of the two rows (last write wins) risks resolving to the wrong
    jurisdiction rather than surfacing that the register or the seed is broken.
    """


@dataclass(frozen=True)
class SourceIdLookup:
    """SIP-185 code (e.g. "NZ-OFF-001") -> `source_library.id`.

    For `source_register.record_source_outcome`: `source_checks.source_id` is NOT NULL
    (`database/schema.sql`), so this lookup must be unambiguous — `sip185_code` is unique per the
    schema, `name` is not.
    """

    _by_code: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_by_code", dict(self._by_code))

    def get(self, sip185_code: str) -> str | None:
        return self._by_code.get(sip185_code)


def build_source_lookups(records: Iterable[dict]) -> tuple[SourceNameLookup, SourceIdLookup]:
    """Splits one `GET /api/source-library` response into both lookups.

    Each record is `{"id": ..., "sip185_code": ... | None, "name": ...}`. `sip185_code` is
    nullable in the schema (non-register sources can exist in `source_library`), so a record
    without one is included in the name lookup but simply absent from the id lookup.

    A name shared by more than one record (`data/sip185_sources_v1.0.csv` has two: "Ministry of
    Defence" and "Ministry of Education", once each for NZ and India) is dropped from the name
    lookup entirely rather than resolving to whichever record was seen last - the same defect
    class `source_register`'s id-keyed coverage gate exists to avoid, just on the name side. A
    dict built in a single pass (`by_name[name] = id`) would let the last record silently win,
    turning "ambiguous" into "wrong jurisdiction" instead of "unset" - so names are counted first,
    and only names seen exactly once are kept. Names are stripped before counting and keying, to
    match `SourceNameLookup.get`'s stripped lookup - counting raw names would let two
    whitespace-differing rows both look unique and survive the dedup.

    A `sip185_code` shared by more than one record raises `DuplicateSip185Code` instead of
    keeping the last row: the schema declares it `unique`, so this can only mean malformed
    endpoint data, and this lookup resolves a NOT NULL, jurisdiction-sensitive column - silently
    picking one of two conflicting rows is worse than refusing to build the lookup at all.
    """
    records = list(records)
    name_counts: dict[str, int] = {}
    for record in records:
        name = record.get("name")
        if name:
            name_counts[name.strip()] = name_counts.get(name.strip(), 0) + 1

    by_name: dict[str, str] = {}
    by_code: dict[str, str] = {}
    for record in records:
        source_id = record["id"]
        name = record.get("name")
        if name:
            stripped = name.strip()
            if name_counts[stripped] == 1:
                by_name[stripped] = source_id
        code = record.get("sip185_code")
        if code:
            if code in by_code:
                raise DuplicateSip185Code(
                    f"sip185_code {code!r} appears on more than one source_library row - "
                    "sip185_code is declared unique in database/schema.sql, so this means the "
                    "register or the seed data is broken, not that one row should silently win"
                )
            by_code[code] = source_id
    return SourceNameLookup(by_name), SourceIdLookup(by_code)
