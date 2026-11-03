"""Real-Postgres regression for the inert SIP import transaction (#528).

All evidence and article data here are SYNTHETIC; setting runs.state directly
is a fixture shortcut, NOT authority for a live SIP-184 run.
"""
from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import psycopg
import pytest
from psycopg.types.json import Jsonb

from apps.sip.collector.source_register import MANDATORY_SOURCES
from services.api.atomic_import import ImportBlockedError, ImportRepository
from services.api.import_contract import ImportBatchIn
from services.api.tests.role_seed import authorise_run, grant

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="Real Postgres needed for SIP import/replay/concurrency assertions"
)
START = datetime(2026, 10, 27, tzinfo=UTC)
END = datetime(2026, 10, 28, tzinfo=UTC)


@pytest.fixture(scope="module")
def mandatory_sources():
    required = list(MANDATORY_SOURCES)
    assert len(required) == 112
    created = []
    with psycopg.connect(DATABASE_URL) as conn:
        existing = {
            row[1]: row[0]
            for row in conn.execute(
                "select id, sip185_code from source_library where mandatory = true"
            ).fetchall()
        }
        ids = []
        for entry in required:
            if entry.source_id in existing:
                ids.append(existing[entry.source_id])
                continue
            row = conn.execute(
                "insert into source_library "
                "(sip185_code, name, layer, mandatory, active) "
                "values (%s, %s, %s, true, true) returning id",
                (entry.source_id, entry.name, entry.layer),
            ).fetchone()
            created.append(row[0])
            ids.append(row[0])
    yield ids
    if created:
        with psycopg.connect(DATABASE_URL) as conn:
            conn.execute(
                "update source_library set mandatory = false where id = any(%s)",
                (created,),
            )

def seed_case(
    source_ids, *, launch=True, checks=112, candidate_source=None, candidates=1
):
    person = uuid.uuid4()
    run_id = uuid.uuid4()
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "insert into users (id, name, email) values (%s, %s, %s)",
            (person, "Synthetic importer", f"import-{person}@example.com"),
        )
        grant(conn, str(person), "SIP Owner", "Analyst")
        conn.execute(
            "insert into runs "
            "(id, run_number, prompt_version, coverage_start_utc, coverage_end_utc, "
            "initiated_by, state, production_enabled) "
            "values (%s, %s, %s, %s, %s, %s, 'Scanning', true)",
            (
                run_id, f"RUN-TEST-{uuid.uuid4().hex[:12]}", "SIP-050 test",
                START, END, person,
            ),
        )
        conn.commit()
        if launch:
            authorise_run(conn, str(run_id), str(person))
        for source_id in source_ids[:checks]:
            conn.execute(
                "insert into source_checks "
                "(run_id, source_id, outcome, method, notes) values "
                "(%s, %s, 'No Qualifying Item', 'Direct access', %s)",
                (
                    run_id, source_id,
                    "Analyst-confirmed evidence: synthetic test record\nFallback trail: Direct access",
                ),
            )
        conn.commit()

    rows = [
        {
            "headline": f"Synthetic event {index}",
            "source_id": str(
                candidate_source if candidate_source is not None and index == 1
                else source_ids[0]
            ),
            "url": f"https://example.org/test-{uuid.uuid4()}",
            "summary": "synthetic only",
            "published_at": "2026-10-27T02:00:00+00:00",
            "in_coverage_window": True,
        }
        for index in range(candidates)
    ]
    payload = {
        "run_id": str(run_id),
        "articles_sha256": "a" * 64,
        "expected_run_version": 0,
        "capture_source_count": 112,
        "candidates": rows,
    }
    batch = ImportBatchIn.model_validate(payload)
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "insert into sip_import_evidence "
            "(run_id, articles_sha256, batch_payload, captured_articles, "
            "source_count, evidence_ref, staged_by) "
            "values (%s,%s,%s,%s,%s,%s,%s)",
            (
                run_id, batch.articles_sha256, Jsonb(batch.model_dump(mode="json")),
                Jsonb([
                    {"url": row["url"], "source_id": row["source_id"],
                     "published_at": row["published_at"]}
                    for row in rows
                ]),
                112, "SYNTHETIC-ONLY-REVIEW-EVIDENCE", person,
            ),
        )
    return batch, str(person)


def counts(run_id):
    with psycopg.connect(DATABASE_URL) as conn:
        c = conn.execute(
            "select count(*) from candidates where run_id = %s", (str(run_id),)
        ).fetchone()[0]
        claim = conn.execute(
            "select count(*) from sip_import_claims where run_id = %s",
            (str(run_id),),
        ).fetchone()[0]
        audit = conn.execute(
            "select count(*) from audit_log where action = 'candidate.import' "
            "and record_id in (select id::text from candidates where run_id = %s)",
            (str(run_id),),
        ).fetchone()[0]
        return c, claim, audit


def test_single_commit_and_idempotent_replay(mandatory_sources):
    batch, actor = seed_case(mandatory_sources)
    repo = ImportRepository(DATABASE_URL)
    first = repo.import_reviewed(batch, actor_id=actor)
    second = repo.import_reviewed(batch, actor_id=actor)
    assert (first.replay, second.replay) == (False, True)
    assert first.claim_key == second.claim_key == batch.claim_key
    assert first.candidate_count == second.candidate_count == 1
    assert counts(batch.run_id) == (1, 1, 1)
    with psycopg.connect(DATABASE_URL) as conn:
        total = conn.execute(
            "select count(*) from audit_log where action = 'sip.import.commit' "
            "and record_id = %s", (str(batch.run_id),),
        ).fetchone()[0]
    assert total == 1  # A replay must not create a second commit event.


