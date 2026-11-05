"""Real-Postgres regression for the inert SIP import transaction (#528).

All evidence and article data here are SYNTHETIC; setting runs.state directly
is a fixture shortcut, NOT authority for a live SIP-184 run.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import psycopg
import pytest
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from apps.sip.collector.capture_manifest import _canonical_bytes
from apps.sip.collector.import_capture import CapturePlan
from apps.sip.collector.review_packet import review_packet
from apps.sip.collector.source_register import MANDATORY_SOURCES
from apps.sip.pipeline.models import Candidate
from services.api.atomic_import import ImportBlockedError, ImportRepository
from services.api.import_contract import ImportBatchIn
from services.api.sip_staging_preflight import verify_handoff
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
    source_ids, *, launch=True, checks=112, candidate_source=None, candidates=1,
    raw_title=None, raw_digest_override=None, source_name="Synthetic Feed",
    window_start=START, window_end=END,
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
                window_start, window_end, person,
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
    raw_articles = [
        {
            "title": raw_title if raw_title is not None and index == 0
                     else row["headline"],
            "description": row["summary"],
            "url": row["url"],
            "source": source_name,
            "published": row["published_at"],
        }
        for index, row in enumerate(rows)
    ]
    digest = hashlib.sha256(_canonical_bytes(raw_articles)).hexdigest()
    payload = {
        "run_id": str(run_id),
        "articles_sha256": raw_digest_override or digest,
        "expected_run_version": 0,
        "capture_source_count": 112,
        "candidates": rows,
    }
    batch = ImportBatchIn.model_validate(payload)
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "insert into sip_import_evidence "
            "(run_id, articles_sha256, batch_payload, captured_articles, raw_articles, "
            "source_count, evidence_ref, staged_by) "
            "values (%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                run_id, batch.articles_sha256, Jsonb(batch.model_dump(mode="json")),
                Jsonb([
                    {"url": row["url"], "source_id": row["source_id"],
                     "published_at": row["published_at"]}
                    for row in rows
                ]),
                Jsonb(raw_articles),
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


def test_original_article_headline_substitution_is_blocked(mandatory_sources):
    batch, actor = seed_case(mandatory_sources, raw_title="Changed original title")
    with pytest.raises(ImportBlockedError, match="candidate text differs"):
        ImportRepository(DATABASE_URL).import_reviewed(batch, actor_id=actor)
    assert counts(batch.run_id) == (0, 0, 0)


def test_original_article_checksum_mismatch_is_blocked(mandatory_sources):
    batch, actor = seed_case(mandatory_sources, raw_digest_override="a" * 64)
    with pytest.raises(ImportBlockedError, match="original article checksum mismatch"):
        ImportRepository(DATABASE_URL).import_reviewed(batch, actor_id=actor)
    assert counts(batch.run_id) == (0, 0, 0)


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


def test_preflight_cannot_authorise_later_write(mandatory_sources):
    """A valid read-only snapshot cannot override newly committed DB state."""
    from services.api.import_contract import require_consistent_batch

    batch, actor = seed_case(mandatory_sources)
    candidate = batch.candidates[0]

    # What an earlier read-only verification can establish, before any write.
    require_consistent_batch(
        batch,
        run_id=batch.run_id,
        run_version=batch.expected_run_version,
        state="Scanning",
        existing_count=0,
        capture_digest=batch.articles_sha256,
        locked_window_start=START,
        locked_window_end=END,
        captured_articles={
            candidate.url: (candidate.source_id, candidate.published_at)
        },
    )

    # An independently committed capture arrives after that valid preview.
    # Use a direct synthetic fixture insert rather than enabling the legacy
    # production route, which must remain unavailable.
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "insert into candidates "
            "(run_id, headline, source_id, url, summary, published_at, "
            "in_coverage_window, captured_by) "
            "values (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                batch.run_id, "Synthetic interleaving capture",
                candidate.source_id, "https://example.org/interleaving-" + str(uuid.uuid4()),
                "Synthetic race fixture", candidate.published_at,
                True, uuid.UUID(actor),
            ),
        )

    # The importer must independently obtain the current count under the
    # run lock and refuse; the earlier preflight grants no write permission.
    with pytest.raises(ValueError, match="existing candidates"):
        ImportRepository(DATABASE_URL).import_reviewed(batch, actor_id=actor)
    assert counts(batch.run_id) == (1, 0, 0)


def test_collector_to_importer_full_synthetic_path(mandatory_sources, tmp_path):
    """One real-PostgreSQL exercise of packet, preflight and locked import."""
    # Use a uniquely named registered source so the independently fetched
    # source library can resolve a publisher without guessing between countries.
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        source = conn.execute(
            "select s.id, s.name from source_library s "
            "where s.mandatory = true and s.active = true "
            "and (select count(*) from source_library t where t.name = s.name) = 1 "
            "order by s.sip185_code limit 1"
        ).fetchone()
    assert source is not None, "synthetic test requires an unambiguous registered source"
    first = source["id"]
    ordered = [first, *(sid for sid in mandatory_sources if sid != first)]
    window_start = datetime(2026, 10, 26, 18, tzinfo=UTC)  # 07:00 NZDT
    window_end = datetime(2026, 10, 27, 18, tzinfo=UTC)
    batch, actor = seed_case(
        ordered, source_name=source["name"],
        window_start=window_start, window_end=window_end,
    )

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        raw_articles = conn.execute(
            "select raw_articles from sip_import_evidence where run_id = %s",
            (batch.run_id,),
        ).fetchone()["raw_articles"]
        run = conn.execute(
            "select id, run_number, version, state, "
            "coverage_start_utc, coverage_end_utc from runs where id = %s",
            (batch.run_id,),
        ).fetchone()
        sources = conn.execute(
            "select id, sip185_code, name, mandatory, active from source_library"
        ).fetchall()

    manifest = {
        "schema_version": 1,
        "kind": "INZBC_SIP_REVIEW_CAPTURE",
        "production_run": False,
        "sip185_outcomes_confirmed": False,
        "locked_sip184_window": False,
        "fetch_started_utc": "2026-10-27T03:00:00+00:00",
        "fetch_finished_utc": "2026-10-27T03:01:00+00:00",
        "rolling_fetch_hours": 24,
        "raw_article_count": len(raw_articles),
        "article_count": len(raw_articles),
        "coverage_state": "observed",
        "coverage_gaps": [],
        "source_fetch_health": {
            source["name"]: {
                "fetch_outcome": "ok", "queries_failed": 0, "queries_total": 1,
            }
        },
        "articles": raw_articles,
        "articles_sha256": batch.articles_sha256,
    }
    original_path = tmp_path / "synthetic-collector-capture.json"
    original_path.write_text(json.dumps(manifest), encoding="utf-8")
    candidate = batch.candidates[0]
    plan = CapturePlan(
        run_id=str(batch.run_id),
        run_number=run["run_number"],
        article_count=len(raw_articles),
        article_checksum=batch.articles_sha256,
        candidates=(
            Candidate(
                run_id=str(batch.run_id),
                source_id=str(candidate.source_id),
                headline=candidate.headline,
                url=candidate.url,
                summary=candidate.summary,
                published_at=candidate.published_at.isoformat(),
                in_coverage_window=True,
            ),
        ),
    )
    packet = review_packet(plan, original_path, expected_run_version=run["version"])
    preflight = verify_handoff(
        packet, original_path.read_bytes(),
        server_run={
            **run,
            "coverage_start_utc": run["coverage_start_utc"].isoformat(),
            "coverage_end_utc": run["coverage_end_utc"].isoformat(),
        },
        server_source_library=sources,
    )
    assert preflight["status"] == "VERIFIED_HANDOFF_ONLY_NOT_STAGED"
    assert preflight["server_evidence_staged"] is False
    assert preflight["import_executed"] is False
    assert packet["raw_articles"] == raw_articles
    assert packet["batch_payload"] == batch.model_dump(mode="json")

    # The independent, pre-existing synthetic DB fixture contains the
    # immutable evidence and 112 confirmed checks. Preflight does not write
    # it. The importer must still recheck every invariant inside its lock.
    outcome = ImportRepository(DATABASE_URL).import_reviewed(batch, actor_id=actor)
    assert not outcome.replay
    assert outcome.candidate_count == 1
    assert counts(batch.run_id) == (1, 1, 1)
