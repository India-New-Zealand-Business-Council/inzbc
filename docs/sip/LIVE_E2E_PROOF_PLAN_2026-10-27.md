# SIP first real-data run — evidence-first E2E plan (27 Oct 2026)

**Owner of this checklist:** Roshan, SIP collection/pipeline lane. **Cross-team owners:** Bhanu (API/deployment/security), Paras (UI/QA workflow), Sunil/INZBC (scope, original authority, human decisions). **Tracked by:** [#55](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/55). This is a proposed execution sequence, **not** a new SIP-191 authorisation or an amendment to SIP-184.

> **Current outcome: NOT PROVEN.** The tech lead [reported](../launch-status-2026-10-24.md) authorisation and a live collection PAT on 24 Oct, but no original written authority, real run ID, 112 source outcomes, production candidate batch import, final QA/CEO decision or delivery evidence is linked to #55. Do not silently claim any gate passed. The client demo [walkthrough](SUNIL_SIP_WALKTHROUGH_2026-10-27.md) and [sample](ILLUSTRATIVE_DAILY_BRIEF.md) are not substitute evidence.

## Run the gates in order, with actual artifacts

| Gate | Prove it by attaching **real, run-bound evidence** | Lead / dependency | Status as checked |
|---|---|---|---|
| 0. Purpose and audience | Sunil reviews preview and names report scope, internal readers, cadence, and who may approve/distribute each version | Sunil / Bhanu (client decision) | **Requested in client conversation**, not recorded |
| 1. Launch authority | Original written SIP-191 authority, permitted run window, authorised operators and approved controlled document set | Sunil / Bhanu | Tech lead **reported** authority, source record **not linked** |
| 2. Controlled E2E environment | An **authorised isolated local Postgres/API environment** with session/roles/CSRF, secure approved access, relevant redaction policy and a disposable or approved protected data store; record endpoint, configuration, disposal and operator evidence. A live staff host is **not required** for the first local real-data proof | Bhanu / authorised technical operator | No run-bound isolated full proof recorded. **Production deployment** is separately tracked by [#99](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/99) |
| 3. Real run opened | Server-created authorised run ID, run state, analyst, start timestamp and run-version evidence | SIP Owner and Analyst | **No link to real run** |
| 4. Fixed coverage window | Actual previous-day 07:00 to current-day 07:00 Pacific/Auckland boundaries; valid local offset and handling of SOP “exactly 24h” ambiguity on NZ DST dates | Analyst / SIP Owner | Not recorded for any real run |
| 5. Source checks | SIP-185 **112/112 mandatory source codes** with one of six controlled outcomes **each**, real references, fallback steps and reasons when failed | Analyst; QA checks completeness | **No genuine complete outcome packet**; news-agent source-health ≠ source checks |
| 6. Capture | News-agent raw article manifest with genuine fetch provenance, canonical SHA-256, source health, timestamps and original URLs; operator reviews gaps | Roshan / authorised collector | Read-only [#15](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/pull/15) proposed, **no proven run-bound export** |
| 7. Safe candidate import | API verifies authority, run-state and digest; writes candidates with audit in one transaction, deterministic replay/rejection and no concurrent duplicate imports | **Bhanu / API owner** | **BLOCKER** — client-side per-item import is intentionally disabled; see [operator preflight](../../apps/sip/collector/OPERATOR_IMPORT.md) |
| 8. Analyst judgement | Actual captured candidates scored with SIP-050 version, duplicate and exclusions accounted for, High/Critical official or independent verification, justified routing | Analyst + separate verifier | Not performed on real captured candidates |
| 9. Daily report | Source-supported SIP-186 report version with real date/window, confidence, action owners, source exceptions and citations; stored append-only | Analyst | UI and seeded versions exist; real report **missing** |
| 10. QA and separation-of-duties evidence | Actual SIP-188 checks including negative paths, unresolved-source stop, provenance and version; identify whether a **different approved reviewer** performed QA, or a formally authorised, audited single-operator exception was used. Never call same-person exception-based QA `independent` | Sunil as sole operator per #266 unless formally revised; Bhanu coordinates UI/test evidence | **No real-run QA or documented run-bound exception** |
| 11. CEO decision | Named CEO decision tied to exact report version, corrections or pause handled, signed decision setting if applicable | Sunil, with Bhanu config | **No linked real decision** |
| 12. Distribution | Separate recipient-bound authorisation; if approved, **manual** send and recorded sender, recipients, version/time and result; if not approved, no send | Sunil + authorised sender | **NOT AUTHORISED BY THIS PLAN** |
| 13. Reconcile / close | Run-state replay, immutable audit and decision readback, source/candidate counts, exception and action-register reconciliation, signed run record | Analyst + independent reviewer | No real closure evidence |

**Milestone distinction:** First **authorised real-data E2E evidence** may be collected in an isolated, protected local environment with a real database and the full run/decision/audit controls; it does not prove the staff app is deployed or suitable for INZBC production use. Actual production launch/staff use additionally requires the INZBC-owned host (#99), configured decision signing, backup/restore, incident response, security/privacy sign-off and the controlling authorisations. A synthetic local seed demo is **not** the real-data proof. Do not upload real content or credentials to a public issue/PR.

**Staffing decision:** #266 records Sunil as the only intended SIP operator and final approver, with no deputy. The older [operator guide](operator-guide.md) named placement-team backup reviewers; it must not be read as authorising those people now. Independent QA requires a genuinely separate approved human actor. An approved, recorded SoD exception may permit a single-person flow but does not constitute independent QA. If the controlled SIP-188/SIP-184 procedure does not permit the arrangement, obtain a formal amendment **before** the real run.

**Stop criteria:** Missing written authority; source outcome blank; unresolved source identity; out-of-window timestamps; unverified High/Critical; unknown approver/recipient; compromised redaction/role policy; unapproved write path; any other SIP-184 Critical stop. A passing Python/CI suite cannot waive any stop.

## API owner handoff — the one concrete write-path blocker

Do not revive `ingest_articles()` as a production workaround. In the [operator preflight](../../apps/sip/collector/OPERATOR_IMPORT.md), `--apply` intentionally refuses **before API access** because two writers can each pass a client-side empty-run check.

A reviewed backend design should include all of the following:
- **Atomic ownership:** lock one run row (or equivalent transactional claim), verify its authorised `Scanning` state, authority and eligible source outcomes **inside the same transaction** as insert.
- **Bounded, validated request:** all candidate fields validated by the backend; tie idempotency to `run_id + articles_sha256` and preserve underlying canonical captured bytes; reject mismatched batch/revision and unauthorized actor.
- **No bypass:** legacy `POST /api/candidates` and any other candidate creation path must not allow interleaving duplicates while the import owns the run; agree migration/compatibility strategy.
- **Audit and replay:** candidate inserts and audit rows commit together; identical replay returns the committed result without duplicates; a different digest conflicts deterministically; rollback leaves no partial import.
- **Tests:** two independent concurrent writers for the same run; repeated same digest; conflicting digests; late/wrong state; partial insert failure; missing coverage; wrong user/CSRF; old per-item endpoint racing a batch.
- **Integration to operator CLI only after review:** implement the approved endpoint contract and test it against a local disposable Postgres; do not enable automation, production import or delivery from this doc.

**Owner:** Bhanu (or explicitly assigned API maintainer). **Roshan:** wire validated exporter/preflight to the reviewed endpoint after it exists, then demonstrate dry-run and concurrency evidence. The path or endpoint signature itself is **to be agreed**, not invented here.

## What the team can execute now without touching production

- **Roshan:** finish review comments on PRs [#480](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/480), [#481](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/481), [#482](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/482); review the [#477](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/477) independent-label packet; demonstrate collector *read-only* preflight with synthetic inputs; document where the real evidence will live.
- **Bhanu:** assign backend batch-import contract, confirm the staff platform's deployable hosting/role and signed-decision policy, review & merge approved branches **in order**, locate written authority rather than relying only on a relayed statement.
- **Paras:** drive an actual UI demonstration in a disposable seeded environment; address review findings on [#478](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/478) and [#479](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/479); collect Sunil's usability feedback.
- **Sunil:** review the [illustrative output](ILLUSTRATIVE_DAILY_BRIEF.md); reconfirm #266's one-person role arrangement or initiate a controlled staffing change, approve any formal SoD exception, and clarify sections/audience **without** changing SIP-191 recipient authority by conversation alone.

## Minimum evidence pack to close issue #55

**Attach references, never tokens or secrets.** The [SIP-184 run record](launch/daily-run-record_v0.9.md) is the controlled template; [Roshan's evidence index](../../apps/sip/collector/RUN_EVIDENCE_HANDOFF.md) points to the missing proof categories, not completed records.

- [[Original written authority reference]]
- [[Run ID and exact local coverage window]]
- [[Approved source-register version and all 112 outcomes with source/attempt evidence]]
- [[Raw capture digest and safe import reconciliation; two-writer test result]]
- [[Candidate scoring, verification, duplicates and routing evidence]]
- [[Source-supported report version and QA evidence: distinct reviewer or approved, recorded SoD exception (not independent)]]
- [[CEO decision; distinct distribution decision and named audience]]
- [[Manual send receipt, **if separately authorised**, or recorded non-distribution]]
- [[Auditable closure, action/watch register reconciliation and exception readback]]

**Until these are independently recorded, the outcome is “not yet evidenced,” not “passed.”**