def test_concurrent_separate_connections_are_serialised(mandatory_sources):
    batch, actor = seed_case(mandatory_sources)
    repo = ImportRepository(DATABASE_URL)
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(
            lambda _: repo.import_reviewed(batch, actor_id=actor), range(2)
        ))
    assert sorted(outcome.replay for outcome in results) == [False, True]
    assert counts(batch.run_id) == (1, 1, 1)


def test_missing_run_authorisation_fails_without_side_effects(mandatory_sources):
    batch, actor = seed_case(mandatory_sources, launch=False)
    with pytest.raises(ImportBlockedError, match="launch authority"):
        ImportRepository(DATABASE_URL).import_reviewed(batch, actor_id=actor)
    assert counts(batch.run_id) == (0, 0, 0)


def test_incomplete_mandatory_source_checks_fail_closed(mandatory_sources):
    batch, actor = seed_case(mandatory_sources, checks=111)
    with pytest.raises(ImportBlockedError, match="112 analyst-confirmed"):
        ImportRepository(DATABASE_URL).import_reviewed(batch, actor_id=actor)
    assert counts(batch.run_id) == (0, 0, 0)


def test_request_cannot_change_server_held_capture(mandatory_sources):
    batch, actor = seed_case(mandatory_sources)
    modified = batch.model_copy(update={"articles_sha256": "b" * 64})
    with pytest.raises(ImportBlockedError, match="immutable reviewed"):
        ImportRepository(DATABASE_URL).import_reviewed(modified, actor_id=actor)
    assert counts(batch.run_id) == (0, 0, 0)


def test_second_insert_failure_rolls_back_first_candidate_and_audit(mandatory_sources):
    # Both candidates were staged as reviewed evidence; the second references
    # a source ID absent from source_library, exercising DB FK rollback.
    batch, actor = seed_case(
        mandatory_sources, candidate_source=uuid.uuid4(), candidates=2
    )
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        ImportRepository(DATABASE_URL).import_reviewed(batch, actor_id=actor)
    assert counts(batch.run_id) == (0, 0, 0)


def test_conflicting_digest_cannot_replay_committed_batch(mandatory_sources):
    batch, actor = seed_case(mandatory_sources)
    repo = ImportRepository(DATABASE_URL)
    repo.import_reviewed(batch, actor_id=actor)
    conflicting = batch.model_copy(update={"articles_sha256": "b" * 64})
    with pytest.raises(ImportBlockedError, match="conflicting"):
        repo.import_reviewed(conflicting, actor_id=actor)
    assert counts(batch.run_id) == (1, 1, 1)


def test_stale_run_version_refused(mandatory_sources):
    batch, actor = seed_case(mandatory_sources)
    # The immutable request still asks for version 0; the DB run has moved
    # and must refuse even though all original capture data still agrees.
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "update runs set version = 17 where id = %s", (str(batch.run_id),)
        )
    with pytest.raises(ValueError, match="version changed"):
        ImportRepository(DATABASE_URL).import_reviewed(batch, actor_id=actor)
    assert counts(batch.run_id) == (0, 0, 0)


def test_replay_cannot_change_stored_candidate_with_same_digest(mandatory_sources):
    batch, actor = seed_case(mandatory_sources)
    repo = ImportRepository(DATABASE_URL)
    repo.import_reviewed(batch, actor_id=actor)
    tampered = batch.model_dump(mode="json")
    tampered["candidates"][0]["headline"] = "Tampered candidate with same digest"
    forged = ImportBatchIn.model_validate(tampered)
    assert forged.claim_key == batch.claim_key
    with pytest.raises(ImportBlockedError, match="replayed request"):
        repo.import_reviewed(forged, actor_id=actor)
    assert counts(batch.run_id) == (1, 1, 1)


def test_source_check_with_empty_evidence_cannot_pass_import(mandatory_sources):
    batch, actor = seed_case(mandatory_sources)
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "update source_checks set notes = %s where run_id = %s and source_id = %s",
            ("Analyst-confirmed evidence:  \nFallback trail: Direct access",
             str(batch.run_id), mandatory_sources[0]),
        )
    with pytest.raises(ImportBlockedError, match="invalid recorded source"):
        ImportRepository(DATABASE_URL).import_reviewed(batch, actor_id=actor)
    assert counts(batch.run_id) == (0, 0, 0)


def test_unrecognised_actor_is_refused_before_any_import(mandatory_sources):
    batch, _actor = seed_case(mandatory_sources)
    with pytest.raises(PermissionError, match="active SIP"):
        ImportRepository(DATABASE_URL).import_reviewed(
            batch, actor_id=str(uuid.uuid4()),
        )
    assert counts(batch.run_id) == (0, 0, 0)


def test_run_without_production_enablement_refuses_import(mandatory_sources):
    batch, actor = seed_case(mandatory_sources)
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "update runs set production_enabled=false where id = %s", (str(batch.run_id),)
        )
    with pytest.raises(ImportBlockedError, match="not enabled"):
        ImportRepository(DATABASE_URL).import_reviewed(batch, actor_id=actor)
    assert counts(batch.run_id) == (0, 0, 0)
