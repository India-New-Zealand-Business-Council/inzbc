# INZBC engineering and handover completion queue — 28 October 2026

**Status:** factual triage and proposed sequence, **not** a client-approved scope expansion or a replacement for the charter, SIP-184 SOP, acceptance register, or release authority. Based on the open issue backlog, current code and the dated repository documents. Owners in this table are accountable for their decisions; implementation may be reassigned by the tech lead.

**Principle:** mergeable code ≠ configured deployment ≠ live run ≠ approved distribution ≠ client acceptance. Each step requires its own evidence.

## A. Immediate engineering review (no live data needed)

| Order | Issues / current evidence | Work that can proceed | Exit criterion |
|---|---|---|---|
| A1 | #303, draft PR #488 | Verify both Comms routes default-deny external model calls and fake-provider tests; review staff-input policy and UI | Green CI plus security/privacy owner review; **not** accepted prose risk |
| A2 | #40, draft PR #487; `docs/security/sip-review.md` exists | Maintain post-review regression checks and audit traceability | Sponsor's written review sign-off remains separate |
| A3 | #393, draft PR #489 | Audit committed lexical/BM25 metrics and held-out overlap; propose lexical retention | Decide retrieval policy only from verified evidence, no model upgrade without approval |
| A4 | #127 / #128 / #129, draft PR #490 | Verify UI transition/refusal, audit read and browser refresh; run real DB/browser exercise later | API prevents illegal actions; browser evidence against real DB to finish #129 |
| A5 | #387 | Finish annotation/original-paper verification and technical review | Literature bibliography verified, with claims matched to originals |
| A6 | #58 / #59 / #69 | Review accessible component states, FTA sourced-answer/no-match UI and test tooling actually wired | Reproducible RTL/Storybook/Playwright/WCAG outputs, not just configuration |
| A7 | #195, draft PR #486 | Sign off definitions, denominators, provenance and missing-feed behaviour | Client data owners approve proposed metric definitions; **no** finance integration |
| A8 | #208 | Review and merge upstream agent PR #14 then rebase/merge stacked #15 in order after checks | Verified collector fetch-health and read-only capture; does not establish real SIP run |

## B. Controlled integration and client gates

| Dependency | Evidence required before marking complete | Decision / delivery owner |
|---|---|---|
| #99 first platform deployment | Named INZBC-owned account, actual service ID/URL, secure environment, migration/restore proof, cost and rollback evidence | INZBC account owner + technical lead |
| #55 first live SIP run | Original SIP-191 authority, 112/112 signed source outcomes, canonical live collector manifest, reviewed atomic batch import, run ID, analyst/QA/CEO evidence and separate recipient-bound delivery authority | SIP owner, technical lead, authorised operators and CEO |
| #39 scoring calibration | Real approved candidate set tied to #55, scoring version, independent review and measured calibration | SIP scoring / QA |
| #45 site-forms integration | **Receiver, HMAC contract and database persistence exist in code** (`services/api/site_forms.py`, `schemas/webhooks.md`, migration `0005_site_form_submissions.sql`). Still need INZBC form/retention/notice authority, Wix producer wiring, secure hosting, secret custody and live signed-delivery evidence | INZBC privacy/data owner + tech lead + website owner |
| #133 client acceptance | Original signed scope, date, environment, version and observed test report; reported acceptance is not reconstructed UAT | Executive Sponsor + client |
| #291 handover | Original sign-off linked, named recipient, secrets custody proof, tested real backup restore/timing, operational walkthrough and record | Technical lead + Sunil |
| #198 member portal / #199 events / #200 sponsor services | Foundation/platform choice, data ownership, user permission model and approved scope before any new personal-data write paths | INZBC client owner |
| #193 newsletter / #194 sector briefs | Explicit priority authorization (both presently optional in the module menu), safe drafting/data boundary | INZBC client owner |

## C. Do-not-do list

- Do not create a replacement membership CRM or move member data from Member Jungle: 16 October decision retained it as the system of record.
- Do not silently expand optional sectors/newsletter/board dashboard functionality into committed scope.
- Do not enable `production_enabled`, send external email, publish FTA/SIP output or turn on the Comms provider opt-in merely because a test passes.
- Do not use a client-side empty-run precheck as substitute for atomic, audited and idempotent backend candidate import.
- Do not treat seeded demos, mock Playwright server state or synthetic vector scores as real-world acceptance evidence.
- Do not publish credentials, private sign-off artifacts, named member records or sensitive decision material to GitHub.

## Review/merge order and proof

1. **Independent branches:** review #486–#490; wait for current CI and the respective technical or content owner reviews. No administrative branch protection bypass.
2. **Upstream collector stack:** #14 based on `main` before #15 (which currently bases on #14), then rerun required checks. Never merge an upper stacked PR to a stale base.
3. **Runtime integration:** agree and test backend atomic import with independent writers and rollback before enabling any #55 production import.
4. **Client acceptance:** gather actual evidence in `docs/testing/acceptance-register.md`, controlled SIP run record, and private credential/sign-off custody. Issues only close against explicit acceptance criteria.

References: `docs/handover-pack.md`, `docs/sip/LIVE_E2E_PROOF_PLAN_2026-10-27.md`, `docs/operations/sunil-handover-readiness.md`, `docs/meetings/client/2026-10-16-decision-update.md`, and `docs/launch-status-2026-10-24.md`.

**Maintainer note:** review this snapshot when PRs land; it is deliberately dated, not an evergreen authoritative dashboard.
