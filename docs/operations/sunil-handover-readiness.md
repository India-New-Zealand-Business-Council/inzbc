# INZBC AIOS — Sunil handover readiness register

**Status:** Working checklist, not a completion certificate. **Target review:** 30 October 2026; **target handover:** 1 November 2026, subject to acceptance. **Recipients:** Sunil Kaushal (INZBC); Bhanu (technical review). This document does not confer production approval.

## Scope and acceptance principle

Use `docs/modules/README.md` and the approved programme brief as the scope baseline. The nine-module map includes modules marked `planned`, `spec`, `launch` and `build`; these labels are not interchangeable. A planned module is **not** a defect simply because it is not implemented. Do not start work gated by the four foundation decisions or other INZBC sign-off without documented authorization. Do not represent draft-only collection as automated publication.

A handover is ready only when the accepted delivery scope is identified, the evidence for that scope is linked, outstanding risks and owners are documented, and INZBC accepts it. Each item below starts **unverified** until evidence is attached.

## Engineering and quality gates

| Gate | Evidence required | Owner / decision maker | Status |
| --- | --- | --- | --- |
| Agreed delivery scope | Approved scope baseline and exclusions against the nine-module map | INZBC / Sunil | Unverified |
| FTA answer provenance | Corpus source review, citation/effective-date checks, no-match behavior | Roshan / reviewer | Unverified |
| FTA evaluation independence | #406: ten blinded checks by Bhanu or Paras, disagreements reconciled | Bhanu or Paras | Pending external review |
| FTA retrieval research | #387: annotated bibliography, source checks and approved design conclusion | Roshan / Bhanu | Unverified |
| FTA role-sensitive API | #392: role authorization, public default, OpenAPI/client regeneration and tests | API owner / Bhanu | Awaiting ownership decision |
| SIP source coverage | #344: approved design for automatic vs manual outcomes; tested implementation if in scope | SIP owners / INZBC | Design decision required |
| SIP collection integration | #55: live collector-to-capture-to-assessment run, failures and run evidence | SIP technical owners | Blocked until backend/config ready |
| Security and privacy | Adversarial test evidence, permissions review, secret handling, PIA and retention decisions where applicable | Security owners / INZBC | Unverified |
| Deployment and operations | Environment inventory (no secrets), rollback, backup restore evidence, monitoring and incident contacts | Technical owners | Unverified |
| Human control | Approval and distribution gates demonstrated to fail closed, audit trail verified | SIP owners / INZBC | Unverified |
| Client acceptance | Walkthrough, known limitations, action owners, written acceptance or conditional acceptance | Sunil / INZBC | Not yet recorded |

## Module disposition for acceptance

For **each** of the nine modules in `docs/modules/README.md`, record: (1) approved scope; (2) delivered version or `not in approved scope`; (3) demo/test evidence; (4) outstanding dependencies; (5) operating owner; and (6) client acceptance. Do not silently convert planned modules into committed deliverables.

## Handover package contents

1. Architecture and module map with live-vs-planned distinctions.
2. Deployment locations and account ownership, excluding credentials and tokens.
3. Operating runbooks: collection, review/approval, backup/restore, recovery and escalation.
4. Security/privacy decisions and any unresolved risks.
5. CI, automated-test and manual acceptance evidence with dates/commit SHAs.
6. Open issues/PRs with priority, owner, dependency and target resolution.
7. Demonstration script and training notes for INZBC staff.
8. Acceptance record signed or explicitly confirmed by the authorized INZBC representative.

## Stop conditions

Do not declare production readiness if a required security gate is failing, a required source cannot be verified, SIP distribution can bypass human approval, critical tests are missing, or the client has not accepted the delivered scope. Record blocked work explicitly rather than closing issues without evidence.

## Reviewer sign-off (to be completed, not assumed)

- Engineering review (Bhanu): **pending**
- Operational walkthrough (INZBC): **pending**
- Client acceptance (Sunil / authorized delegate): **pending**
- Acceptance date and evidence link: **pending**
