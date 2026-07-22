"""Checks that SourceLibraryEntry's fields match `source_library`'s columns in schema.sql -
same drift guard test_models.py applies to the enums, applied to this table's shape.
"""

from __future__ import annotations

import re
from pathlib import Path

from apps.sip.pipeline.models import SourceLibraryEntry

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = REPO_ROOT / "database" / "schema.sql"


def _source_library_columns() -> set[str]:
    sql_text = SCHEMA_PATH.read_text(encoding="utf-8")
    match = re.search(r"create table source_library\s*\((.*?)\);", sql_text, re.IGNORECASE | re.DOTALL)
    assert match, "expected a `source_library` table in database/schema.sql"
    columns = set()
    for line in match.group(1).splitlines():
        line = line.strip().rstrip(",")
        if not line:
            continue
        columns.add(line.split()[0])
    return columns


def test_source_library_entry_fields_match_schema_columns() -> None:
    assert set(SourceLibraryEntry.model_fields) == _source_library_columns()


def test_source_library_entry_round_trips_a_row() -> None:
    entry = SourceLibraryEntry(
        id="11111111-1111-1111-1111-111111111111",
        name="MFAT",
        layer=1,
        mandatory=True,
        base_url="https://www.mfat.govt.nz",
        active=True,
    )
    assert entry.name == "MFAT"
    assert entry.fallback_note is None
