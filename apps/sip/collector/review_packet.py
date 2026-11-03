"""Read-only capture-to-batch review packet for SIP operators (#530).

This never stages, imports, publishes or authorises data. Its output is an
untrusted proposal until a named backend owner independently verifies the
original export, the source-name-to-UUID mapping, and SIP-191 authority.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path

from apps.sip.collector.capture_manifest import validate_capture
from apps.sip.collector.import_capture import CapturePlan
from apps.sip.collector.mapping import parse_published_at
from apps.sip.collector.source_register import MANDATORY_SOURCES
from apps.sip.pipeline.models import VerificationState
from services.api.import_contract import ImportBatchIn

_MAX_MANIFEST_BYTES = 10 * 1024 * 1024


def review_packet(
    plan: CapturePlan, capture_file: Path, *, expected_run_version: int
) -> dict:
    """Prepare a deterministic operator-review packet; perform absolutely no writes.

    The plan is expected to come from `prepare_capture` against an authenticated,
    existing run, but this pure function cannot prove that origin. The backend
    must use its *own* locked run/evidence checks rather than trusting this JSON.
    """
    if type(expected_run_version) is not int or expected_run_version < 0:
        raise ValueError("expected_run_version must be a nonnegative integer")
    if capture_file.stat().st_size > _MAX_MANIFEST_BYTES:
        raise ValueError("capture exceeds 10 MiB safety limit")
    raw = capture_file.read_bytes()
    if len(raw) > _MAX_MANIFEST_BYTES:
        raise ValueError("capture exceeds 10 MiB safety limit")
    snapshot = json.loads(raw.decode("utf-8"))
    verified = validate_capture(snapshot)
    if verified.gaps:
        raise ValueError("collection gaps must be reconciled before review packet")
    articles = snapshot["articles"]
    if (not articles or verified.article_count != plan.article_count
            or plan.article_checksum != verified.articles_sha256
            or len(plan.candidates) != len(articles)):
        raise ValueError("capture plan does not match validated manifest")

    try:
        run_uuid = uuid.UUID(plan.run_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("capture plan run_id must be a UUID") from exc

    proposed = []
    originals = []
    seen_urls: set[str] = set()
    for index, (article, candidate) in enumerate(zip(articles, plan.candidates, strict=True)):
        if candidate.run_id != plan.run_id:
            raise ValueError(f"article {index}: candidate belongs to another run")
        if candidate.url != article["url"] or candidate.headline != article["title"]:
            raise ValueError(f"article {index}: candidate differs from original title or URL")
        if candidate.summary != (article.get("description") or None):
            raise ValueError(f"article {index}: candidate summary differs from original")
        timestamp = parse_published_at(article.get("published"))
        if timestamp is None or candidate.published_at is None:
            raise ValueError(f"article {index}: original publication timestamp is missing")
        if datetime.fromisoformat(candidate.published_at) != datetime.fromisoformat(timestamp):
            raise ValueError(f"article {index}: candidate publication time differs from original")
        if candidate.in_coverage_window is not True:
            raise ValueError(f"article {index}: outside locked run window")
        try:
            resolved_source = uuid.UUID(candidate.source_id or "")
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f"article {index}: source must be a resolved UUID") from exc

        if candidate.url in seen_urls:
            raise ValueError("duplicate original candidate URL")
        seen_urls.add(candidate.url)
        # The capture stage must never smuggle a pre-scored/verified article
        # into an insertion that should start at Unverified.
        if (candidate.verification != VerificationState.UNVERIFIED
                or any(getattr(candidate, field) is not None for field in (
                    "nz_relevance", "india_relevance", "member_relevance",
                    "signal", "confidence", "duplicate_of", "included",
                    "reason", "proposed_routing",
                ))):
            raise ValueError(f"article {index}: capture candidate has assessment data")

        proposed.append({
            "headline": candidate.headline,
            "source_id": str(resolved_source),
            "url": candidate.url,
            "summary": candidate.summary,
            "published_at": candidate.published_at,
            "in_coverage_window": True,
        })
        originals.append({
            "url": article["url"],
            # Mapping is proposed for human reconciliation with source_library;
            # it is not authoritative proof a publisher owns this article.
            "source_id": str(resolved_source),
            "published_at": timestamp,
        })

    batch = ImportBatchIn.model_validate({
        "run_id": str(run_uuid),
        "articles_sha256": verified.articles_sha256,
        "expected_run_version": expected_run_version,
        "capture_source_count": len(MANDATORY_SOURCES),
        "candidates": proposed,
    })
    return {
        "status": "REVIEW_ONLY_NO_WRITE",
        "run_id": str(run_uuid),
        "run_number": plan.run_number,
        "manifest_file_sha256": hashlib.sha256(raw).hexdigest(),
        "articles_sha256": verified.articles_sha256,
        "source_count": len(MANDATORY_SOURCES),
        "candidate_count": len(batch.candidates),
        "claim_key": batch.claim_key,
        "batch_payload": batch.model_dump(mode="json"),
        "captured_articles": originals,
        # Same validated original article objects, not a reconstructed
        # candidate projection. Protected handoff only: source licenses,
        # collector provenance and permission to stage remain independent.
        "raw_articles": articles,
        "operator_notice": (
            "Not SIP-191 authority, not a source-rights or SIP-185 certification, "
            "not a server-held capture, and not a production import."
        ),
    }
