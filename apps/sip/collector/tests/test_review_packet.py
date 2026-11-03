"""Synthetic checks for review-only SIP packet production (#530)."""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from apps.sip.collector import capture_manifest
from apps.sip.collector.import_capture import CapturePlan
from apps.sip.collector.review_packet import review_packet
from apps.sip.pipeline.models import Candidate, SignalStrength
from services.api.import_contract import ImportBatchIn, require_consistent_batch


@pytest.fixture
def prepared(tmp_path):
    run = str(uuid.uuid4())
    source = str(uuid.uuid4())
    article = {
        "title": "Synthetic NZ–India trade document",
        "source": "Test Publisher",
        "url": "https://example.org/article-1",
        "description": "Synthetic public information, no real data",
        "published": "2026-10-27T02:00:00+00:00",
        "sectors": "Trade",
    }
    digest = hashlib.sha256(capture_manifest._canonical_bytes([article])).hexdigest()
    manifest = {
        "schema_version": 1,
        "kind": "INZBC_SIP_REVIEW_CAPTURE",
        "production_run": False,
        "sip185_outcomes_confirmed": False,
        "locked_sip184_window": False,
        "fetch_started_utc": "2026-10-27T03:00:00+00:00",
        "fetch_finished_utc": "2026-10-27T03:01:00+00:00",
        "rolling_fetch_hours": 24,
        "raw_article_count": 1,
        "article_count": 1,
        "coverage_state": "observed",
        "coverage_gaps": [],
        "source_fetch_health": {
            "Test Publisher": {
                "fetch_outcome": "ok", "queries_failed": 0, "queries_total": 1,
            }
        },
        "articles": [article],
        "articles_sha256": digest,
    }
    path = tmp_path / "capture.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    candidate = Candidate(
        run_id=run, source_id=source, headline=article["title"],
        url=article["url"], summary=article["description"],
        published_at=article["published"], in_coverage_window=True,
    )
    plan = CapturePlan(
        run_id=run, run_number="RUN-20261027-01",
        article_count=1, article_checksum=digest, candidates=(candidate,),
    )
    return path, plan


def test_review_packet_is_reconciled_serializable_and_read_only(prepared):
    path, plan = prepared
    before = path.read_bytes()
    packet = review_packet(plan, path, expected_run_version=4)
    assert packet["status"] == "REVIEW_ONLY_NO_WRITE"
    assert packet["candidate_count"] == 1
    assert packet["source_count"] == 112
    assert packet["articles_sha256"] == plan.article_checksum
    assert packet["manifest_file_sha256"] == hashlib.sha256(before).hexdigest()
    assert packet["batch_payload"]["expected_run_version"] == 4
    assert packet["batch_payload"]["run_id"] == plan.run_id
    assert packet["batch_payload"]["candidates"][0]["source_id"] == plan.candidates[0].source_id
    assert packet["captured_articles"][0]["url"] == plan.candidates[0].url
    assert "not a production import" in packet["operator_notice"]
    json.dumps(packet)
    assert path.read_bytes() == before


def test_packet_plus_original_manifest_matches_atomic_evidence_contract(prepared):
    # This tests whether the review packet carries enough data to construct
    # the immutable server evidence requested in #533. It does not stage it.
    path, plan = prepared
    manifest = json.loads(path.read_text(encoding="utf-8"))
    packet = review_packet(plan, path, expected_run_version=4)
    assert packet["raw_articles"] == manifest["articles"]
    assert hashlib.sha256(
        capture_manifest._canonical_bytes(packet["raw_articles"])
    ).hexdigest() == packet["articles_sha256"]

    batch = ImportBatchIn.model_validate(packet["batch_payload"])
    original = {
        row["url"]: (
            uuid.UUID(row["source_id"]),
            datetime.fromisoformat(row["published_at"]),
        )
        for row in packet["captured_articles"]
    }
    require_consistent_batch(
        batch,
        run_id=uuid.UUID(plan.run_id),
        run_version=4,
        state="Scanning",
        existing_count=0,
        capture_digest=packet["articles_sha256"],
        locked_window_start=datetime(2026, 10, 27, tzinfo=UTC),
        locked_window_end=datetime(2026, 10, 28, tzinfo=UTC),
        captured_articles=original,
    )
    assert batch.candidates[0].headline == packet["raw_articles"][0]["title"]
    assert batch.candidates[0].summary == packet["raw_articles"][0]["description"]


def test_packet_cannot_replace_original_article_without_changing_checksum(prepared):
    path, plan = prepared
    packet = review_packet(plan, path, expected_run_version=4)
    copied = json.loads(json.dumps(packet))
    copied["raw_articles"][0]["title"] = "Replacement headline"
    changed_digest = hashlib.sha256(
        capture_manifest._canonical_bytes(copied["raw_articles"])
    ).hexdigest()
    assert changed_digest != copied["articles_sha256"]
    assert copied["batch_payload"]["candidates"][0]["headline"] != copied[
        "raw_articles"
    ][0]["title"]


@pytest.mark.parametrize(("mutation", "message"), [
    ({"url": "https://example.org/other"}, "title or URL"),
    ({"headline": "Different"}, "title or URL"),
    ({"summary": "Changed"}, "summary"),
    ({"published_at": "2026-10-27T04:00:00+00:00"}, "publication time"),
    ({"source_id": "not-a-uuid"}, "resolved UUID"),
    ({"in_coverage_window": None}, "outside locked"),
    ({"signal": SignalStrength.HIGH}, "assessment data"),
    ({"run_id": str(uuid.UUID(int=42))}, "another run"),
])
def test_rejects_candidate_inconsistent_with_manifest(prepared, mutation, message):
    path, plan = prepared
    altered = plan.candidates[0].model_copy(update=mutation)
    with pytest.raises(ValueError, match=message):
        review_packet(replace(plan, candidates=(altered,)), path, expected_run_version=4)


def test_rejects_original_manifest_tampering_after_preflight(prepared):
    path, plan = prepared
    modified = json.loads(path.read_text(encoding="utf-8"))
    modified["articles"][0]["title"] = "Replaced outside preflight"
    path.write_text(json.dumps(modified), encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        review_packet(plan, path, expected_run_version=4)


def test_rejects_manifest_that_validates_but_differs_from_plan(prepared):
    path, plan = prepared
    modified = json.loads(path.read_text(encoding="utf-8"))
    modified["articles"][0]["title"] = "New valid title"
    modified["articles_sha256"] = hashlib.sha256(
        capture_manifest._canonical_bytes(modified["articles"])
    ).hexdigest()
    path.write_text(json.dumps(modified), encoding="utf-8")
    with pytest.raises(ValueError, match="capture plan does not match"):
        review_packet(plan, path, expected_run_version=4)


@pytest.mark.parametrize("version", [-1, True, "4", None])
def test_invalid_run_version_refused(prepared, version):
    path, plan = prepared
    with pytest.raises(ValueError, match="expected_run_version"):
        review_packet(plan, path, expected_run_version=version)


def test_rejects_unreconciled_source_fetch_failures(prepared):
    path, plan = prepared
    modified = json.loads(path.read_text(encoding="utf-8"))
    modified["source_fetch_health"]["Test Publisher"].update(
        fetch_outcome="partial", queries_failed=1, queries_total=2
    )
    modified["coverage_state"] = "incomplete"
    modified["coverage_gaps"] = ["Test Publisher"]
    path.write_text(json.dumps(modified), encoding="utf-8")
    with pytest.raises(ValueError, match="gaps must be reconciled"):
        review_packet(plan, path, expected_run_version=4)
