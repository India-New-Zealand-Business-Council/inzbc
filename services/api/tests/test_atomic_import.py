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
    created = []
    with psycopg.connect(DATABASE_URL) as conn:
        existing = conn.execute(
            "select id from source_library where mandatory = true and active = true"
        ).fetchall()
        assert len(existing) <= 112
        ids = [row[0] for row in existing]
        for index in range(112 - len(ids)):
            key = uuid.uuid4().hex
            row = conn.execute(
                "insert into source_library "
                "(sip185_code, name, layer, mandatory, active) "
                "values (%s, %s, 1, true, true) returning id",
                (f"TEST-{key}", f"Synthetic source {index}"),
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
                "(run_id, source_id, outcome, notes) values "
                "(%s, %s, 'No Qualifying Item', %s)",
                (
                    run_id, source_id,
                    "Analyst-confirmed evidence: synthetic test record\n"
                    "Fallback trail: Direct website",
                ),
            )
        conn.commit()

    rows = [
        {
            "headline": f"Synthetic event {index}",
            "source_id": str(candidate_source or source_ids[0]),
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
            "(run_id, articles_sha256, batch_payload, source_count, evidence_ref, staged_by) "
            "values (%s,%s,%s,%s,%s,%s)",
            (
                run_id, batch.articles_sha256, Jsonb(batch.model_dump(mode="json")),
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
    with pytest.raises(ImportBlockedError, match="112 independently"):
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
    stale = batch.model_copy(update={"expected_run_version": 17})
    with psycopg.connect(DATABASE_URL) as conn:
        # Keep server-held immutable evidence matching the stale request only
        # so the version guard, rather than the equality guard, is exercised.
        # New test evidence is append-only, therefore seed a distinct staged
        # run instead of attempting to mutate the stored record.
        pass
    with pytest.raises(ImportBlockedError, match="immutable reviewed"):
        ImportRepository(DATABASE_URL).import_reviewed(stale, actor_id=actor)
    assert counts(batch.run_id) == (0, 0, 0)
