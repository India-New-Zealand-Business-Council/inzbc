# ADR-0011 (PROPOSED): reconcile CEO decision records with persisted run states

**Status:** Proposal for technical-lead and sponsor review — **not adopted, not implemented, and not an authority to deploy**  
**Prepared:** 28 October 2026  
**Issue:** #127; related #55, #129, #291  
**Existing authority:** `docs/decisions/ADR-0010-signed-human-decisions.md`, ADR-0005, `schemas/state-machine.md`, SIP-184/SIP-188 and `docs/sip/launch/launch-config.md`. This proposal does **not** supersede the existing controlled launch procedure.

## Problem reproduced by code-path inspection (not a real-data test)

`apps/sip/ui/src/api/reportsStore.ts:recordCeoDecision()` posts to `POST /api/reports/{id}/ruling`, then locally returns a `DailyBriefReport` whose `state` is changed to `Continue`, `Continue With Correction`, `Paused` or `Stopped`.

The API `services/api/reports.py:_record_decision()` only calls `DecisionRepository.record()`. That repository transaction appends a decision and moves its stream head, **but it does not move `runs.state` or bump `runs.version`**. `GET /api/runs/{id}` therefore can continue returning `Awaiting CEO Decision`, and actions requiring a later state may fail after refresh. No system should present a local optimistic state as a durable human-approved transition.

`authoriseDistribution()` has a similar local optimistic state update to `Approved for Manual Distribution` after recording a Distribution Authority decision. The current run-state transition is not committed there either.

## Existing state-machine nuance: do not apply a simplistic fix

The legal table in `apps/sip/core/orchestrator.py` permits **five** targets from `Awaiting CEO Decision`: `Continue`, `Continue With Correction`, `Paused`, `Stopped` and `Approved for Manual Distribution`. `Continue` and `Continue With Correction` are currently terminal in that table; there is **no** legal `Continue -> Approved for Manual Distribution` transition.

Therefore automatically moving `runs.state` to `Continue` as soon as a CEO ruling arrives would make a subsequent legitimate, separately authorised distribution impossible without changing the state machine. Conversely an automatic `Awaiting CEO Decision -> Approved for Manual Distribution` on the ruling alone would bypass the distinct report-approval/distribution-authority requirements. Neither is acceptable.

## Proposed design for review

**One domain owner for run/decision coordination.** Add a server-side application service/command that locks the run and relevant decision-stream heads in one documented order, resolves all permissions from the authenticated principal, records the decision and (when a resulting state is authorised) the state change, and writes audit evidence **in the same Postgres transaction**. Do not split the operation across `DecisionRepository.record()` and `RunRepository.apply_transition()` using separate independent database connections; that permits one to commit when the other rolls back. Preserve existing append-only decision records, expected stream revision, run version CAS and role/SoD/signature gates; do not bypass them with an extra UPDATE.

**Proposed mapping needing approval:**

| Event | Proposed persisted state rule | Required evidence and refusal |
|---|---|---|
| CEO ruling `Pause` | `Awaiting CEO Decision -> Paused`, committed with ruling | CEO decision record for this exact report/run, verified actor, version and audit |
| CEO ruling `Stop` | `Awaiting CEO Decision -> Stopped` (terminal), committed with ruling | Same; no resurrection or automatic resumption |
| CEO ruling `Continue` | **Remain Awaiting CEO Decision** while approval/distribution choice remains unresolved; display ruling as a separate recorded fact | A ruling is **not** yet report approval or distribution authority |
| CEO ruling `Continue With Correction` | Decide whether correction is terminal at the present version or a return-to-revision branch; do not silently relabel local state | Must not authorise distribution of an unreviewed correction; requires recorded product/controlled-SOP choice |
| Report approval + Distribution Authority `Authorised`, CEO ruling exactly `Continue` | `Awaiting CEO Decision -> Approved for Manual Distribution`, atomically with the final authorising event | Requires actual Approved report approval, Continue ruling, no open Critical QA, exact-version/recipient-bound authorisation and full audit |
| Distribution Authority `Not Authorised` after Continue | Proposed `Awaiting CEO Decision -> Continue` with no send | Explicit refusal is a recorded decision; no distribution, and the run must have a defined closeout path |
| Actual manual send | `Approved for Manual Distribution -> Distributed` only on recorded delivery | Delivery evidence is not release authority; recipient/version must match approved record |

The proposed `Continue` staging, correction disposition and no-send terminal handling are **questions for the domain owner**, not permission to change the existing state machine. Some decision streams permit correction/supersession; assess whether a prior ruling can be changed after a terminal transition. Scope the command to the **current immutable report version**, not merely the run ID.

**Read API contract:** A write response must either include the committed `runs.state` and `runs.version`, or require the UI to re-fetch them before enabling the next action. UI may show the human ruling as *recorded* while the run still awaits the additional authorisation; it may not fabricate a completed transition. Never auto-retry a human decision after a timeout/409.

## Required verification before adoption

1. **Transactional rollback:** deliberately fail stream append, run update or audit insert and verify none of the three persisted; no orphan decision record/head.
2. **Two writers / concurrency:** same run with competing or duplicate ruling and distribution submissions; one legal resulting state, no lost updates or double decision on idempotent replay.
3. **Exactly-once semantics:** known idempotency key with identical request yields documented replay; same key and changed contents conflicts deterministically. Cover response-lost retries and stale stream revisions.
4. **Gate integrity:** refuse wrong run, wrong report version, wrong decision kind, unknown approver, revoked role, self-decision without valid SoD exception, missing signing key when enforcement is configured, missing report approval, QA fail and recipient mismatch.
5. **All five branch outcomes:** `Pause`, `Stop`, `Continue`, `Continue With Correction`, `Approved for Manual Distribution`; ensure the documented follow-up transitions actually exist, especially no-send and correction.
6. **Browser with real Postgres:** record the decision, reload from `GET /api/runs/{id}`, verify state/version match the UI, verify illegal action is refused. Mock-backed #490 does not prove this.
7. **Audit/replay:** decision ID and run-state audit row must reconcile; replay after process restart should report the same authority and state with no invented transition.

## Rollout, compatibility and open decisions

- Keep automated production and distribution disabled. No migration should be applied to INZBC systems before the technical lead approves the contract, reports existing run/version migration needs, and the sponsor accepts any controlled-SOP amendment.
- Existing `/ruling`, `/approval`, `/distribution` API clients and any saved decision streams require a compatibility strategy: do not change semantics invisibly behind an unchanged client.
- Decide whether CEO `Continue` waits for distribution/approval, how `Continue With Correction` moves to a corrected report, how a `Not Authorised` branch closes, and whether superseded rulings may reverse earlier run state.
- Independent QA versus single-person SoD exception must be displayed honestly as required by #266 and SIP-188; no recorded exception can be mistaken for a second reviewer.
- Until the transactional implementation passes the real database tests, report the gap under #127 and keep any live-run claim or client acceptance conditional.

**Decision requested:** Bhanu (technical lead) and Sunil (domain/sponsor) to select and approve the legal transitions and user journey. This PR carries engineering analysis only, no credentials, production writes or new approval authority.
