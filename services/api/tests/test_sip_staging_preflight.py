"""Synthetic, read-only staging boundary regressions (#536)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from apps.sip.collector.capture_manifest import _canonical_bytes
from apps.sip.collector.import_capture import CapturePlan
from apps.sip.collector.review_packet import review_packet
from apps.sip.collector.source_register import MANDATORY_SOURCES
from apps.sip.pipeline.models import Candidate
from services.api.sip_staging_preflight import verify_handoff


@pytest.fixture
def evidence(tmp_path):
    run_id = str(uuid.uuid4())
    source_id = str(uuid.uuid4())
    article = {
        "title": "Synthetic NZ India trade update",
        "source": "Test Publisher",
        "url": "https://example.org/article-1",
        "description": "Synthetic paragraph, no real source data",
        "published": "2026-10-27T02:00:00+00:00",
    }
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
        "articles_sha256": hashlib.sha256(_canonical_bytes([article])).hexdigest(),
    }
    file_path = tmp_path / "original.json"
    file_path.write_text(json.dumps(manifest), encoding="utf-8")
    candidate = Candidate(
        run_id=run_id,
        source_id=source_id,
        headline=article["title"],
        url=article["url"],
        summary=article["description"],
        published_at=article["published"],
        in_coverage_window=True,
    )
    plan = CapturePlan(
        run_id=run_id,
        run_number="RUN-20261027-01",
        article_count=1,
        article_checksum=manifest["articles_sha256"],
        candidates=(candidate,),
    )
    packet = review_packet(plan, file_path, expected_run_version=4)
    sources = [
        {
            "id": str(uuid.uuid4()),
            "sip185_code": entry.source_id,
            "name": entry.name,
            "mandatory": True,
            "active": True,
        }
        for entry in MANDATORY_SOURCES
    ]
    sources.append({
        "id": source_id, "sip185_code": None,
        "name": article["source"], "mandatory": False, "active": True,
    })
    server_run = {
        "id": run_id,
        "run_number": plan.run_number,
        "version": 4,
        "state": "Scanning",
        "coverage_start_utc": "2026-10-26T18:00:00+00:00",
        "coverage_end_utc": "2026-10-27T18:00:00+00:00",
    }
    return {
        "packet": packet,
        "raw": file_path.read_bytes(),
        "sources": sources,
        "run": server_run,
        "file": file_path,
        "plan": plan,
        "manifest": manifest,
    }


def verify(evidence):
    return verify_handoff(
        evidence["packet"], evidence["raw"],
        server_run=evidence["run"],
        server_source_library=evidence["sources"],
    )


def test_valid_packet_proves_consistency_but_not_authorisation(evidence):
    result = verify(evidence)
    assert result["status"] == "VERIFIED_HANDOFF_ONLY_NOT_STAGED"
    assert result["candidate_count"] == 1
    assert result["articles_sha256"] == evidence["packet"]["articles_sha256"]
    assert not any(result[key] for key in (
        "launch_authority_verified", "source_rights_verified",
        "mandatory_source_outcomes_verified", "server_evidence_staged",
        "import_executed",
    ))
    assert evidence["file"].read_bytes() == evidence["raw"]


def test_raw_manifest_from_different_custody_is_rejected(evidence):
    with pytest.raises(ValueError, match="original file checksum"):
        verify_handoff(
            evidence["packet"], evidence["raw"] + b" ",
            server_run=evidence["run"],
            server_source_library=evidence["sources"],
        )


def test_altered_raw_articles_in_packet_are_rejected(evidence):
    evidence["packet"]["raw_articles"][0]["title"] = "Replaced text"
    with pytest.raises(ValueError, match="original articles differ"):
        verify(evidence)


def test_replaced_candidate_text_is_rejected(evidence):
    evidence["packet"]["batch_payload"]["candidates"][0]["headline"] = "Forged"
    with pytest.raises(ValueError, match="candidate text"):
        verify(evidence)


def test_fake_source_uuid_is_rejected_against_db_mapping(evidence):
    evidence["packet"]["captured_articles"][0]["source_id"] = str(uuid.uuid4())
    with pytest.raises(ValueError, match="resolved source"):
        verify(evidence)


def test_ambiguous_server_source_name_is_rejected(evidence):
    evidence["sources"].append({
        "id": str(uuid.uuid4()), "name": "Test Publisher",
        "sip185_code": None, "active": True, "mandatory": False,
    })
    with pytest.raises(ValueError, match="unambiguously resolved"):
        verify(evidence)


def test_missing_one_mandatory_register_row_fails(evidence):
    evidence["sources"].pop(0)
    with pytest.raises(ValueError, match="mandatory SIP-185 register"):
        verify(evidence)


def test_run_version_change_is_rejected(evidence):
    evidence["run"]["version"] = 5
    with pytest.raises(ValueError, match="version changed"):
        verify(evidence)


def test_locked_window_protects_against_false_coverage_flag(evidence):
    article = evidence["manifest"]["articles"][0]
    article["published"] = "2026-10-28T02:00:00+00:00"
    evidence["manifest"]["articles_sha256"] = hashlib.sha256(
        _canonical_bytes(evidence["manifest"]["articles"])
    ).hexdigest()
    evidence["file"].write_text(json.dumps(evidence["manifest"]), encoding="utf-8")
    new_candidate = evidence["plan"].candidates[0].model_copy(update={
        "published_at": article["published"],
        "in_coverage_window": True,
    })
    plan = replace(
        evidence["plan"],
        article_checksum=evidence["manifest"]["articles_sha256"],
        candidates=(new_candidate,),
    )
    packet = review_packet(plan, evidence["file"], expected_run_version=4)
    with pytest.raises(ValueError, match="outside locked run window"):
        verify_handoff(
            packet, evidence["file"].read_bytes(),
            server_run=evidence["run"],
            server_source_library=evidence["sources"],
        )


def test_wrong_run_identity_refused(evidence):
    evidence["run"]["id"] = str(uuid.uuid4())
    with pytest.raises(ValueError, match="identity/state mismatch"):
        verify(evidence)


def test_naive_source_projection_rejected(evidence):
    evidence["packet"]["captured_articles"][0]["published_at"] = (
        "2026-10-27T02:00:00"
    )
    with pytest.raises(ValueError, match="timezone"):
        verify(evidence)
