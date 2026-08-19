"""Unauthorised dry run of the collector -> capture pipeline (#55).

**Not a SIP-184 production run.** SIP-191's launch window was 27-31 Jul 2026
(`docs/sip/launch/launch-config.md`) and has expired with no re-approval on record; SIP-184 step 1
and its fail-closed list both treat a run outside authorised window/authority as a Critical stop.
This script exists to prove the *code path* works end-to-end against a real backend, not to
produce a record for the Production Run Register. `run_number` is stamped `DRYRUN-...` rather
than `RUN-...` so a dry-run row can never be mistaken for an authorised one if it ever ends up in
a real database.

`GET /api/source-library` (`services/api/source_library.py`), its seed step
(`scripts/seed_source_library.py`), and `POST .../source-checks`
(`services/api/source_checks.py`) are now all built. This script deliberately still does not call
`record_source_check` for any of the 112 real mandatory sources: nobody actually checked them for
this run, and writing "Included"/"Excluded" outcomes against the real SIP-185 register for sources
that were never visited would be inventing data into a real, writable system - the same rule
`CLAUDE.md` states for statistics and board names applies here. `source_checks` reports as
`missing` for every mandatory source, which is the honest state. `apply_candidate_assessment`
(SIP-184 steps 6-7 scoring) is left out for the same reason - no scoring framework exists to call
here yet (see `README.md`'s "Known gap"), and hand-writing plausible-looking scores would be
exactly the kind of invented content this codebase's non-negotiables rule out.

Usage:
    python -m apps.sip.collector.run_dry_run \\
        --base-url http://localhost:8000 \\
        --articles-file apps/sip/collector/data/dry_run_fixture_articles.json \\
        --session-cookie "$SESSION_COOKIE" \\
        --csrf-token "$CSRF_TOKEN"

`--session-cookie`/`--csrf-token` must come from an established session (ADR-0004): every business
route requires one, and `initiated_by`/`actor_id` are no longer accepted in request bodies - the
server derives them from the session instead. There is deliberately no sign-in route this script
can call; sessions are issued out of band by `scripts/dev_session.py`, which needs database access.
The CI workflow seeds a deterministic dry-run user with the Analyst role and mints a session for it
before running this script; do the same locally.

`--articles-file` must hold a JSON list of `clean_articles()`-shaped dicts. There is no wiring
from this repo to the live agent yet (cross-repo checkout in CI would need a new PAT secret -
that's an infra ask, not a code one), so this script consumes a fixture file rather than a live
fetch. That fixture is synthetic, clearly-labelled test data - never present its output as a real
day's collected intelligence.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from apps.sip.pipeline.client import SipApiError, SipPipelineClient
from apps.sip.pipeline.models import Run

from .ingest import ingest_articles
from .source_lookup import build_source_lookups
from .source_register import missing_mandatory_outcomes

_AUCKLAND = ZoneInfo("Pacific/Auckland")


def _locked_coverage_window(now_utc: datetime) -> tuple[str, str]:
    """SIP-184 step 2: previous day 07:00 to current day 07:00 Pacific/Auckland, exact 24h."""
    now_nz = now_utc.astimezone(_AUCKLAND)
    end_nz = now_nz.replace(hour=7, minute=0, second=0, microsecond=0)
    if now_nz.hour < 7:
        end_nz -= timedelta(days=1)
    start_nz = end_nz - timedelta(days=1)
    return start_nz.astimezone(UTC).isoformat(), end_nz.astimezone(UTC).isoformat()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--articles-file", required=True, type=Path)
    parser.add_argument(
        "--session-cookie",
        required=True,
        help="value of an established `inzbc_session` cookie (see `scripts/dev_session.py`) - "
        "every business route requires one (ADR-0004).",
    )
    parser.add_argument(
        "--csrf-token",
        required=True,
        help="the CSRF token returned alongside --session-cookie; required on every "
        "state-changing request (create_run, create_candidate).",
    )
    parser.add_argument("--evidence-out", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    articles = json.loads(args.articles_file.read_text(encoding="utf-8"))
    if not isinstance(articles, list):
        raise ValueError(f"{args.articles_file} must contain a JSON list of article dicts")

    client = SipPipelineClient(args.base_url, args.session_cookie, args.csrf_token)
    now = datetime.now(UTC)
    coverage_start, coverage_end = _locked_coverage_window(now)

    run = client.create_run(
        Run(
            run_number=f"DRYRUN-{now.strftime('%Y%m%d%H%M%S')}",
            coverage_start_utc=coverage_start,
            coverage_end_utc=coverage_end,
            prompt_version="SIP-050-v1.1",
            initiated_by="",  # server-derived from the session now; unused, kept for Run's schema
            production_enabled=False,
        )
    )
    run_id = run["id"]
    print(f"[dry-run] created run {run['run_number']} (id={run_id}), production_enabled=False")

    try:
        source_rows = client.get_source_library()
    except SipApiError as error:
        # Fatal, not a downgraded warning: a broken or unseeded source_library would otherwise
        # look like a pass (candidates still get created, just all with source_id=None), which
        # is exactly the failure mode this dry run exists to catch before a real run hits it.
        print(f"[dry-run] FATAL: GET /api/source-library unavailable ({error})", file=sys.stderr)
        return 1
    source_name_lookup, _source_id_lookup = build_source_lookups(source_rows)

    ingest_result = ingest_articles(
        client, run_id, articles, source_name_lookup, (coverage_start, coverage_end)
    )

    evidence = {
        "dry_run": True,
        "sip_191_authority": "expired (window was 27-31 Jul 2026); this run has no authority",
        "run_id": run_id,
        "run_number": run["run_number"],
        "coverage_start_utc": coverage_start,
        "coverage_end_utc": coverage_end,
        "articles_in": len(articles),
        "candidates_created": len(ingest_result.created),
        "candidates_failed": [asdict(f) for f in ingest_result.failed],
        "source_library_available": True,
        "mandatory_source_outcomes_recorded": 0,
        "mandatory_source_outcomes_missing": list(missing_mandatory_outcomes(set())),
    }
    print(json.dumps(evidence, indent=2))

    if args.evidence_out:
        args.evidence_out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    return 1 if ingest_result.failed else 0


if __name__ == "__main__":
    sys.exit(main())
