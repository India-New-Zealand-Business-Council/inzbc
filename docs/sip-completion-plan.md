# SIP completion plan

Status: proposed 27 August 2026. Owner: Bhanu. Covers the week of 27 August to 2 September.

## What this plan is for

SIP has more built than its issue list suggests. Every screen exists, the run state machine
works, the candidate commands work, and the review UI now runs against the real API rather than
fixtures (#336, merged as #339). What it cannot do is finish a run. A run reaches the decision
gate and stops, because the code that records a decision has no HTTP surface.

This plan closes that gap and the two defects behind it, then proves the whole thing with one
real end-to-end run. It does not try to build everything still open against SIP.

## The one thing blocking everything

`services/api/decisions.py` implements `DecisionRepository.record` with its separation-of-duties
checks, its append-only writes and its approval-reference validation. **No `APIRouter` is mounted
for it.** `services/api/main.py` includes thirteen routers and decisions is not one of them. That
is deliberate: the module was left off the HTTP surface until INZBC answered who is allowed to
record each kind of decision, which is #348.

Three things wait on it, and they are not three problems:

1. **CEO Decision screen (#293).** `apps/sip/ui/src/screens/CeoDecisionScreen.tsx` is built and
   correct. Both its actions are fixture-backed because there is nothing to call.
2. **QA fail path (#292).** `POST /api/runs/:id/fail-qa` is human-gated and needs `approval_ref`
   to name a real `decision_records` row. Nothing can create one, so a Critical QA failure cannot
   actually stop a run. Only the Pass path works today.
3. **Candidate self-verification exception (#292).** `record_verification` needs an approved
   `candidate_sod_exceptions` row and there is no endpoint to create one.

**#348 is now answerable.** The client's position is that Sunil holds every role, and the agreed
approach is one account per role with Sunil holding the credentials for all of them. That is
enough to seed `decision_role_permissions` and proceed.

## Two defects that must be fixed in the same week

**`runs.analyst_id` is never written.** `services/api/decisions.py:538` guards QA self-review
with `if analyst is not None and analyst == actor`. `create_run` does not set the column and
nothing else writes it, so it is NULL on every run and the guard has never fired in production.
The control is documented, tested against a fixture that sets the column directly, and dead where
it matters. Under one person holding every role this is the control doing the most work.

**Separation of duties is mechanical, not real, and the documents must say so.** Distinct
accounts give distinct UUIDs, so `canonical_actor` sees different principals and every guard
fires correctly. One human still drives all of them. The system will be satisfied; the control
will not be. Recording this as "separation of duties enforced" would be false, and the honest
version is that every run carries a recorded exception, which the schema already supports.

## The week

**Day 1. Unblock the decision gate.**
Seed `roles` and `decision_role_permissions` as a migration under `database/migrations/`, mapping
the three `decision_kind` values (`CEO Ruling`, `Report Approval`, `Distribution Authority`) to
the roles allowed to record them. Create one user account per role and hand all credentials to
Sunil. Close #348 with the mapping written down, not just applied.

**Day 1 to 2. Mount the decisions router.**
A `services/api/decisions_api.py` exposing record-decision for the three kinds, plus the two
exception-creation endpoints (`sod_exceptions`, `candidate_sod_exceptions`). The repository logic
already exists and is tested; this is the HTTP surface it never got, not new business logic.
Regenerate `schemas/openapi.json` and the TypeScript clients.

**Day 2. Fix `analyst_id`.**
Populate it at the point the analyst first acts on the run rather than at creation, since the
person who starts a run is not necessarily the analyst. Add a regression test that fails if the
QA self-review guard stops firing.

**Day 2 to 3. Wire the two screens (#293, #292).**
`CeoDecisionScreen` and `QaReviewScreen`'s fail path move off fixtures onto the new endpoints.
Both screens already exist and are tested; this is a client swap.

**Day 3. Brief Builder source table (#344).**
The 112-source table has nothing for the analyst to work from. Data problem, not a build problem.

**Day 4. One real end-to-end run (#55).**
Draft to Distributed through the SIP-184 SOP, using Sunil's role accounts, against a real
Postgres. Every gate crossed by the account that is supposed to cross it, with the audit log and
decision records inspected afterwards rather than assumed.

**Day 4 to 5. Close out.**
Adversarial security review (#40), then #189 and the handover pack (#291).

## Not in this week, and why

#62 agentic orchestrator, #63 pgvector, #64 LLM-as-judge, #38 eval harness, #39 scoring v0.2 and
#61 executive dashboard UI. These are the AI flagship builds. SIP is a governed intelligence
platform without any of them, and adding them does not make a run complete. They stay specified
and open.

## What this plan cannot deliver

- **Deployment.** `production_enabled` is false and no environment exists. Gated on #99 and #97,
  both client decisions. Everything above is provable locally and nowhere else.
- **Real separation of duties.** See above. One person, several accounts.
- **A signed security review.** #40 produces the review; INZBC signing it is not ours to do.
