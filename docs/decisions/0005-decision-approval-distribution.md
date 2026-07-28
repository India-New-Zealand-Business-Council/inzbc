# ADR-0005: Separate the CEO decision, the approval and the distribution authority

- Status: **Proposed** — Bhanu to accept or amend
- Date: 2026-07-28
- Deciders: Bhanu (tech lead). Affects Roshan's run and candidate endpoints and Paras's decision screen
- Unblocks: issues #120, #121, #124, #125, #126, #127, and the CEO decision screen (REQ-U-02)

## Context

Four artefacts describe what happens when the CEO rules on a run, and they do not agree:
`RunState` (`apps/sip/pipeline/models.py`), `schemas/state-machine.md`, `database/schema.sql`
and `schemas/api-contract.md`. The decision screen cannot be built against four sources that
disagree, and two engineers are about to build endpoints on top of them.

The run-state vocabulary itself is fine: `RunState` and the `run_state` enum in `schema.sql` carry
the same 18 values. The disagreement is structural — **the database treats decision, approval and
distribution as three independent axes, while the state machine folds all three into one line.**

The SOP the system implements already treats them as separate. SIP-184 §12:

> CEO records one decision: Continue / Continue with Correction / Pause / Stop, with reason,
> conditions, owner, evidence, next review, **distribution authorised Yes/No**, authorised
> version, timestamp.

One decision, a separate distribution authority, and a separate authorised version — three facts
recorded together, not one value. The database matches that shape. The state machine does not.

Six concrete conflicts follow.

**1. `Continue` and `Continue With Correction` are orphan states.** `state-machine.md` line 25
allows `Awaiting CEO Decision -> {Continue | Continue With Correction | Paused | Stopped}` but
lists no transition *out of* either. `Paused -> Coverage Locked` exists and `Stopped` is explicitly
terminal, so those two behave like states. The other two are dead ends. They are not states at all;
they are the CEO's ruling, which is already how the database stores them:

```sql
ceo_decision  text,  -- Continue / Continue with Correction / Pause / Stop
```

**2. Distribution scope cannot be expressed in the run state.** `distribution_state` distinguishes
`Internal Approved`, `Member Approved` and `Public Approved`. `run_state` has one value,
`Approved for Manual Distribution`. A run cleared for internal circulation only is
indistinguishable from one cleared for members.

**3. The same fact lives in two columns with no stated authority.** `approvals.ceo_decision` holds
Continue / Pause / Stop; `runs.state` holds Continue / Paused / Stopped. Two writers, one truth,
and nothing says which wins when they diverge.

**4. Two `approval_state` columns, no stated relationship.** `approvals.approval` covers a report
version; `daily_intelligence.approval` covers a single intelligence item. Whether an approved
report may contain a Pending item is undefined.

**5. `runs.qa_status` is free text** sitting alongside `run_state`'s `QA In Progress` and
`QA Failed`, and alongside the SIP-188 QA record written through `POST /api/reports/:id/qa`.
Three places record QA outcome; none is named as authoritative.

**6. The blanket PATCH survives alongside the explicit commands it was meant to replace.**
`api-contract.md` lines 20-21 carry both `PATCH /api/candidates/:id` and
`POST /api/candidates/:id/verify | /score | /route | /merge`. A PATCH cannot produce a meaningful
audit entry, because the server never learns which action was intended — only which columns moved.

## Decision

### 1. Three axes, one authoritative field each

| Concern | Authoritative field | Written by | Must not be duplicated in |
|---|---|---|---|
| Where the run has reached | `runs.state` | the pipeline, on legal transitions only | `approvals`, `runs.qa_status` |
| What the CEO ruled | `approvals.ceo_decision` | the decision endpoint | `runs.state` |
| Whether a report version is approved | `approvals.approval` | the approve / request-changes endpoints | `runs.state` |
| What distribution is authorised, and to whom | `approvals.distribution` | the decision endpoint | `runs.state` |

No fact appears in two places. Where a consumer needs a combined view, it derives it; it does not
store it.

### 2. `run_state` records lifecycle position only

Remove `Continue` and `Continue With Correction` from `RunState` and from the `run_state` enum.
They are `ceo_decision` values, not states, and they have no exits today.

Keep `Paused` and `Stopped` — both describe the run itself and both have defined behaviour.

The CEO decision then routes the run rather than becoming it:

