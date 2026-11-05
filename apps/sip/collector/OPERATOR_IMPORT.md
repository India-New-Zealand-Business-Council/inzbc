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

**Production legacy-capture isolation (#526):** the API repository takes a
`runs ... FOR UPDATE` lock before any per-item candidate INSERT and refuses
`POST /api/candidates` for runs marked `production_enabled=true` with HTTP
409. This closes the direct per-item race/bypass for production runs; it does
**not** make the batch import functional. Non-production/manual rehearsal
capture remains available with its existing audit records. Do not set
`production_enabled` merely to attempt a run while the authorised batch path
is absent.

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

## Review-only capture-to-batch packet (#530)

After `prepare_capture` passes against an authorised existing run, the pure
`apps.sip.collector.review_packet.review_packet` function prepares an
**in-memory, local operator-review packet** from the very same original capture
file, a validated `CapturePlan` and the run version fetched from the API.
It revalidates the raw manifest, binds its file SHA-256 and canonical article
checksum, checks every proposed candidate against the manifest's original
headline, URL, summary and publication timestamp, and requires a resolved UUID
source. It emits the reviewed `ImportBatchIn` envelope plus original
URL/source/time rows **and the unmodified, validated original `raw_articles`**
for independent staging review. Keeping raw articles is necessary for the
server-held evidence contract in PR #533 to recompute the canonical exporter
checksum and compare source text; a proposed candidate payload alone is
insufficient. These are potentially licensed third-party materials: do not
put the packet in an issue, PR, source-control history or an unprotected
shared drive. It **does not** stage or
import anything; never store raw packets in Git, PRs or unprotected issues.

The import-reconciliation boundary additionally stores the original exporter
`raw_articles` list alongside the proposed candidates and resolved
URL/source/timestamp records. Before inserting, it recalculates
`articles_sha256` from the exporter's exact canonical article list and
compares raw headline, summary and publication timestamp with the candidate
mapping. A matching URL or request-supplied digest **alone** is no longer
sufficient to change a news headline under an unchanged capture claim.

**Forward migration safety:** `0008_sip_import_evidence.sql` remains
byte-for-byte unchanged for databases that already applied it. The separate
`0009_sip_original_articles_forward.sql` adds `raw_articles` and rejects any
*new* staged evidence without a bounded original article list. A pre-0009 row
cannot be retroactively treated as source-authenticated: it remains unmodified
and ineligible for import because the importer refuses missing original bytes.
No SQL backfill of an append-only evidence record is authorised; produce a new,
independently approved run and re-stage the verified source capture instead.
The upgrade is exercised against a temporary PostgreSQL table with the old
0008 layout, including legacy-row preservation and new-row rejection.

The append-only `sip_import_evidence` row must be populated by a **separately
reviewed and authorised evidence-staging path**, binding original collector
bytes and independently resolved source IDs to the proposed candidate batch.
That staging path does **not** exist yet. A direct SQL insert, a test fixture,
the request body's SHA-256, or an analyst typing a reference is **not** proof
that the original collector manifest or its licence/source outcome trail was
checked. Therefore no HTTP importer or CLI `--apply` is registered or
enabled. Do not call the internal repository in production.


## Independent staging handoff preflight (#536 — no writes)

The pure `services.api.sip_staging_preflight.verify_handoff` function
re-checks a review packet against **separately obtained original manifest
bytes**, the actual server-side run snapshot and server `source_library`
rows. It requires the exact original file SHA-256, original article checksum,
verified source-name-to-UUID mapping, 112 registered mandatory source codes,
complete candidate URL/title/summary/time reconciliation, and true coverage
against the locked 07:00 Auckland run window. It rejects missing, ambiguous
or altered evidence and returns **metadata only**, with every authorisation
and import flag false.

The caller must fetch the run and source library independently from its
own authenticated, permission-checked backend. Values supplied in a client
packet must never substitute for those server records. This preflight does
not authenticate the collector, sign an archive, verify publisher licensing
or record 112 human source outcomes. It **never inserts**
`sip_import_evidence`, creates an import claim or calls the HTTP API.
The independently authorised evidence-custody and staging transaction,
run-row lock, launch window, secret handling and reviewed import endpoint
are separate future work. A green preflight is not permission to run SIP.
