# SIP adversarial security review

**Date:** 20 November 2026  
**Scope:** SIP control plane, capture/import path, staff assistant, Comms provider path, audit
integrity and deployment gates.  
**Status:** code findings remediated in PR #570; staff use still requires the deployment and
owner sign-offs listed below.

## Threat model

| Threat | Boundary | Control |
|---|---|---|
| A model or caller crosses a human state transition | Agent output, UI and API state changes | `Orchestrator` transition allowlist; `RunRepository.apply_transition` resolves evidence inside the same PostgreSQL transaction |
| A valid evidence record from another run or report is replayed | Human-gate `approval_ref` values | Gate evidence is bound to current report version, run, actor, decision kind and permitted value |
| The report author or run analyst self-reviews | SIP-188 QA | QA rejects both `report_versions.created_by` and `runs.analyst_id` for the acting reviewer |
| Staff paste sensitive prose into an external model | Comms and Platform Assistant | Provider calls are default-deny until the approved deployment release; gateway redaction and prompt-source policy remain required |
| Imported text loses provenance or copies source article text into audit | Collector handoff to atomic import | Immutable digest checks, original article verification and per-candidate evidence-reference audit rows |
| A state transition commits without matching audit evidence | PostgreSQL durability boundary | State update and audit insert share one transaction; optimistic `version` check rejects races |
| A session or CSRF token is absent on a write | Browser-to-API boundary | `read_access` / `write_access` dependencies cover mounted business routers; anonymous requests fail before business handlers |
| A webhook leaks data in URLs or replays the same event | Wix producer boundary | Query strings are refused, body HMAC/timestamp is checked, event IDs are idempotent and database records carry a payload digest |

## Authorization matrix

| Actor | Principal permitted actions | Separation checks |
|---|---|---|
| Analyst | Create runs; capture/score/route/merge candidates; submit reports | Cannot QA a report they authored or a run they worked |
| Reviewer | Verify candidates; record QA; approve reports when not the author; fail QA and return failed work for correction | QA reviewer differs from report author and run analyst |
| SIP Owner | Launch/resume; CEO ruling; distribution authority; controlled administration | Decision evidence is actor-, kind-, value- and current-report-bound |
| Secretariat | Draft Comms; record controlled delivery evidence | Delivery transition requires the delivery row from the same sender and current report |
| Auditor | Read audit/history and internal evidence | No state-changing route |
| Other staff | Read staff surfaces and use released assistant/Comms paths | No write without the route's explicit roles and CSRF |

The canonical role checks are exercised by `services/api/tests/test_router_auth.py`; decision
and transition integrity is covered by the Postgres suites.

## Findings and disposition

1. **QA self-review when `runs.analyst_id` was null** — fixed. QA binds the acting reviewer
   against both run analyst and exact report author.
2. **Human-gate evidence not bound to report/actor/transition** — fixed. QA evidence, CEO
   rulings and delivery rows must match the current report version, exact transition/value,
   current run and acting actor. Unmapped human-gated edges fail closed.
3. **Platform Assistant bypassed provider release gating** — fixed. The assistant and Comms
   share the same explicit provider release dependency while session/CSRF remains mandatory.
4. **Atomic-import audit references reused the final candidate index** — fixed. Insertion now
   emits one evidence reference per candidate and a two-candidate regression verifies it.

## Remaining deployment gates

| Gate | Owner | Release condition |
|---|---|---|
| Production provider calls | Technical lead / SIP owner | Approved environment release; configured redaction policy; secret custody verified |
| Staff authentication assurance | Account owner / administrator | OIDC identity, role assignments, session controls and MFA confirmed for every owned account |
| Signed human decisions | Technical lead / database operator | `SIP_REQUIRE_SIGNED_DECISIONS=true` and a managed signing key in the deployed environment |
| Site-form data handling | Privacy/data owner + website owner | PIA/notice, retention, reader role, Wix secret custody and live signed-delivery evidence |
| SIP production capture/import | SIP owner + CEO | `production_enabled` remains false; no live run, source-rights sign-off or staging/import activation is implied by this review |
| Comms free-text exposure | Comms owner + privacy owner | Structured input and release gating are implemented; explicit accepted-risk decision still required before any staff may send non-public prose to a provider |

This review is evidence for the code review gate, not a substitute for those owner decisions or
for production deployment approval.