```
Awaiting CEO Decision --(decision: Continue)-->                Approved for Manual Distribution
Awaiting CEO Decision --(decision: Continue With Correction)-->Report Drafted
Awaiting CEO Decision --(decision: Pause)-->                   Paused
Awaiting CEO Decision --(decision: Stop)-->                    Stopped
```

Every one of those transitions requires an `approvals` row to exist first. There is no path from
`Awaiting CEO Decision` that does not record who decided what.

SIP-184 §12 names the four decisions and records `distribution authorised Yes/No` alongside them,
but does not say which run state each decision produces. The routing above reads `Continue` as
continue to distribution and `Continue With Correction` as return for correction then re-review,
consistent with §11's "block release on any Critical" and §13's "manual distribution only if CEO
approved". `[[Confirm with Sunil that Continue means distribution authorised rather than continue
the run without distributing — the SOP records the two as separate fields, so it is possible to
Continue with distribution set to No.]]`

### 3. `Approved for Manual Distribution` means authorised, not what it is authorised for

The state records that distribution has been authorised at some scope. The scope itself is
`approvals.distribution`. A UI showing "approved" without reading that column is showing an
incomplete fact, and an endpoint that authorises distribution without writing it is failing closed
by accident rather than by design.

Keeping the existing state name avoids a migration and a rename across three files for no
behavioural gain.

### 4. Report approval gates; item approval is editorial

`approvals.approval` is the release gate. `daily_intelligence.approval` records whether an
individual item was accepted into the brief.

**A report version cannot move to `Approved` while any item it contains is `Pending`.** Enforced
server-side, in the approve endpoint. Rejected and Superseded items are allowed — they are decided,
just not included.

### 5. Drop `runs.qa_status`

The QA outcome is `run_state` (`QA In Progress` / `QA Failed`) plus the SIP-188 record written by
`POST /api/reports/:id/qa`. A third free-text field cannot be reconciled with either and is the
kind of column that drifts silently.

### 6. Remove `PATCH /api/candidates/:id`

The explicit commands already exist. Every candidate mutation goes through one that names its
intent, so the audit row records the action rather than a column diff. This is the second half of
issue #114 and the whole of issue #121.

Adding a command is cheap; the rule is that a command names a thing an analyst actually does.

## Consequences

**Positive.** The decision screen has one source per fact. Roshan's #120 and #121 have a contract
to build against instead of inventing one. The audit requirement becomes satisfiable: every
state change traces to a named command and, where a human ruled, to an `approvals` row.
Separation of duties gets a place to attach, because approval is a record rather than a state.

**Negative, and the mitigations.**

- Two enum values are removed, which needs a migration and a code change in `RunState`. Mitigation:
  neither value has a defined exit today, so nothing legal can currently be in them. The migration
  is expand-then-contract per ADR-0004.
- `runs.qa_status` is dropped, which is a destructive migration, and it **is** currently consumed:
  `apps/sip/pipeline/models.py:95` carries `qa_status: str | None = None`. Mitigation: expand-then-contract.
  Remove the model field and any reader first, leave the column nullable and unwritten for one
  release, then drop it. Do not drop the column and the field in the same change.
- Deriving a combined view costs a join the UI did not previously need. Mitigation: `GET /api/dashboard`
  already exists to serve exactly that composite.
- More endpoints than a single PATCH. Mitigation: that is the point; the count is the audit trail.

**Open, and deliberately not decided here.** Whether `Internal Approved` / `Member Approved` /
`Public Approved` are ordered levels or independent grants. Note the schema is richer than the SOP
asks for: SIP-184 §12 records distribution authority as `Yes/No`, and §13 sends manually to a
single recipient. So the three-scope enum is currently unused headroom, not a live requirement.
It does not block anything, and guessing a rule now would put an invented one in the schema.

## References
- Issue #114 — the disagreement this resolves; #121 implements the command split
- [ADR-0004](0004-platform-graduation.md) — hosted backend, migration and rollback approach
- `schemas/state-machine.md` — the transitions amended by decision 2
- `schemas/api-contract.md` — the endpoint list amended by decision 6
- `database/schema.sql` — `run_state`, `approval_state`, `distribution_state`, `approvals`
- `apps/sip/pipeline/models.py` — `RunState`
- `docs/sip/launch/SIP-184_daily_run_SOP_v0.9.md` — §12 records the CEO decision and the separate
  distribution authority this ADR follows; §11 QA, §13 manual distribution
