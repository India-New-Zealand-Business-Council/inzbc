"""Integration tests for source_library seeding + the read repository (#55), against a real
Postgres. Skipped without `DATABASE_URL`, same convention as test_persistence.py.
"""

from __future__ import annotations

import os
import subprocess
import sys

import psycopg
import pytest

from apps.sip.collector.source_lookup import build_source_lookups
from apps.sip.collector.source_register import ALL_SOURCES, MANDATORY_SOURCES
from services.api.source_library import SourceLibraryRepository

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - source_library tests need a real Postgres with schema.sql applied",
)


@pytest.fixture(autouse=True)
def _clean_source_library():
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("delete from source_library")
        conn.commit()
    yield
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("delete from source_library")
        conn.commit()


def _run_seed_script() -> None:
    subprocess.run(
        [sys.executable, "scripts/seed_source_library.py"],
        check=True,
        env={**os.environ, "DATABASE_URL": DATABASE_URL},
    )


def test_seed_script_loads_every_register_source() -> None:
    _run_seed_script()
    repo = SourceLibraryRepository(DATABASE_URL)
    rows = repo.list_sources()
    assert len(rows) == len(ALL_SOURCES)
    codes = {row.sip185_code for row in rows}
    assert codes == {s.source_id for s in ALL_SOURCES}


def test_seed_script_is_idempotent() -> None:
    _run_seed_script()
    _run_seed_script()
    repo = SourceLibraryRepository(DATABASE_URL)
    assert len(repo.list_sources()) == len(ALL_SOURCES)


def test_seeded_rows_resolve_every_mandatory_source_via_source_id_lookup() -> None:
    """The end-to-end point of seeding: record_source_outcome must be able to resolve every
    mandatory SIP-185 code to a db id, closing the SourceIdUnresolved gap #55 found.
    """
    _run_seed_script()
    repo = SourceLibraryRepository(DATABASE_URL)
    rows = [{"id": r.id, "sip185_code": r.sip185_code, "name": r.name} for r in repo.list_sources()]
    _name_lookup, id_lookup = build_source_lookups(rows)

    unresolved = [s.source_id for s in MANDATORY_SOURCES if id_lookup.get(s.source_id) is None]
    assert unresolved == []
