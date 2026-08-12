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


def _empty_source_library(conn) -> None:
    """Clear the table, or skip with the reason rather than a raw driver error.

    These tests assert exact row counts after seeding, so they need the table to themselves —
    there is no version of them that tolerates pre-existing rows. But `candidates.source_id` is
    a FK to it, so the delete fails outright against any database that has captured a candidate.

    That is not hypothetical and not a CI concern: CI builds a fresh database per job, while a
    developer who has run `apps/sip/collector/run_dry_run.py` locally (which is the documented
    way to exercise #55) has candidate rows pointing here, and then sees three
    `ForeignKeyViolation` errors from a test file that looks unrelated to what they ran.

    Deleting the referencing candidates instead would silently destroy the evidence from that
    dry run, which is worse than not running. So: skip, and say exactly why and what to do.
    """
    try:
        conn.execute("delete from source_library")
        conn.commit()
    except psycopg.errors.ForeignKeyViolation:
        conn.rollback()
        pytest.skip(
            "this database holds candidates referencing source_library, so the table cannot be "
            "emptied without destroying them - point DATABASE_URL at a fresh database "
            "(schema.sql applied) to run these"
        )


@pytest.fixture(autouse=True)
def _clean_source_library():
    with psycopg.connect(DATABASE_URL) as conn:
        _empty_source_library(conn)
    yield
    with psycopg.connect(DATABASE_URL) as conn:
        _empty_source_library(conn)


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
