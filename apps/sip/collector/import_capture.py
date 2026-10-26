"""Operator-only, read-only preflight for a captured SIP run (#55).

There is NO production write path in this module. Server-side transactional
import/idempotency is missing, so candidate POST loops are deliberately disabled.
The preflight cannot authorise SIP-191, score, publish, or infer SIP-185 outcomes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from apps.sip.pipeline.client import SipPipelineClient
from apps.sip.pipeline.models import Candidate, SourceOutcome

from .capture_manifest import validate_capture
from .mapping import map_article, parse_published_at
from .source_lookup import build_source_lookups
from .source_register import FALLBACK_SEQUENCE, MANDATORY_SOURCES, missing_mandatory_outcomes

_AUCKLAND = ZoneInfo("Pacific/Auckland")
_RUN_NUMBER = re.compile(r"RUN-[0-9]{8}-[0-9]{2}\Z")
_SOURCE_OUTCOMES = frozenset(item.value for item in SourceOutcome)


@dataclass(frozen=True)
class CapturePlan:
    run_id: str
    run_number: str
    article_count: int
    article_checksum: str
    candidates: tuple[Candidate, ...]

    def summary(self) -> dict:
        return {
            "mode": "preview-only",
            "run_id": self.run_id,
            "run_number": self.run_number,
            "candidate_count": self.article_count,
            "articles_sha256": self.article_checksum,
            "preflight_passed": True,
            "production_run_executed": False,
            "operator_approval_recorded": False,
            "note": (
                "Preflight is not human launch authority. No candidates have been "
                "created and no SIP-185 outcomes have been inferred."
            ),
        }


def _run_window(run: dict) -> tuple[datetime, datetime]:
    try:
        start = datetime.fromisoformat(run["coverage_start_utc"])
        end = datetime.fromisoformat(run["coverage_end_utc"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("run has no valid locked coverage timestamps") from error
    if (start.tzinfo is None or end.tzinfo is None
            or start.utcoffset() is None or end.utcoffset() is None):
        raise ValueError("run coverage timestamps must be timezone aware")
    if not start < end:
        raise ValueError("run coverage window must be increasing")
    start_local = start.astimezone(_AUCKLAND)
    end_local = end.astimezone(_AUCKLAND)
    if (start_local.hour, start_local.minute, start_local.second, start_local.microsecond) != (7, 0, 0, 0) or (end_local.hour, end_local.minute, end_local.second, end_local.microsecond) != (7, 0, 0, 0):
        raise ValueError("run must use SIP-184 local 07:00-to-07:00 boundaries")
    if (end_local.date() - start_local.date()).days != 1:
        raise ValueError("run must span exactly one local calendar day")
    if (end.astimezone(UTC) - start.astimezone(UTC)).total_seconds() != 86400:
        raise ValueError(
            "DST SOP conflict: local 07:00 boundaries are not 24 elapsed hours; "
            "obtain an approved SIP-184 interpretation before importing"
        )
    return start, end


def _require_confirmed_source_note(row: dict, code: str) -> None:
    """Mirror the BriefBuilderScreen evidence contract instead of trusting free text."""
    notes = row.get("notes")
    prefix, trail_prefix, reason_prefix = (
        "Analyst-confirmed evidence: ", "Fallback trail: ", "Access failure: "
    )
    if not isinstance(notes, str) or not notes.startswith(prefix):
        raise ValueError(f"{code}: expected Analyst-confirmed evidence notes")
    lines = notes.split("\n")
    evidence = lines[0][len(prefix):].strip()
    trail_lines = [line for line in lines[1:] if line.startswith(trail_prefix)]
    reason_lines = [line for line in lines[1:] if line.startswith(reason_prefix)]
    if not evidence or len(trail_lines) != 1 or len(reason_lines) > 1 or len(lines) != 2 + len(reason_lines):
        raise ValueError(f"{code}: incomplete analyst evidence or fallback trail")
    raw_steps = trail_lines[0][len(trail_prefix):]
    steps = [step.strip() for step in raw_steps.split(";") if step.strip()]
    ordered = {step: n for n, step in enumerate(FALLBACK_SEQUENCE)}
    last = -1
    for step in steps:
        location = ordered.get(step, -1)
        if location <= last:
            raise ValueError(f"{code}: invalid SIP-185 fallback sequence")
        last = location
    method = steps[-1] if steps else None
    fallback = any(step != FALLBACK_SEQUENCE[0] for step in steps)
    if row.get("method") != method or row.get("fallback_used") is not fallback:
        raise ValueError(f"{code}: source-check method or fallback flag differs from trail")
    reason = reason_lines[0][len(reason_prefix):].strip() if reason_lines else ""
    requires_reason = row.get("outcome") in {"Inaccessible", "Excluded"} or fallback
    if requires_reason and not reason:
        raise ValueError(f"{code}: fallback/access failure requires recorded reason")
    if row.get("access_error") != (reason if requires_reason else None):
        raise ValueError(f"{code}: access error does not match confirmed reason")


def _checked_source_codes(client: SipPipelineClient, run_id: str) -> set[str]:
    sources = client.get_source_library()
    if not isinstance(sources, list):
        raise TypeError("API source library must be a list")
    _, ids = build_source_lookups(sources)
    required = {}
    for source in MANDATORY_SOURCES:
        db_id = ids.get(source.source_id)
        if db_id is None:
            raise ValueError(f"mandatory SIP-185 source {source.source_id} is not seeded")
        required[db_id] = source.source_id

    checks = client.list_source_checks(run_id)
    if not isinstance(checks, list):
        raise TypeError("source-check response must be a list")
    checked: set[str] = set()
    for row in checks:
        if not isinstance(row, dict):
            raise TypeError("source-check row must be an object")
        if row.get("run_id") != run_id:
            raise ValueError("source check belongs to a different run")
        db_id = row.get("source_id")
        code = required.get(db_id)
        if code is None:
            continue
        if code in checked:
            raise ValueError("duplicate source check for mandatory SIP-185 source")
        if row.get("outcome") not in _SOURCE_OUTCOMES:
            raise ValueError(f"invalid SIP-185 outcome for {code}")
        _require_confirmed_source_note(row, code)
        checked.add(code)
    missing = missing_mandatory_outcomes(checked)
    if missing:
        raise ValueError(
            f"{len(missing)} mandatory SIP-185 outcomes unconfirmed; "
            f"first missing code: {missing[0]}"
        )
    return checked


def prepare_capture(
    client: SipPipelineClient, run_id: str, capture_file: Path
) -> CapturePlan:
    """Read-only verification of existing run, evidence and every candidate."""
    if capture_file.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("capture exceeds 10 MiB safety limit")
    # Parse ONCE. The exact object that passed validation is the object we map.
    with capture_file.open(encoding="utf-8") as handle:
        capture = json.load(handle)
    validation = validate_capture(capture)
    if validation.gaps:
        raise ValueError("collection has incomplete fetch coverage; reconcile before import")
    run = client.get_run(run_id)
    if not isinstance(run, dict) or run.get("id") != run_id:
        raise ValueError("run ID does not match authenticated API response")
    number = run.get("run_number")
    if not isinstance(number, str) or _RUN_NUMBER.fullmatch(number) is None:
        raise ValueError("run number must be a real RUN-YYYYMMDD-NN, never DRYRUN/WALK")
    if run.get("state") != "Scanning":
        raise ValueError("run must already be in authorised Scanning state")
    start, end = _run_window(run)
    _checked_source_codes(client, run_id)
    if client.list_candidates(run_id):
        raise ValueError("run already has candidates; reconcile before importing")

    rows = client.get_source_library()
    name_lookup, _ = build_source_lookups(rows)
    candidates: list[Candidate] = []
    seen_urls: set[str] = set()
    for article in capture["articles"]:
        url = article["url"].strip().lower().rstrip("/")
        if url in seen_urls:
            raise ValueError("duplicate URL within capture; reconcile before importing")
        seen_urls.add(url)
        # No guessed dates. The rolling fetch window is NOT the run's locked interval.
        published = parse_published_at(article.get("published"))
        if published is None:
            raise ValueError("article has unknown publication time")
        published_dt = datetime.fromisoformat(published)
        if published_dt.tzinfo is None or published_dt.utcoffset() is None:
            raise ValueError("article publication time has no timezone")
        if not start <= published_dt <= end or published_dt == end:
            raise ValueError("article outside locked run window; reconcile before importing")
        candidate = map_article(
            article, run_id, name_lookup,
            (start.isoformat(), end.isoformat()),
        ).candidate
        if candidate.source_id is None:
            raise ValueError("article source name is unresolved or ambiguous")
        if candidate.in_coverage_window is not True:
            raise ValueError("candidate could not be placed inside locked window")
        candidates.append(candidate)

    return CapturePlan(
        run_id=run_id,
        run_number=number,
        article_count=len(candidates),
        article_checksum=validation.articles_sha256,
        candidates=tuple(candidates),
    )


def apply_capture(
    client: SipPipelineClient, plan: CapturePlan,
    *, confirmed_run_number: str, sip191_reviewed: bool,
) -> dict:
    """No writes until the SIP API implements an atomic, idempotent import claim."""
    raise RuntimeError(
        "SIP candidate import is disabled: the API lacks a transactionally locked, "
        "idempotent bulk-capture endpoint. A client-side empty-run check cannot "
        "prevent concurrent duplicate writes. Tech-lead API work is required."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-run-number")
    parser.add_argument("--confirm-sip191-reviewed", action="store_true")
    args = parser.parse_args(argv)
    if args.apply:
        parser.error("--apply is unavailable: no server-side atomic/idempotent import endpoint")
    # Auth comes from inherited environment, never command-line arguments or committed files.
    cookie, csrf = os.getenv("SIP_SESSION_COOKIE"), os.getenv("SIP_CSRF_TOKEN")
    if not cookie or not csrf:
        parser.error("set SIP_SESSION_COOKIE and SIP_CSRF_TOKEN in the operator environment")
    endpoint = urlsplit(args.base_url)
    if (endpoint.scheme != "https"
            and not (endpoint.scheme == "http" and endpoint.hostname in {
                "localhost", "127.0.0.1",
            })):
        parser.error("API must be HTTPS or a loopback HTTP development endpoint")
    client = SipPipelineClient(args.base_url, cookie, csrf)
    plan = prepare_capture(client, args.run_id, args.capture)
    result = plan.summary()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
