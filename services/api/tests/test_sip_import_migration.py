"""Forward-only upgrade test for already-applied SIP import evidence 0008 (#531).

An isolated temporary table models 0008's columns before 0009 adds raw articles.
It never writes to production evidence, nor to any persistent table.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg.types.json import Jsonb

DATABASE_URL = os.environ.get("DATABASE_URL")
_MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "database/migrations/0009_sip_original_articles_forward.sql"
)

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="SIP upgrade tests require real PostgreSQL"
)


def test_0009_upgrades_already_applied_0008_without_rewriting_legacy_evidence():
    migration = _MIGRATION.read_text(encoding="utf-8")
    legacy_run = uuid.uuid4()
    new_run = uuid.uuid4()
    with psycopg.connect(DATABASE_URL) as conn:
        # TEMP has precedence in search_path for unqualified table names.
        # Represents the old 0008 physical layout (no raw_articles yet).
        conn.execute(
            "create temporary table sip_import_evidence ("
            "run_id uuid primary key, articles_sha256 text not null, "
            "batch_payload jsonb not null, captured_articles jsonb not null, "
            "source_count integer not null, evidence_ref text not null, "
            "staged_by uuid not null) on commit preserve rows"
        )
        conn.execute(
            "insert into sip_import_evidence "
            "(run_id, articles_sha256, batch_payload, captured_articles, "
            "source_count, evidence_ref, staged_by) "
            "values (%s, %s, %s, %s, %s, %s, %s)",
            (legacy_run, "a" * 64, Jsonb({}), Jsonb([{"url": "https://example.org"}]),
             112, "legacy synthetic only", uuid.uuid4()),
        )
        # Applying 0009 twice is safe for a fresh schema and for replay checks.
        conn.execute(migration)
        conn.execute(migration)

        legacy = conn.execute(
            "select raw_articles from sip_import_evidence where run_id = %s",
            (legacy_run,),
        ).fetchone()
        assert legacy == (None,)  # no fabricated backfill of earlier evidence

        with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
            conn.execute(
                "insert into sip_import_evidence "
                "(run_id, articles_sha256, batch_payload, captured_articles, "
                "source_count, evidence_ref, staged_by) "
                "values (%s, %s, %s, %s, %s, %s, %s)",
                (uuid.uuid4(), "b" * 64, Jsonb({}), Jsonb([{"url": "https://a.org"}]),
                 112, "new missing evidence", uuid.uuid4()),
            )
        for invalid in ([], {"not": "an array"}):
            with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
                conn.execute(
                    "insert into sip_import_evidence "
                    "(run_id, articles_sha256, batch_payload, captured_articles, "
                    "raw_articles, source_count, evidence_ref, staged_by) "
                    "values (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (uuid.uuid4(), "b" * 64, Jsonb({}), Jsonb([{"url": "https://a.org"}]),
                     Jsonb(invalid), 112, "invalid synthetic evidence", uuid.uuid4()),
                )
        original = [{"title": "Unchanged synthetic article", "url": "https://example.org"}]
        conn.execute(
            "insert into sip_import_evidence "
            "(run_id, articles_sha256, batch_payload, captured_articles, "
            "raw_articles, source_count, evidence_ref, staged_by) "
            "values (%s, %s, %s, %s, %s, %s, %s, %s)",
            (new_run, "c" * 64, Jsonb({}), Jsonb([{"url": "https://example.org"}]),
             Jsonb(original), 112, "new synthetic evidence", uuid.uuid4()),
        )
        assert conn.execute(
            "select raw_articles from sip_import_evidence where run_id = %s",
            (new_run,),
        ).fetchone()[0] == original
