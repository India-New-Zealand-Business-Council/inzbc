# Operator-controlled SIP capture import (#55)

This module builds on the **read-only capture verifier** in PR #472, which is stacked on news-agent exporter PR #15 (itself stacked on #14). Do not treat any of these PRs as merged, deployed or production-authorised. These scripts have not been run against live INZBC data.

## Purpose

`apps.sip.collector.import_capture` is the last application-side handoff for capturing externally collected public intelligence as *unscored candidates* in an **existing** run. It never creates a run, authorises a run, generates source outcomes, scores, verifies, routes, approves a report, or distributes a brief. The existing SIP session/CSRF enforcement is the server authority.

## Preflight (default, read-only)

With an operator-established Analyst session, supply `SIP_SESSION_COOKIE` and `SIP_CSRF_TOKEN` through a protected environment, **not command-line arguments, tracked environment files or GitHub issues**. Point `--base-url` at the approved HTTPS API (or localhost loopback for isolated testing). Example command: `uv run python -m apps.sip.collector.import_capture --capture /secure/captures/2026-10-26.json --run-id <existing-run-uuid> --base-url https://approved-operator-api.example`.

Preflight refuses to proceed unless ALL of the following are true:

- Export JSON passes PR #472 checks (shape, hash, public article links, bounded size and actual fetch statuses) and has no unresolved `partial`, `empty` or `error` fetch source.
- The authenticated API returns precisely the specified run, with a real `RUN-YYYYMMDD-NN` identifier and state `Scanning` (not Draft, DRYRUN or a rehearsed WALK). Merely finding a run does **not** prove written SIP-191 authority.
- The run has valid, consecutive 07:00 local-day boundaries AND 24 elapsed hours. This deliberately stops on a DST changeover until the unresolved SOP decision in PR #473 is recorded.
- All 112 mandatory SIP-185 codes resolve by unique stable code through the real source-library API; every one has a recorded, valid source outcome and non-empty human evidence notes from the existing authenticated source-check UI/API. Agent fetch-health observations **never** count as these decisions.
- This run has no previously captured candidates, to avoid replaying an earlier partial batch.
- Every article has a unique URL, parseable timezone-aware publication time within the run's **locked** coverage interval, resolvable unambiguous source name, and maps to an unscored `Candidate`. Articles outside the fixed window are refused for operator reconciliation, never silently dropped.

The command prints a compact preview with the SHA-256 digest, run number and count. **No API write happens by default**.

## Explicit capture (operator only)

Only after the operator has independently checked the actual signed/written SIP-191 run authority, its active window, the source evidence and the preview should they add all of:

`--apply --confirm-run-number RUN-YYYYMMDD-01 --confirm-sip191-reviewed`

The command re-reads the target run and confirms that no candidates appeared since preflight, then POSTs only candidate-capture fields through the existing session-authenticated client. It stops on the first HTTP error. **This is not a transactional batch**: if a later write fails, previous candidates may already exist, and a retry must be manually reconciled. The script refuses a blind retry when the run has candidates.

Even a successful candidate import is **not an SIP-184 completed production run**. The analyst must still conduct approved relevance/scoring/verification, reconcile carry-forward registers, draft the brief, obtain independent QA and CEO authorization, and record manual distribution and closeout when permitted. No real capture, live credentials, approval or distribution was performed in the development of this PR.

## Tests

Run `uv run python -m pytest apps/sip/collector/tests/test_capture_manifest.py apps/sip/collector/tests/test_import_capture.py -q` and `uv run ruff check apps/sip/collector`. Tests use local synthetic data, a fake API and fake source checks — they are **not** a substitute for the real end-to-end launch evidence in issue #55.
