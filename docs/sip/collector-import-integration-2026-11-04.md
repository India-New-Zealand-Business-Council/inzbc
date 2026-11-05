# SIP-184 collector-to-import integration proof — 4 November 2026

**Scope: synthetic CI only. No production import, staged evidence, launch,
collection or distribution.** Review issue #539, normal integration PR.

## Review branch composition

This integration branch is based on original-article validation PR #533,
stacked on the internal atomic import PR #529, itself stacked on batch-contract
PR #500. It brings across **unchanged** the following modules/tests from
read-only packet PR #532 and offline source/run preflight PR #538:

- `apps/sip/collector/review_packet.py` and `tests/test_review_packet.py`
- `services/api/sip_staging_preflight.py` and
  `services/api/tests/test_sip_staging_preflight.py`

No original pull request has been merged. The legacy production-write exclusion
remains a separate PR #527 against main. The integrator cannot be deployed
without that guard and review of *all* other candidate-write paths.

## Synthetic verification

1. A synthetic news-agent manifest is checksummed with the exporter's exact
   canonical article encoding; packet construction rejects changed source
   article text, run ID, coverage and unverified candidates.
2. The standalone preflight rechecks **original bytes**, checksum, run version,
   07:00 Auckland locked coverage and source IDs resolved from separately
   supplied server-library rows, including all 112 mandatory register codes.
3. The internal importer operates only on separately staged, immutable
   database evidence, verifies run authorisation and 112 human source checks,
   and commits candidates/audit/claim atomically under a shared run-row lock.
   The tests use fabricated data and real disposable PostgreSQL.
4. The forward 0009 migration preserves existing 0008 and refuses new
   evidence lacking original article bodies; legacy rows remain unmodified.
5. CI must pass all Python, Postgres, frontend, Docker, lint, security, SAST and
   link checks at the **integration head**, not only individual source PR heads.

## 6 November integration regression and schema handoff

- The integration head adds
  `test_preflight_cannot_authorise_later_write` in
  `services/api/tests/test_atomic_import.py`. It first proves the pure
  precondition accepts a synthetic empty Scanning run, then commits another
  candidate before the write. The real-PostgreSQL importer must read the
  new count under its run lock and refuse the import, leaving zero
  `candidate.import` audit events and zero import claims. The preflight
  result is **not** a transferable authorisation token.
- The **current integration branch** consistently uses `raw_articles` in
  `database/schema.sql`, forward migration
  `0009_sip_original_articles_forward.sql`, `atomic_import.py`,
  `review_packet.py`, and its PostgreSQL migration/transaction tests.
  The separately proposed #537 branch has been described in tech-lead
  review as using `exported_articles`. These are **alternative schema
  contracts**, not fields to mix. Do not merge or cherry-pick that sibling
  migration/importer without first choosing one name across schema,
  migrations, evidence staging and importer, then re-running the
  real-PostgreSQL migration, concurrency and original-text tests.
- This remains a **synthetic integration proof only**. The CI status must be
  taken from the *latest* head SHA, not a green result on an older parent
  branch or an unrelated PR.

## Production hard stops

- There is **no authenticated, permission-checked custody/staging service**
  or HTTP batch import endpoint. This preflight accepts inputs supplied by its
  caller: the future handler must fetch the original bytes, run and source
  library through independent, trusted mechanisms and prove permissions.
- A captured articles checksum is an integrity check, **not** a signature or
  publisher-rights authorisation.
- Original written SIP-191 authority and live window, real 112 mandatory
  SIP-185 outcomes, observer evidence, independently reviewed candidate scores,
  QA/CEO decisions, backup proof and separate distribution authority remain
  unverified. No source-health status may be substituted for a human outcome.
- The read-only operator CLI `--apply` and every candidate-write HTTP endpoint
  stay disabled for bulk import.

**Merge/review order:** #527 and #500, then #529; #533 and #532/#538 must
be reconciled with the reviewed integration diff, no blind sibling merge.
This PR and all parents remain open until Roshan reviews them personally.
