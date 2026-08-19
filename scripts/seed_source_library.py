"""Seed `source_library` from the approved SIP-185 v1.0 register (#55).

`database/schema.sql` creates `source_library` empty - nothing ever populated it, so
`GET /api/source-library` (services/api/source_library.py) always returned `[]` and
`source_register.record_source_outcome()` could never resolve a SIP-185 code to a db id (raises
`SourceIdUnresolved` for every one of the 112 mandatory sources). This script is the missing seed
step.

`apps/sip/collector/source_register.py`'s `ALL_SOURCES` is the existing, already-tested loader for
`apps/sip/collector/data/sip185_sources_v1.0.csv` - reused here rather than re-parsing the CSV, so
there is exactly one place that turns the register CSV into source rows.

Idempotent: `ON CONFLICT (sip185_code) DO UPDATE` keyed on the column already declared unique in
`database/schema.sql`, so re-running after the register CSV changes updates existing rows instead
of erroring or duplicating them.
"""

from __future__ import annotations

import os
import sys

import psycopg

from apps.sip.collector.source_register import ALL_SOURCES

_UPSERT = """
insert into source_library (sip185_code, name, layer, mandatory, active)
values (%s, %s, %s, %s, true)
on conflict (sip185_code) do update set
    name = excluded.name,
    layer = excluded.layer,
    mandatory = excluded.mandatory,
    active = true
"""


def main() -> int:
    database_url = os.environ["DATABASE_URL"]
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for source in ALL_SOURCES:
                cur.execute(
                    _UPSERT,
                    (source.source_id, source.name, source.layer, source.mandatory),
                )
        conn.commit()
    print(f"seeded {len(ALL_SOURCES)} source_library rows from the SIP-185 v1.0 register")
    return 0


if __name__ == "__main__":
    sys.exit(main())
