# Operator-controlled SIP capture import (#55)

This module builds on the **read-only capture verifier** in PR #472, which is stacked on news-agent exporter PR #15 (itself stacked on #14). Do not treat any of these PRs as merged, deployed or production-authorised. **This PR is preflight-only. The write path was disabled in response to Bhanu's 26 Oct P2 review, because the current candidate API cannot atomically claim an import or prevent simultaneous imports.**

## Purpose

`apps.sip.collector.import_capture` validates and previews mapping public-source intelligence into an **existing** run. It does **not** write candidate records. It never creates a run, authorises a run, generates source outcomes, scores, verifies, routes, approves a report, or distributes a brief. The existing SIP session/CSRF enforcement is the server authority.

## Preflight (default, read-only)

With an operator-established Analyst session, supply `SIP_SESSION_COOKIE` and `SIP_CSRF_TOKEN` through a protected environment, **not command-line arguments, tracked environment files or GitHub issues**. Point `--base-url` at the approved HTTPS API (or localhost loopback for isolated testing). Example command: `uv run python -m apps.sip.collector.import_capture --capture /secure/captures/2026-10-26.json --run-id <existing-run-uuid> --base-url https://approved-operator-api.example`.

Preflight refuses to proceed unless ALL of the following are true:

- Export JSON passes PR #472 checks (shape, hash, public article links, bounded size and actual fetch statuses) and has no unresolved `partial`, `empty` or `error` fetch source.
- The authenticated API returns precisely the specified run, with a real `RUN-YYYYMMDD-NN` identifier and state `Scanning` (not Draft, DRYRUN or a rehearsed WALK). Merely finding a run does **not** prove written SIP-191 authority.
- The run has valid, consecutive 07:00 local-day boundaries AND 24 elapsed hours. This deliberately stops on a DST changeover until the unresolved SOP decision in PR #473 is recorded.
- All 112 mandatory SIP-185 codes resolve by unique stable code through the real source-library API; every one has a recorded, valid source outcome. Human evidence must use the **actual Brief Builder contract**: `Analyst-confirmed evidence: <nonblank reference>`, followed by `Fallback trail: <approved ordered methods>`, and `Access failure: <reason>` when required; the persisted method, fallback flag and access error must match this trail. Generic free-text notes are not sufficient. Agent fetch-health observations **never** count as these decisions.
- This run has no previously captured candidates, to avoid replaying an earlier partial batch.
- Every article has a unique URL, parseable timezone-aware publication time within the run's **locked** coverage interval, resolvable unambiguous source name, and maps to an unscored `Candidate`. Articles outside the fixed window are refused for operator reconciliation, never silently dropped.

The command prints a compact preview with the SHA-256 digest, run number and count. **No API write happens by default**.

## Write path is deliberately disabled (review blocker)

The earlier candidate-by-candidate POST loop could pass a client-side empty-run
check in **two simultaneous processes**, allowing duplicate candidates. The API
has neither an atomic batch endpoint nor a transactionally protected idempotency
claim. Consequently `--apply` now **fails before API access**; even a direct
`apply_capture()` call raises a clear error without writing anything. Merely
repeating a client-side GET or adding a local file lock would not fix concurrency
between different operator machines.

**Backend owner follow-up:** implement and review a server-side transactional
batch import that locks the run, verifies its state/authority and the candidate
absence within the **same transaction**, enforces an idempotency key derived from
`run_id + articles_sha256`, validates each candidate, inserts its audit entries,
and returns deterministic reconciliation evidence. Other candidate endpoints
must not bypass the same exclusion invariant. Once it exists, integrate it into
this operator tool with a real two-writer concurrency test. That server change
belongs with the SIP API owner and must not be silently authorised in this PR.

Even a successful future import will **not** equal a finished SIP-184 production
run. The analyst must still score/verify, reconcile source registers, draft the
brief, complete independent QA, CEO decision and manual distribution when allowed.
**No live capture, credential use, production write or distribution occurred.**

## Tests

Run `uv run python -m pytest apps/sip/collector/tests/test_capture_manifest.py apps/sip/collector/tests/test_import_capture.py -q` and `uv run ruff check apps/sip/collector`. Tests use local synthetic data, a fake API and fake source checks — they are **not** a substitute for the real end-to-end launch evidence in issue #55. They also assert that writes remain disabled until the API's atomic-import contract exists.

## Internal transactional import preparation (#528, not callable by operators)

The `services.api.atomic_import.ImportRepository` module now contains an
**unregistered internal service** for a reviewed import batch. In a single
PostgreSQL transaction it locks `runs ... FOR UPDATE`, verifies the caller's
active Analyst/SIP Owner role, run state/version/production flag, recorded
Launch authorisation, complete mandatory source checks and **server-held,
append-only** capture evidence; it then writes candidates, individual audit
records, analyst claim and deterministic import claim together. An exact replay
returns the committed count; a conflicting digest or incomplete run is refused.

The import-reconciliation boundary additionally stores the original exporter
`raw_articles` list alongside the proposed candidates and resolved
URL/source/timestamp records. Before inserting, it recalculates
`articles_sha256` from the exporter's exact canonical article list and
compares raw headline, summary and publication timestamp with the candidate
mapping. A matching URL or request-supplied digest **alone** is no longer
sufficient to change a news headline under an unchanged capture claim.

The append-only `sip_import_evidence` row must be populated by a **separately
reviewed and authorised evidence-staging path**, binding original collector
bytes and independently resolved source IDs to the proposed candidate batch.
That staging path does **not** exist yet. A direct SQL insert, a test fixture,
the request body's SHA-256, or an analyst typing a reference is **not** proof
that the original collector manifest or its licence/source outcome trail was
checked. Therefore no HTTP importer or CLI `--apply` is registered or
enabled. Do not call the internal repository in production.

Before enabling, the API owner must merge/reconcile the legacy-production
per-item exclusion in #526, verify migrations, build the controlled evidence
staging interface, run the full concurrent-writer and negative auth/CSRF
tests against a disposable Postgres, and obtain SIP-191/source authority.
Successful synthetic CI demonstrates transaction mechanics only; it does not
complete the authorised run or any approval/distribution gate.
