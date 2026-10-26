"""Operator-controlled ingestion of a verified news-agent capture into an EXISTING SIP run.

No run creation, run transition, SIP-185 decision, assessment, approval, or distribution.
Dry-run preview is the default. A real write requires exact run confirmation,
human SIP-191 confirmation, an authenticated Analyst session, and 112 source checks.
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

from .capture_manifest import validate_file
from .mapping import map_article, parse_published_at
from .source_lookup import build_source_lookups
from .source_register import MANDATORY_SOURCES, missing_mandatory_outcomes

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
    if (start_local.hour, start_local.minute, end_local.hour, end_local.minute) != (7, 0, 7, 0):
        raise ValueError("run must use SIP-184 local 07:00-to-07:00 boundaries")
    if (end_local.date() - start_local.date()).days != 1:
        raise ValueError("run must span exactly one local calendar day")
    if (end.astimezone(UTC) - start.astimezone(UTC)).total_seconds() != 86400:
        raise ValueError(
            "DST SOP conflict: local 07:00 boundaries are not 24 elapsed hours; "
            "obtain an approved SIP-184 interpretation before importing"
        )
    return start, end


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
        if not isinstance(row.get("notes"), str) or not row["notes"].strip():
            raise ValueError(f"mandatory SIP-185 source {code} has no evidence notes")
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
    validation = validate_file(capture_file)
    if validation.gaps:
        raise ValueError("collection has incomplete fetch coverage; reconcile before import")
    with capture_file.open(encoding="utf-8") as handle:
        capture = json.load(handle)
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
    """Explicit operator-only write; partial failures are reported, never concealed."""
    if confirmed_run_number != plan.run_number or not sip191_reviewed:
        raise ValueError("exact run number and reviewed SIP-191 authority are required")
    current = client.get_run(plan.run_id)
    if (current.get("state") != "Scanning"
            or current.get("run_number") != plan.run_number):
        raise ValueError("run changed after preflight; aborting import")
    if client.list_candidates(plan.run_id):
        raise ValueError("run now contains candidates; aborting to prevent duplicates")
    created: list[str] = []
    for candidate in plan.candidates:
        try:
            row = client.create_candidate(candidate)
        except Exception as error:
            # HTTP capture has no batch transaction; expose partial writes and stop.
            raise RuntimeError(
                f"capture stopped after {len(created)} writes; reconcile run {plan.run_id} "
                "before any retry"
            ) from error
        created.append(str(row["id"]))
    return {
        "created": len(created),
        "run_id": plan.run_id,
        "run_number": plan.run_number,
        "articles_sha256": plan.article_checksum,
        "note": "Capture only. Scoring, SIP-185 decisions, QA and distribution are separate.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-run-number")
    parser.add_argument("--confirm-sip191-reviewed", action="store_true")
    args = parser.parse_args(argv)
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
    if args.apply:
        if not args.confirm_run_number or not args.confirm_sip191_reviewed:
            parser.error("--apply requires exact --confirm-run-number and "
                         "--confirm-sip191-reviewed")
        result = apply_capture(
            client, plan, confirmed_run_number=args.confirm_run_number,
            sip191_reviewed=args.confirm_sip191_reviewed,
        )
    else:
        result = plan.summary()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
