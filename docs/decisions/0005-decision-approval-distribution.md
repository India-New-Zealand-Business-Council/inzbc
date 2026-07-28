# ADR-0005: One authoritative field per decision, approval and distribution

- Status: **Proposed** — Bhanu to accept or amend
- Date: 2026-07-28
- Deciders: Bhanu (tech lead). Affects Roshan's run and candidate endpoints and Paras's decision screen
- Partially addresses issue #114. Unblocks #120, #121. Does **not** resolve the state topology — see
  Open questions

## Context

Four artefacts describe what happens when the CEO rules on a run — `RunState`
(`apps/sip/pipeline/models.py:52-70`), `schemas/state-machine.md`, `database/schema.sql` and
`schemas/api-contract.md` — and they do not agree. Two engineers are about to build endpoints on
top of them (#120, #121) and the CEO decision screen is blocked behind the same ambiguity (#57,
REQ-U-02).

The run-state vocabulary is not the problem. `RunState` and the `run_state` enum carry the same
18 values in the same order, and `apps/sip/pipeline/tests/test_models.py:60-66` asserts it. The
problem is that **the database models decision, approval and distribution as separate columns
while the state machine folds them into one line.**

Three sources say the database is right.

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

This ADR decides only the authority rule and the controlled-launch mapping. The state topology
needed to express approved-but-not-distributed is left open deliberately, because the options
differ in migration cost and that is Bhanu's call, not a detail.

## Decision

### 1. One authoritative field per fact

| Fact | Authoritative field | Written by | Must not also live in |
|---|---|---|---|
| Where the run has reached | `runs.state` | the pipeline, on legal transitions only | `approvals`, `runs.qa_status` |
| What the CEO ruled | `approvals.ceo_decision` | the decision endpoint | `runs.state` |
| Whether a report version is approved | `approvals.approval` | approve / request-changes | `runs.state` |
| What distribution is authorised | `approvals.distribution` | the decision endpoint | `runs.state` |

A consumer needing a combined view derives it. No endpoint writes the same fact to two places, and
no new endpoint may introduce a second home for one of these four.

This is the rule #120 and #121 need in order to proceed. It does not require a migration.

### 2. Controlled-launch distribution mapping

Until the scope semantics are decided (Open question 6), the decision endpoint maps:

| CEO input | `approvals.distribution` |
|---|---|
| Distribution authorised: Yes | `Internal Approved` |
| Distribution authorised: No | `Not Authorised` |
| anything requesting Member or Public | **rejected, fail-closed** |

`SIP-184 §13` and `operator-guide.md:187-192` keep member, external, public and social distribution
off during the controlled launch, and `docs/client-answers.md` B8 names a single recipient. Writing
`Member Approved` or `Public Approved` today would record an authority nobody has granted, so the
endpoint refuses rather than storing it.

### 3. Candidate mutation becomes one named command, and stays atomic

Replace `PATCH /api/candidates/:id` with `POST /api/candidates/:id/assess`, taking the same payload.

Issue #114 asks for explicit commands so an audit record can name what was done. It does not
require splitting one operation into four. `CandidateAssessment`
(`apps/sip/collector/assessment.py:39`) carries relevance, signal, confidence, verification,
duplicate linkage, inclusion, reason and routing as one payload, and
`apply_candidate_assessment` (`:56`) computes `effective_signal` and `effective_verification`
across the combined update before calling `enforce_verification_gate` (`:87-89`). Splitting that
across `/score`, `/verify`, `/merge` and `/route` would create exactly the transient
signal-without-verification states that gate exists to reject.

One named command keeps the atomicity and names the intent. The existing `/verify`, `/score`,
`/route` and `/merge` commands stay for single-purpose use.

Migration is expand-then-contract: add `/assess`, switch `SipPipelineClient.patch_candidate`
(`apps/sip/pipeline/client.py:100-101`) and its ten tests, then remove the PATCH from the contract.

### 4. Two constraints on whatever topology is chosen

Recorded here so the open question cannot be resolved in a way that reintroduces the defect:

**A run that is approved with distribution No must reach close-out without passing through
`Distributed`.** Today the only path to `Closed` is
`Approved for Manual Distribution -> Distributed -> Closed` (`schemas/state-machine.md:24-28`),
which cannot express the outcome `operator-guide.md:183-185` requires.

