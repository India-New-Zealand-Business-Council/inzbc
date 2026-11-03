"""Pure SIP staging-handoff validation; no DB writes, API or authority (#536).

All source-library and run data MUST be fetched by a separately authenticated,
server-owned handler. A caller-supplied packet or digest is never custody proof.
This module deliberately cannot stage evidence or import candidates.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

from apps.sip.collector.capture_manifest import _canonical_bytes, validate_capture
from apps.sip.collector.import_capture import _run_window
from apps.sip.collector.mapping import parse_published_at
from apps.sip.collector.source_lookup import build_source_lookups
from apps.sip.collector.source_register import MANDATORY_SOURCES
from services.api.import_contract import ImportBatchIn, require_consistent_batch

_MAX_BYTES = 10 * 1024 * 1024


def verify_handoff(
    packet: dict,
    original_manifest_bytes: bytes,
    *,
    server_run: dict,
    server_source_library: list[dict],
) -> dict:
    """Cross-check packet against independently retrieved run/source evidence.

    Returns only non-sensitive metadata. Never returns validated articles for
    direct storage: a separate reviewed custody/authorisation process must
    hold the original bytes and stage immutable evidence in one transaction.
    """
    if not isinstance(original_manifest_bytes, bytes):
        raise TypeError("original capture must be raw bytes from trusted custody")
    if not original_manifest_bytes or len(original_manifest_bytes) > _MAX_BYTES:
        raise ValueError("original capture must be bounded and nonempty")
    if not isinstance(packet, dict) or not isinstance(server_run, dict):
        raise TypeError("packet and server run must be mappings")
    if not isinstance(server_source_library, list):
        raise TypeError("server source library must be a list")

    manifest_hash = hashlib.sha256(original_manifest_bytes).hexdigest()
    if packet.get("manifest_file_sha256") != manifest_hash:
        raise ValueError("original file checksum differs from review packet")
    try:
        manifest = json.loads(original_manifest_bytes)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("original capture JSON is invalid") from exc
    checked = validate_capture(manifest)
    if checked.gaps or not manifest["articles"]:
        raise ValueError("original capture is incomplete")
    originals = manifest["articles"]
    if (
        packet.get("raw_articles") != originals
        or packet.get("articles_sha256") != checked.articles_sha256
        or hashlib.sha256(_canonical_bytes(originals)).hexdigest()
        != checked.articles_sha256
    ):
        raise ValueError("packet original articles differ from reviewed capture")

    if packet.get("status") != "REVIEW_ONLY_NO_WRITE":
        raise ValueError("unrecognised review packet status")
    batch = ImportBatchIn.model_validate(packet.get("batch_payload"))
    if (
        packet.get("run_id") != str(batch.run_id)
        or packet.get("claim_key") != batch.claim_key
        or packet.get("candidate_count") != len(batch.candidates)
        or packet.get("source_count") != 112
        or batch.capture_source_count != 112
        or len(batch.candidates) != len(originals)
    ):
        raise ValueError("review packet metadata does not match candidate batch")

    try:
        run_uuid = uuid.UUID(str(server_run["id"]))
        run_version = server_run["version"]
        if type(run_version) is not int or run_version < 0:
            raise ValueError("run version is invalid")
        if (
            run_uuid != batch.run_id
            or packet.get("run_number") != server_run["run_number"]
            or server_run["state"] != "Scanning"
        ):
            raise ValueError("server run identity/state mismatch")
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("server run snapshot is incomplete") from exc
    start, end = _run_window(server_run)

    # Exact approved mandatory SIP-185 register, from server-held source rows.
    # A source label might be duplicated between countries; never pick one.
    normalised = []
    for row in server_source_library:
        if not isinstance(row, dict) or not row.get("id"):
            raise ValueError("invalid server source library entry")
        normalised.append({**row, "id": str(row["id"])})
    mandatory = [row for row in normalised if row.get("mandatory") is True]
    approved = {entry.source_id for entry in MANDATORY_SOURCES}
    if (
        len(approved) != 112
        or len(mandatory) != 112
        or {row.get("sip185_code") for row in mandatory} != approved
        or any(row.get("active") is not True for row in mandatory)
    ):
        raise ValueError("server mandatory SIP-185 register is incomplete")
    name_lookup, _ = build_source_lookups(normalised)

    captured = packet.get("captured_articles")
    if not isinstance(captured, list) or len(captured) != len(originals):
        raise ValueError("review capture projections are incomplete")
    original_by_url = {}
    for article, resolved in zip(originals, captured, strict=True):
        if not isinstance(resolved, dict):
            raise TypeError("malformed captured article projection")
        source_name = article["source"].strip()
        db_id = name_lookup.get(source_name)
        if db_id is None:
            raise ValueError("original publisher source cannot be unambiguously resolved")
        if (
            article["url"] != resolved.get("url")
            or str(db_id) != str(resolved.get("source_id"))
        ):
            raise ValueError("resolved source or URL differs from server source library")
        published = parse_published_at(article.get("published"))
        if published is None:
            raise ValueError("original publication time is missing")
        try:
            original_time = datetime.fromisoformat(published)
            projected_time = datetime.fromisoformat(resolved["published_at"])
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("invalid original publication projection") from exc
        if (
            original_time.tzinfo is None
            or original_time.utcoffset() is None
            or projected_time.tzinfo is None
            or projected_time.utcoffset() is None
        ):
            raise ValueError("original publication projection requires timezone")
        if original_time.astimezone(UTC) != projected_time.astimezone(UTC):
            raise ValueError("original publication time changed in review packet")
        if article["url"] in original_by_url:
            raise ValueError("duplicate original URL")
        original_by_url[article["url"]] = (uuid.UUID(str(db_id)), original_time)

    article_by_url = {article["url"]: article for article in originals}
    for candidate in batch.candidates:
        source_article = article_by_url.get(candidate.url)
        if source_article is None or (
            candidate.headline != source_article["title"]
            or candidate.summary != (source_article.get("description") or None)
        ):
            raise ValueError("candidate text differs from original collector data")

    require_consistent_batch(
        batch,
        run_id=run_uuid,
        run_version=run_version,
        state=server_run["state"],
        existing_count=0,  # read-only preview, not a transactional count claim
        capture_digest=checked.articles_sha256,
        locked_window_start=start,
        locked_window_end=end,
        captured_articles=original_by_url,
    )
    return {
        "status": "VERIFIED_HANDOFF_ONLY_NOT_STAGED",
        "run_id": str(run_uuid),
        "candidate_count": len(batch.candidates),
        "articles_sha256": checked.articles_sha256,
        "manifest_file_sha256": manifest_hash,
        "launch_authority_verified": False,
        "source_rights_verified": False,
        "mandatory_source_outcomes_verified": False,
        "server_evidence_staged": False,
        "import_executed": False,
    }
