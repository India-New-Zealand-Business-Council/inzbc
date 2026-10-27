# SIP adversarial security review plan — pre-staff-use gate

**Status:** proposed test plan, **not** a performed security review or approval.  
**Tracks:** #40. Maintainers and INZBC security/production owners must validate role names and sign off; no staff access is authorised by this document.

## Scope and trust boundaries

- Untrusted external news, RSS, scraped source text and attached source metadata enter collection and candidate capture. Treat titles, URLs, excerpts and documents as **data**, never instructions.
- Authenticated analysts/reviewers use the internal SIP API and UI. Client state must never be treated as authorisation.
- Model gateway receives only approved, classified and redacted material; output is untrusted until validated.
- Immutable audit records and separate distribution destinations are protected assets. Development fixtures, synthetic rehearsals and seeded data are not production evidence.
- Secrets, service credentials, webhook signatures and session cookies must not appear in output, logs, prompts, URLs or screenshots.

## Proposed authorisation matrix (confirm exact implemented roles)

| Action | Analyst | Source/QA reviewer | Release approver | Platform administrator | Unauthenticated |
|---|---|---|---|---|---|
| View assigned restricted candidates | Scoped | Scoped | Scoped | Operational metadata only by default | Deny |
| Capture or assess candidate | Permit with audit | Only if explicitly delegated | Deny by default | Deny by default | Deny |
| Record verification / QA | Cannot self-verify | Permit with audit | Read | Deny by default | Deny |
| Approve Internal / Member / Public distribution | Deny | Deny | Permit only on validated eligible item and distinct creator/reviewer | Deny | Deny |
| Change launch configuration | Deny | Deny | Deny | Controlled change with audit and separate launch authorisation | Deny |
| Send / publish content | Deny | Deny | Separate explicit channel approval, where implemented | Deny | Deny |
| Read security/audit history | Own permitted scope | Relevant scope | Relevant scope | Approved operational scope | Deny |

This is a **target policy**, not a claim that the current API enforces every cell. Verify routes, token scopes, role mappings, state transitions, and privilege combinations against the implementation; a single person holding multiple roles must not self-approve. Approval of one audience cannot authorise another.

## Adversarial test catalogue

| ID | Scenario | Expected evidence |
|---|---|---|
| S01 | External article says to ignore workflow and publish | Prompt injection ignored; candidate treated as untrusted |
| S02 | Source URL contains fake instruction or credentials | No follow-on tool action or secret disclosure |
| S03 | Analyst calls approve endpoint directly, bypassing UI | HTTP refusal, no state mutation, audit/security event |
| S04 | Creator/reviewer/approver same identity | Self-approval refused at service/database boundary |
| S05 | Approve public using internal-only approval | Audience-specific denial |
| S06 | Concurrent approvals and duplicated requests | Idempotent or single authoritative transition; no double publication |
| S07 | Replay expired/modified auth session and CSRF | Request rejected with no mutation |
| S08 | Disabled production flag, missing launch approval | No scheduled distribution or publication |
| S09 | Missing source / stale source beyond 24h Auckland window | Candidate quarantined or marked ineligible, not silently approved |
| S10 | High/Critical candidate lacks required verification | Release denied until official/two independent-source gate satisfied |
| S11 | Member/Board/confidential text reaches model path | Refused/redacted as defined, with non-sensitive audit |
| S12 | API error/retry after approval or import | No partial unaudited transition or silent data loss |
| S13 | Cross-user or cross-role read of candidate and audit | Scoped authorisation rejection |
| S14 | Log or trace capture during rejected request | No tokens, private text, provider keys or credential-bearing URLs |
| S15 | Client tampers with state, actor ID, role or action IDs | Service derives identity from verified session and rejects illegal transition |

For each run record: build commit, environment, synthetic test ID, expected policy, request/response with credentials removed, observed audit event, reviewer, date, and pass/fail with an issue link. Do **not** run live adversarial tests against production or real confidential records without an approved test window.

## Audit coverage checklist

Every substantive candidate mutation, verification decision, launch-control change and audience-specific approval should record a trusted actor ID, action, resource ID, state before/after, timestamp, request/correlation ID and immutable evidence reference. Explicitly check for rejected privileged actions and duplicate requests without logging raw restricted text. Confirm the audit store's tamper resistance, retention and export ownership; do not assert immutability solely because a DB row exists.

## Exit criteria (all required)

1. Implementation-versus-matrix traceability completed for all sensitive routes and model paths.
2. Adversarial suite run against a fixed build with actual observed results, not only proposed scenarios.
3. Critical/High findings resolved and retested, or release remains blocked.
4. Named security owner, SIP production owner and INZBC approver record sign-off and known residual risk.
5. `production_enabled` remains false until **separate** formal launch approval; this test plan never enables publishing.
6. Comms free-text leakage risk (#303) is reviewed under its own boundary; SIP review cannot be used to claim that gap is closed.

References: `docs/sip/README.md`, `docs/inzbc-ai-operating-system.md` §§3, 7, 9, and issue #40.