**No state advance that asserts distribution authority may occur without a complete `approvals`
row.** Nothing enforces this today: `runs.state` has no constraint referencing `approvals`, and
`ceo_decision`, `approver_id` and `decided_at` are all nullable
(`database/schema.sql:38-55,169-180`). `HumanDecision` (`apps/sip/core/orchestrator.py:102`)
validates that a decision is non-blank and attributable, but it is an in-memory object; nothing
requires the corresponding `approvals` row to have been persisted.

### 5. A note on the operator guide, which is not contradictory

`operator-guide.md:208-221` lists "a human approval is missing, or distribution was not authorised"
among reasons to stop. That is about proceeding to **send** without authority, not about the CEO
deciding No. Missing is not the same as withheld. Read that way it agrees with Step 12, and no
clarification is needed before building.

## Consequences

**Positive.** #120 and #121 get an authority rule without waiting on a migration or a schema
redesign. The decision endpoint has a defined, fail-closed mapping. The atomic assessment survives
while gaining a name the audit log can record. The two constraints stop the next attempt at the
topology from re-conflating approval with distribution.

**Negative, and the mitigations.**
- The topology remains undecided, so the CEO decision screen (#57) is unblocked on data shape but
  not on the approved-but-not-distributed path. Mitigation: Open question 1 is scoped and has two
  candidate answers; it is a decision, not research.
- `/assess` plus four narrower commands is more surface than one PATCH. Mitigation: the PATCH goes
  away, so the count is net zero, and each remaining route names an action.
- The authority rule is convention until constraints exist. Mitigation: constraint 4B records what
  the persistence work (#117) must enforce.

## Open questions

Each is a real decision with a named blocker. None is deferred for convenience.

1. **State topology for approved-but-not-distributed.** Either add a state meaning "CEO approved,
   distribution decided separately" and let it reach both `Distributed` and `Closed`, or keep
   `Approved for Manual Distribution` and add a direct transition to `Closed`. The second is a
   smaller migration but leaves a state whose name asserts more than it means. **Bhanu.**
2. **Whether `Continue` and `Continue With Correction` leave `run_state`.** They have no outgoing
   transition (`schemas/state-machine.md:24-25`; `apps/sip/core/orchestrator.py:36-54`), which is
   what identifies them as decision outcomes rather than states. Removal touches eight files
   including the orchestrator, its tests and the architecture diagram, and depends on question 1.
3. **`approvals` does not satisfy REQ-U-02.** `docs/requirements.md:230-234` requires reason,
   conditions, owner, evidence reference and next review. None exist in
   `database/schema.sql:169-180`. Needs a schema change before the decision screen can be built.
4. **Report and item approval cannot be related yet.** `daily_intelligence.approval` and
   `approvals.approval` are separate `approval_state` columns, but there is no reports table, no
   report-version table and no item-membership, so "the items in this version" is not a question
   the database can answer. Any rule here must wait for that schema. It is not invented in the
   meantime.
5. **`runs.qa_status` cannot be dropped yet.** SIP-188 requires Pass/Fail, critical failures,
   corrections, reviewer signature and timestamp (`SIP-188_qa_checklist_v0.9.md:40-44`), and no QA
   record table exists (`database/schema.sql:169-194`). Add the replacement first, then contract.
6. **Are `Internal` / `Member` / `Public Approved` ordered levels or independent grants?** Deferred
   by decision 2's fail-closed mapping, not resolved. `docs/sip/README.md:10-24` plans an approved
   public feed, so this becomes live before Phase 2.
7. **`Corrected` and `Withdrawn` are unreachable.** Enum values described as post-close branches
   with no transition entering them (`schemas/state-machine.md:10-11`;
   `apps/sip/core/orchestrator.py:48-54`).
8. **`distribution_state` duplicates `run_state`.** Both carry `Distributed` and `Withdrawn`
   (`database/schema.sql:13-18`), so decision 1's invariant is not fully achieved until one gives
   way.

## References
- Issue #114 — the disagreement; #121 implements decision 3
- `docs/requirements.md` — REQ-G-04 (:91-100), REQ-U-02 (:224-234)
- `docs/sip/launch/SIP-184_daily_run_SOP_v0.9.md` §12-13 — one decision, separate distribution authority
- `docs/sip/operator-guide.md` — Step 12 (:169-185), the stop list (:208-221)
- `docs/sip/launch/SIP-188_qa_checklist_v0.9.md` — the QA record open question 5 depends on
- `database/schema.sql`, `schemas/state-machine.md`, `schemas/api-contract.md`,
  `apps/sip/pipeline/models.py`, `apps/sip/core/orchestrator.py`
- [ADR-0004](0004-platform-graduation.md) — expand-then-contract migration approach
