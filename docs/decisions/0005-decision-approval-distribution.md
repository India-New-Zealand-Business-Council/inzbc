# ADR-0005: One authoritative record stream per decision, approval and distribution

- Status: Accepted
- Date: 2026-07-30
- Deciders: Bhanu (tech lead). Affects Roshan's run and persistence work and Paras's decision screen
- Addresses issue #114. Does **not** unblock #120 or #121 — see Required follow-up
- Does **not** resolve the run-state topology — see Open questions

## Context

Four artefacts describe what happens when the CEO rules on a run — `RunState`
(`apps/sip/pipeline/models.py:52-70`), `schemas/state-machine.md`, `database/schema.sql` and
`schemas/api-contract.md` — and they do not agree. Two engineers are about to build on top of them
and the CEO decision screen is blocked behind the same ambiguity (#57, REQ-U-02).

The run-state vocabulary is not the problem. `RunState` and the `run_state` enum carry the same
18 values in the same order, and `apps/sip/pipeline/tests/test_models.py:60-66` asserts it. The
problem is that **the database models decision, approval and distribution as separate columns
while the state machine folds them into one line** — and that even the database's separation is
too weak to record what the governance documents require.

Three sources say decision, approval and distribution are distinct facts.

`docs/requirements.md:91-100`, REQ-G-04, priority Must:

> As the **CEO**, I need approving the report and authorising its distribution to be two distinct
> recorded decisions, so that approval alone never causes something to be sent.

`docs/sip/launch/SIP-184_daily_run_SOP_v0.9.md:54-57` records one decision plus a separate
`distribution authorised Yes/No` and an authorised version. `docs/sip/operator-guide.md:169-185`
says the same and adds the case that decides the shape of everything else:

> **"Distribution authorised: No" does not stop the run.** It is a valid outcome: step 13 is
> skipped, and the run proceeds to close-out and is recorded as approved but not distributed.
> Only a Pause or Stop decision halts the run.

So a run can be approved, not distributed, and still close. Any model that treats "the CEO said
Continue" and "distribution is authorised" as one fact cannot express that.

**The current `approvals` table cannot express it either.** `database/schema.sql:169-181` stores a
mutable row whose `distribution` column is `not null default 'Not Authorised'`, so an explicit CEO
"No" is indistinguishable from a run nobody has ruled on yet. Its single `approver_id` and
`decided_at` belong to the whole row, so a distribution decision has no actor or timestamp of its
own — exactly what `SIP-050 §26` requires be recorded per decision. And because the row is mutable,
a correction overwrites its predecessor, which `SIP-050 §24` forbids:

> Do not overwrite run evidence. Retain source outcomes, candidate decisions, verification, report
> versions, QA, **approvals, distribution decisions**, exceptions and corrections. Correct a record
> through a linked correction or superseding record.

This ADR decides the record shape and the controlled-launch decision rule. The run-state topology
is left open deliberately: the options differ in migration cost and that is a separate call.

## Decision

### 1. One authoritative record stream per decision fact

CEO ruling, report approval and distribution authority are three **immutable decision streams**
recorded against an immutable report version. They are not columns on a mutable row.

| Fact | Authoritative source | Not to be read from |
|---|---|---|
| Where the run has reached operationally | `runs.state` | decision records |
| What the CEO ruled | current record of the CEO-ruling stream | `runs.state`, `runs.qa_status` |
| Whether a report version is approved | current record of the report-approval stream | `runs.state` |
| What distribution is authorised | current record of the distribution-authority stream | `runs.state` |
| What was actually sent | delivery record | any decision stream |

Rules:

- **Absence after submission means undecided.** Once a report version is submitted for decision, a
  stream with no current record means "not yet decided". `Not Authorised` is an explicit refusal.
  The two are never stored as the same value.
- **Each record carries its own actor and time**, plus reason, conditions, owner, evidence
  reference and next review (REQ-U-02, `docs/requirements.md:224-234`; `SIP-050 §26`).
- **Corrections append a superseding record.** Records are never updated or deleted. The
  application role holds `SELECT` and `INSERT` on decision records and no `UPDATE` or `DELETE`.
- **Distribution delivery is an execution record, not an authority state.** Sender, recipient,
  channel, sent time and result (`docs/sip/operator-guide.md:187-192`) belong to a delivery record
  referencing the authority decision, not to the authority decision itself.
- **Combined reads go through one named current-decision view.** Consumers do not each invent a
  derivation rule.
- **`runs.state` is not a projection of these records** and must not be derived from them. The
  streams carry decision acts only; scanning, QA and close-out transitions are not decision acts.
- **A decision and any state transition it gates commit in one transaction.**

The existing `approvals` row (`database/schema.sql:169-181`) is hereby a **superseded draft shape**,
not the target. This requires a schema change. It is cheap now: `schema.sql` is an unmigrated draft
(see its header) and no production data exists.

### 2. Controlled-launch decision values and the release predicate

Values, during the controlled launch:

| Stream | Values | Pending |
|---|---|---|
| CEO ruling | `Continue`, `Continue With Correction`, `Pause`, `Stop` | no current record |
| Report approval | `Approved`, `Rejected`, `Returned for Correction` | no current record |
| Distribution authority | `Authorised`, `Not Authorised` | no current record |

`Authorised` is valid **only** when all hold for that exact immutable report version:

1. its current report approval is `Approved`;
2. its current CEO ruling is `Continue`;
3. no open Critical QA failure;
4. the recipient is the single configured recipient.

`Continue With Correction` does not permit release. It requires a corrected report version, a fresh
approval and a fresh authority decision before anything is sent.

Fail-closed, and **total**: any requested scope other than the single internal recipient is
rejected. `docs/sip/launch/launch-config.md:33-46` requires seven controls to stay false —
automated email, member, external-stakeholder, website, social, automatic publication and
autonomous approval. A request touching any of them is refused, not stored.

Further invariants:

- `Not Authorised` is valid alongside any ruling. `Approved` + `Not Authorised` is the valid
  closed-without-send outcome the operator guide requires.
- `Pause` or `Stop` together with a current `Authorised` is invalid.
- Missing authority and explicit `Not Authorised` both block sending, and remain distinguishable.
- A superseding ruling or approval that invalidates existing authority must supersede that
  authority in the same transaction.
- **The recipient is revalidated at send time, not only at authorisation.** Condition 4 is checked
  again when the delivery commits. If the configured recipient has changed since the authority was
  granted, that authority is stale: the send is refused and a fresh distribution decision is
  required. Delivery never sends to a recipient the current configuration does not name, and never
  to one the authority record did not name. Both must agree.

The CEO ruling and the distribution authority are **separate commands**, not one endpoint writing
two fields. REQ-U-02 requires distribution to be captured as a separate action; one submission
writing two records is still one action.

`docs/client-answers.md:48` (B8) names the single recipient but is marked `PROPOSED`. The recipient
is configuration, not a constant in this ADR, and stays fail-closed until B8 is confirmed.

### 3. Two constraints on whatever topology is chosen

Recorded so the open topology question cannot be resolved in a way that reintroduces the defect.

**A run that is approved with distribution `Not Authorised` must reach close-out without passing
through `Distributed`.** Today the only path to `Closed` is
`Approved for Manual Distribution -> Distributed -> Closed`
(`apps/sip/core/orchestrator.py:45-46`), which cannot express the outcome
`docs/sip/operator-guide.md:183-185` requires.

**No send, delivery record, or distribution-asserting state transition may commit unless it
references the current `Authorised` decision for that exact immutable report version.** The
authority check, the delivery insert, the audit insert and any resulting state transition share one
transaction. Nothing enforces this today: `runs.state` has no constraint referencing `approvals`,
and `ceo_decision`, `approver_id` and `decided_at` are all nullable
(`database/schema.sql:38-56,169-181`). `HumanDecision` (`apps/sip/core/orchestrator.py:102`)
validates that a decision is non-blank and attributable, but it is an in-memory object; nothing
requires a persisted record to exist.

### 4. The operator guide contradiction must be resolved before build

`docs/sip/operator-guide.md:208-221` lists "a human approval is missing, or distribution was not
authorised" among reasons to stop the run. `:183-185` says an explicit `No` does **not** stop the
run. The stop list carries no qualifier distinguishing the two, so the guide contradicts itself.

An earlier revision of this ADR claimed the guide was consistent when read as being about sending
without authority. That reading is not supported by the text and **is withdrawn**.

This is a process question for the CEO / SIP Owner, not a code fix. The proposed clarification:

> Missing approval or authority stops distribution. An explicit "Distribution authorised: No" skips
> the send and permits close-out; it does not stop the run.

## Consequences

**Positive.** Decision, approval and distribution become separately recorded, separately attributed
and separately correctable, which is what REQ-G-04, REQ-U-02 and `SIP-050 §24` and `§26` already
require and the current schema cannot deliver. The controlled-launch rule is total and fail-closed
against all seven launch controls. Approved-but-not-distributed becomes expressible. The two
constraints stop the next attempt at the topology from re-conflating approval with distribution.

**Negative, and the mitigations.**
- This needs a schema change; the previous revision claimed it did not. Mitigation: `schema.sql` is
  an unmigrated draft and there is no production data, so the cost is a rebase, not a migration.
- Four tables where there was one. Mitigation: this is selective append-only recording of decisions
  only. It is not event sourcing; `runs` and the rest of the pipeline stay ordinary mutable tables.
- More endpoints, since ruling and authority split. Mitigation: REQ-U-02 requires it.
- The topology remains undecided, so the approved-but-not-distributed path is still not buildable.

**Withdrawn claims.** The previous revision asserted that this required no migration, that #120 and
#121 could proceed, that the decision screen was "unblocked on data shape", that a consumer could
derive a combined view without a normative rule, and that the operator guide needed no
clarification. None of those hold.

## Required follow-up

These block a valid implementation. They are work items, not open decisions.

1. **Item membership.** `report_versions` gives a version an identity, but nothing yet says which
   items a version contains. `daily_intelligence` is per-item and carries its own `approval`
   column (`database/schema.sql:112-127`), so "the items in this approved version" is still not a
   question the database can answer, and report approval cannot be related to item approval.
   Approving a version is only meaningful once it is.
2. **Decision metadata.** Reason, conditions, owner, evidence reference and next review do not
   exist in the schema. REQ-U-02 cannot be satisfied without them.
3. **Durable QA evidence.** The release predicate needs "no open Critical QA failure" to be a
   queryable fact. `runs.qa_status` is free text and no QA record table exists; SIP-188 requires
   Pass/Fail, critical failures, corrections, reviewer signature and timestamp.
4. **Separation of duties binds to roles, not to people.** `schemas/api-contract.md:7-8` says nobody
   approves their own output, but `docs/sip/launch/launch-config.md:12-24` assigns CEO/SIP Owner
   **and** Primary Analyst to the same person, and `database/schema.sql:55` enforces
   analyst-vs-reviewer only. The rule is therefore expressed per decision kind against the **role
   held at the time of the act**, with the required-distinct pairs held in configuration rather than
   hardcoded. Where one principal necessarily holds both roles, the decision still commits, but only
   with a recorded exception naming the approver, the reason and a review date. Silent bypass is not
   a permitted outcome; an unrecorded self-approval is refused.

   This replaces the single `users.role_id` column with a `user_roles` table, superseding the
   one-column mapping described in [ADR-0004](0004-platform-graduation.md) at its role-mapping note.
   That decision's intent, that role mapping is data rather than code, is unchanged.

   This is deliberately not a staffing fix. The current three-engineer split is a 16-week placement,
   so the steady state after it ends is one person holding every role, or a delegation to someone not
   yet named. Single-principal operation must stay valid with no schema change and no code change:
   only the configured role pairs and the exception record change. The audit trail then shows who
   acted in which capacity and under what exception, which is what `SIP-050 §26` asks for and what a
   handover needs.
5. **Concurrency, idempotency and grants.** One-current-record-per-stream enforcement, an
   idempotency key, and `INSERT`-only grants scoped to decision records — not to the whole
   application role, which needs `UPDATE` on `runs`.
6. **API contract and transaction boundary.** `schemas/api-contract.md` splits into separate ruling
   and authority commands. PR #163's `RunRepository` opens and commits a connection per method, so
   "insert decision, then transition" cannot currently be atomic; it needs a unit-of-work path for
   human-gated transitions. Its `runs.version` optimistic-concurrency column is useful and should be
   reused, not removed. Because its CI applies `schema.sql` directly, amend the schema first and
   rebase #163 rather than merging the superseded `approvals` shape.
7. **Candidate assessment command.** The previous revision also proposed replacing
   `PATCH /api/candidates/:id` with `POST /api/candidates/:id/assess`. It is unrelated to decision
   authority and made this ADR two decisions. It moves to its own ADR or issue note, unchanged in
   substance.

## Open questions

Genuine topology decisions. None blocks the record shape above.

1. **State topology for approved-but-not-distributed.** Either add a state meaning "CEO approved,
   distribution decided separately" that can reach both `Distributed` and `Closed`, or keep
   `Approved for Manual Distribution` and add a direct transition to `Closed`. The second is a
   smaller migration but leaves a state whose name asserts more than it means. **Bhanu.**
2. **Whether `Continue` and `Continue With Correction` leave `run_state`.** They have no outgoing
   transition (`schemas/state-machine.md:24-25`; `apps/sip/core/orchestrator.py:36-54`), which is
   what identifies them as decision outcomes rather than states. Removal touches the orchestrator
   and its tests, `models.py`, `schema.sql`, `state-machine.md`, and the architecture and daily-run
   records that also encode them. Depends on question 1. **Bhanu.**
3. **`Corrected` and `Withdrawn` are unreachable.** Enum values described as post-close branches
   with no transition entering them (`schemas/state-machine.md:10-11`;
   `apps/sip/core/orchestrator.py:48-54`). **Bhanu.**
4. **Are `Internal` / `Member` / `Public Approved` ordered levels or independent grants?** Not
   needed for the controlled launch, which rejects everything but the single internal recipient.
   `docs/sip/README.md:10-24` plans an approved public feed, so this becomes live before that ships.

## References
- Issue #114 — the disagreement
- `docs/requirements.md` — REQ-G-04 (:91-100), REQ-U-02 (:224-234)
- `docs/sip/launch/SIP-050_master_prompt_v1.1.md` — §24 append-only evidence, §26 approval and
  distribution authority
- `docs/sip/launch/SIP-184_daily_run_SOP_v0.9.md` §12-13 — one decision, separate distribution
  authority
- `docs/sip/launch/launch-config.md` — roles (:12-24), controls that stay false (:33-46)
- `docs/sip/operator-guide.md` — Step 12 (:169-185), Step 13 (:187-192), the stop list (:208-221)
- `docs/sip/launch/SIP-188_qa_checklist_v0.9.md` — the QA record follow-up 3 depends on
- `database/schema.sql`, `schemas/state-machine.md`, `schemas/api-contract.md`,
  `apps/sip/pipeline/models.py`, `apps/sip/core/orchestrator.py`
- [ADR-0004](0004-platform-graduation.md) — expand-then-contract migration approach
