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
    """

    _by_name: dict[str, str] = field(default_factory=dict)

    def get(self, name: str) -> str | None:
        return self._by_name.get(name)


@dataclass(frozen=True)
class SourceIdLookup:
    """SIP-185 code (e.g. "NZ-OFF-001") -> `source_library.id`.

    For `source_register.record_source_outcome`: `source_checks.source_id` is NOT NULL
    (`database/schema.sql`), so this lookup must be unambiguous — `sip185_code` is unique per the
    schema, `name` is not.
    """

    _by_code: dict[str, str] = field(default_factory=dict)

    def get(self, sip185_code: str) -> str | None:
        return self._by_code.get(sip185_code)


def build_source_lookups(records: Iterable[dict]) -> tuple[SourceNameLookup, SourceIdLookup]:
    """Splits one `GET /api/source-library` response into both lookups.

    Each record is `{"id": ..., "sip185_code": ... | None, "name": ...}`. `sip185_code` is
    nullable in the schema (non-register sources can exist in `source_library`), so a record
    without one is included in the name lookup but simply absent from the id lookup.
    """
    by_name: dict[str, str] = {}
    by_code: dict[str, str] = {}
    for record in records:
        source_id = record["id"]
        name = record.get("name")
        if name:
            by_name[name] = source_id
        code = record.get("sip185_code")
        if code:
            by_code[code] = source_id
    return SourceNameLookup(by_name), SourceIdLookup(by_code)
