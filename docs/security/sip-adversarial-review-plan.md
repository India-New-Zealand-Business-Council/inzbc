# SIP post-review regression and staff-use sign-off checklist

**Status (28 October 2026):** supplemental release checklist. The substantial adversarial review is **already complete**, with 18 documented reproduced-and-fixed findings in [sip-review.md](sip-review.md); Executive Sponsor sign-off remains outstanding. This file does **not** redo, supersede, or certify that review.

**Scope:** supporting evidence/verification for #40 before any staff-facing use. The canonical authorisation matrix and implementation conformance live in [security/README.md](README.md), `services/api/tests/test_router_auth.py` and the detailed [review](sip-review.md). If this checklist conflicts with the current route implementation, raise a finding rather than silently treating either prose version as authoritative.

## Focused regression matrix

| Abuse case / assertion | Verification evidence required |
|---|---|
| External source attempts to change model instructions or disclose data | Run adversarial source/LLM tests against a fixed commit; preserve content-free results and explicit refusal |
| User omits authentication, CSRF or proper session | Route auth suite and HTTP negative test; no state mutation |
| Reviewer and candidate author/analyst are the same person across roles | Persistence-level separation-of-duties test using canonical actor ID; deny even with multiple roles |
| Reviewer can stop a run independently | Route matrix and real HTTP negative/positive tests, with audit readback |
| Unverified High/Critical candidate attempts inclusion | Routing persistence/quality gate rejects it; observe consistent candidate and audit states |
| Replay uses expired/forged approval ID or ambiguous authority | Server resolves authority to a real approved record and rejects missing/mismatched references |
| Disabled production flag or missing launch authority | No collection execution or distribution, even if client posts actions directly |
| Stale source beyond Auckland 24-hour window | Ineligible in collector and persisted source check; no silent upgrade from unknown |
| Same idempotency key sent twice or raced | Exactly one authoritative transition/delivery, no duplicate send or changed payload acceptance |
| Restricted text or secrets in provider request, audit or error response | Confirm boundary refusal, redaction and logs using synthetic adversarial inputs |
| Audit history modification attempted through SQL | Row-level and statement-level UPDATE/DELETE/TRUNCATE refused after schema restore |
| Unauthorized cross-role audit read or write | API authorization scopes and append-only writer role tested |
| Session expiry, sign-out, reactivation after expiry | Old session not revived; creation/sign-out audit gap recorded separately |
| Malformed state transition and client UI manipulation | API refuses and state persists unchanged across refresh |

## Evidence collection instructions

For each post-review regression: record **fixed commit SHA, environment, synthetic fixture ID, observed API status/state, related audit event ID, reviewer, test output/CI URL, and unresolved deviation**. This checklist makes no new claim that these scenarios passed on 28 October. Use the existing `docs/security/sip-review.md` findings table as the baseline for what was previously reproduced and fixed.

Do not treat local unit tests as evidence of a real SIP day, a timed production backup restore, client UAT, or approval to publish. No live confidential records, credentials or sensitive screenshots belong in public GitHub evidence.

## Outstanding gates (owned decisions)

- **Executive Sponsor:** written signed acceptance of the SIP adversarial review and any residual risk. A reported telephone conversation is not a written record (see `docs/security/sip-review.md` §6).
- **Technical lead:** verify actual deployment environment, MFA on owned accounts, role matrix and current branch after any security-touching merge. Review session establishment/sign-out audit gaps.
- **Comms owner and INZBC privacy owner:** separate #303 staff-authored prose risk; an SIP review does not close it. PR #488 is containment only.
- **SIP production owner and client:** execute the formal launch/UAT/proof steps independently of this document. The `production_enabled` state and release authority must remain governed by the current SOP, not test scripts.

**Resolution rule:** #40 is not completed by creating this checklist. It closes only when the review's required sponsor sign-off and regression evidence are recorded and linked.
