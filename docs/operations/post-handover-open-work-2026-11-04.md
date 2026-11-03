# INZBC AIOS — post-handover open-work and evidence queue

**Snapshot:** 4 November 2026 (Pacific/Auckland)  
**Status:** Engineering triage for technical-lead review. **Not** a change to client-approved scope, deployment authority, SIP-191, SIP-184, source licences, or production settings.  
**Tracking:** [#521](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/521)

## Read this before taking work

The [4 November final handover](../final-handover-2026-11-04.md) reports that Sunil accepted the delivered work and the tech lead reported acceptance of residual risk. The original written record is to be linked when INZBC files it. **Acceptance of the delivered scope does not prove that the unbuilt or unconfigured items below are live, tested or authorised.**

The same final handover records **1,398 Python tests passed and 225 skipped without a database**, plus local FTA API smoke tests using demo data. These are valid engineering results; they are *not* a live SIP-184 run, real-backup recovery, production configuration check or independent client UAT.

To avoid accidental overclaiming, classify each item separately:

1. **Code in `main`** — an implementation has merged; verification may still be pending.
2. **Open PR** — not part of `main` until reviewed and merged by the technical lead.
3. **Local/CI test** — demonstrates the tested path under the recorded environment.
4. **Production proof** — must include a real authorised run/endpoint, observed result and protected evidence location.
5. **Client/owner authority** — a signed or otherwise recorded approval must be obtained separately; an environment flag or test result is not approval.

## Priority queue (status at the snapshot date)

| Priority | Issue / owner gate | Current evidence and remaining gap | Next safe action | Closure requires |
|---|---|---|---|---|
| **P0** | [#99 hosting](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/99) — INZBC account owner and tech lead | Final handover says **no Render service exists**; API/platform UI are local only | Check INZBC-owned access, resource/budget decisions and deployment checklist, without creating a service unilaterally | Actual service ID/URL, configuration, migrations, health checks, monitoring, cost/rollback and authorised owner evidence |
| **P0** | [#55 first SIP-184 run](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/55) — SIP owner, approved operators, tech lead | No first production run recorded. [PR #500](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/500) only validates a bounded import; **write endpoint remains disabled** | Review PR #500's validation and hand-off; have backend owner design atomic, audited, idempotent import with two concurrent-writer Postgres tests | Recorded SIP-191 authority, correct coverage window, 112/112 independently evidenced mandatory-source outcomes, canonical capture, backend transaction proof, real run ID, QA/CEO decisions and separately authorised distribution |
| **P0** | Backup and restore — INZBC operations owner / tech lead | Final handover explicitly says no timed restore of a real backup | Prepare controlled restore rehearsal, isolated target, verification procedure and private evidence fields | Real backup restored with integrity checks, actual elapsed time, recovery/failure notes and owner acknowledgement; do **not** invent RTO |
| **P1** | [News-agent #17 source health/rights](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/issues/17) — SIP source owner | Live staging smoke logged 10/18 usable legacy RSS feeds; 8 failed. Scoop/Indian Express rights remain uncleared; PIB, Beehive, MFAT, ORF need permitted verified endpoints or a documented fallback | Owner reviews publisher permissions, confirms only official working URLs, reruns read-only staging health checks and records per-source results | Source-rights decision, HTTP/parser/freshness evidence, accepted fallback for each failure and source-owner review. **Not** a 112-source coverage claim |
| **P1** | [#509 hourly collection](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/509) — SIP owner / CEO | [News-agent PR #16](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/pull/16) is staging-only; cron remains **off**, retention and owner fields unsigned | Review staging tests, checkpoint corruption/recovery, DST windows, monitoring and licence decisions | All #509 decision fields and staging gates signed; a **separate activation PR** reviewed. No implicit approval from variable `SIP_HOURLY_COLLECTION_APPROVED` |
| **P1** | [#39 real scoring calibration](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/39) — Intelligence/QA | Only golden-set scoring is evidenced in final handover | Prepare calibration protocol tied to #55 and independently checked real candidates | Approved real candidate sample, pinned scorer/version, independent labels, measured errors and authorised calibration decision |
| **P1** | [#60 Comms review UI](../handover-pack.md) — assigned UI owner | Approval API exists; reviewer screen not delivered per final handover | Technical lead to assign UI scope, implement and test review/approval refusal flow **without** enabling provider or publication | Reviewer UI, logged human action, refusal/self-approval tests, scoped UAT |
| **P1** | [#303 sensitive Comms inputs](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/303) — security/privacy owner | Structured brief and [default-deny external-model release gate](../security/comms-release-gate.md) merged; staff prose can still contain confidential information | Review policy, redaction limits, signed residual-risk terms and adversarial cases for both sync/stream endpoints | Explicit approved permitted-input policy and technical/security review before any external-model opt-in |
| **P1** | [#45 live site forms](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/45) — privacy/data owner and website owner | Webhook contract/receiver/tests exist; no live forms producer integration | Confirm notice, retention, form scopes, secret custody and testing environment | Approved policy, wiring and real signed-delivery verification with no unauthorised personal data |
| **P2** | [#393 FTA retrieval](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/393) / [#387 source review](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/387) — Intelligence/tech lead | Lexical, BM25 and synthetic dense/hybrid harness documented. Held-out questions are synonym-only and 2/10 overlap development data; no genuine independently graded dense scores | Verify bibliography; obtain authorised independent checker, full-ranking real embedding snapshot, precommitted threshold and independent no-match/product test questions | Reproducible provenance, independently reviewed reference labels and per-type error analysis; no automatic ranker deployment |

## Open PR dependencies to reconcile before integration

- Main [#500](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/500) (draft): contract-only import validation. **Do not turn on a write path or describe it as a live SIP run.**
- Main [#497](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/497) (draft): research/trust wording. Verify current `main` and doc delta before considering it; do not assume it is merged.
- [News agent #14](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/pull/14) (open) is the source-freshness base. [#15](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/pull/15) (open) **targets #14's branch**, not `main`; review #14 first, then update/re-test #15 if approved. Both are review-only collection work.
- [News agent #16](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/pull/16) (draft) is a **separate staging-only** hourly collector design. Reconcile output formats, checkpoint and source-health semantics with #14/#15 before integration. Its current success does not authorise the cron.
- The rehearsal UI fixes [#494](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/494), [#498](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/498), [#501](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/501) and [#507](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/507) **have merged**. [Issue #493](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/493) and [#510](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/510) can be reconciled against the merged tests; do not recreate those fixes.

## Suggested execution batches

**Batch A — safe review, no new permissions:** verify #500 and #497 against current main; inspect regression tests for merged #494/#501/#507; assess the #14 → #15 stack, then #16 schema reconciliation; confirm source rights and live-health evidence. Evidence: linked CI/test logs, reviewed diffs and issue updates. A green check does not override the tech-lead merge decision.

**Batch B — controlled integration design:** backend owner specifies a transactionally safe SIP bulk import with immutable capture, duplicate/idempotency and concurrent-writer tests; operating owner prepares real-backup restore; Comms UI owner completes human reviewer workflow; privacy owner validates forms. No production data or external model provider needed to draft tests/specifications.

**Batch C — only with explicit client and platform authority:** provision INZBC-owned infrastructure, verify migration/rollback and restore, execute authorised 112-source SIP-184 run and independent QA/CEO trail, calibrate on real candidates; separately sign off optional hourly polling, retention and source rights before any schedule activation.

## Out of this execution scope

[Member portal #198](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/198), [events #199](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/199), [sponsors #200](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/200), [newsletter #193](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/193) and [sector briefs #194](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/194) have open proposals/issues. They are **not** automatically new commitments after the 4 November accepted delivery; confirm owner priorities and privacy/data scope first. Member Jungle remains the membership system of record. No direct edits to the live `inzview` site.

## Closeout checklist for this queue

- [ ] Tech lead reviews priority and ownership assignments and marks any status errors on [#521](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/521).
- [ ] PRs and the merged code behind #493/#510 are cross-checked; issue states are reconciled by their owners with test evidence.
- [ ] Each P0/P1 issue points to its **actual** next dependency and closure proof. No private credentials, members' data, internal approvals or unpublished evidence are copied into public issues.
- [ ] The original INZBC written acceptance record is privately linked or its absence explicitly noted. The final handover's report of acceptance is retained as reported; do not fabricate UAT results.
- [ ] The tech lead owns any merge; INZBC / Sunil controls live deployment, source/retention policy and SIP operation.

For canonical scope and sign-off, read [final handover](../final-handover-2026-11-04.md), [handover pack](../handover-pack.md), [October engineering queue](engineering-backlog-2026-10-28.md), [SIP evidence plan](../sip/LIVE_E2E_PROOF_PLAN_2026-10-27.md) and [client decision update](../meetings/client/2026-10-16-decision-update.md).