# INZBC AIOS — proposed handover evidence register

**Status:** Working evidence index; not an approved scope baseline, delivery deadline, or production sign-off. The programme brief (`docs/inzbc-ai-operating-system.md`) is a research-reviewed draft, and `docs/project-charter.md` is proposed pending signatures. Use a signed client/technical-lead scope decision when available. No new handover or review date is imposed here.

This index supplements, and does not replace, `docs/handover-pack.md`, `docs/testing/acceptance-register.md`, `docs/raci.md`, and the applicable module acceptance criteria. Follow their recorded responsibilities and evidence.

## Existing acceptance evidence

The technical lead has reported a client session and written sign-off (see `docs/testing/acceptance-register.md` and `docs/handover-pack.md`). This is **reported acceptance with incomplete traceability**, not absence of acceptance and not proof of version-specific production approval. Locate the original record and establish date, signed scope, delivered version and artifact location before treating it as final.

## Open evidence and decision points

| Area | Evidence or decision to reconcile | Accountability |
| --- | --- | --- |
| Delivery scope | Signed client scope, exclusions and foundation decisions; do not treat all nine proposed modules as committed | Executive Sponsor for client scope; Technical Lead for engineering authorization, per `docs/raci.md` |
| FTA independent evaluation (#406) | Reviewer remains **unassigned** pending tech-lead authorization; blinded, independent answer checks and reconciled metrics | Technical Lead to designate checker |
| FTA retrieval research (#387) | Source verification, annotated bibliography and design conclusions | Intelligence & Data, with Technical Lead review |
| FTA depth API (#392) | Explicit ownership decision, role checks, OpenAPI regeneration and regression evidence | Technical Lead to authorize API-lane work |
| SIP source coverage (#344) | Decide whether source outcomes are generated automatically or remain manual; implement only approved design | Technical Lead to resolve cross-component design |
| SIP live collection (#55) | **Fresh INZBC SIP-191 authorization and a PAT for live collection** are prerequisites, per `docs/workstreams/roshan.md`; `.github/workflows/sip-full-walk.yml` already exercises the backend | Technical Lead coordinates authorization; Intelligence & Data executes authorized run |
| SIP safety | Fail-closed distribution, human review, audit and security test evidence | Technical Lead |
| AI Communications Assistant | Redaction, restricted-input and human-review evidence against canonical handover O3 criteria | Technical Lead |
| Public website | Cutover, redirects, accessibility and operational evidence against canonical handover O4 criteria | Product & UX / Technical Lead |
| Deployment and operations | Environment ownership, monitoring, backup restore, incident response and rollback evidence, without exposing credentials | Technical Lead |
| Client acceptance | Reconcile reported sign-off to scope/version/date and outstanding conditions | Executive Sponsor |

For other modules in `docs/modules/README.md`, record `planned`, `spec`, `launch` or `build` as documented; do not convert unapproved modules into delivery obligations. Consult `docs/handover-pack.md` for the canonical handover and module acceptance checklist.

## Stop conditions

Do not claim readiness if critical security tests fail, SIP distribution bypasses human approval, required sources cannot be verified, authorized live testing has not happened where required, or acceptance evidence cannot be tied to the relevant delivered version. Keep open blockers visible; do not close issues without evidence.

## Sign-off references (not approvals)

- Engineering review: **pending for this register**
- Existing client session and written sign-off: **reported; underlying date, scope and version evidence to locate**
- Production authorization: **not established by this register**
