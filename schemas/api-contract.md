# SIP API contract — v0.1 draft

The interface Roshan (pipeline, writes) and Paras (UI, reads) build against. REST, JSON. Every
write requires authentication, role permission, validation, and an audit-log entry. The
Intelligence Database is the single Action Register — no endpoint creates a competing one.

Auth: an opaque server-side session in a `HttpOnly`, `Secure`, `SameSite=Lax`, host-only cookie,
with a double-submit CSRF token on every state-changing request (ADR-0004). Not a bearer token: the
staff surface is same-origin precisely so a token never has to live anywhere a script can read it.

Roles come from `user_roles`, not `users.role_id`, which ADR-0005 removed: one principal may hold
several roles, because the steady state after the placement is one person holding every one of
them.

Separation of duties is enforced server-side and binds to the **role held at the time of the act**,
not to a person. `runs.analyst_id <> runs.reviewer_id` is a database constraint and still holds.
Where one principal necessarily holds both sides, the decision still commits, but only against a
recorded `sod_exceptions` row naming the approver, the reason and a review date. An unrecorded
self-approval is refused.

**Two halves, and only one of them is enforced today.** Saying otherwise would overstate the
control, which is worse than the gap.

*Enforced:* authorship. `DecisionRepository.record` reads `report_versions.created_by`,
canonicalises both identities so a differently-spelled UUID cannot slip past, and refuses when the
decider created the version being decided on. Candidate acts are checked the same way, against
`captured_by` and `assessed_by` rather than against role membership.

*Not enforced:* the role pairs. `decision_sod_role_pairs` is designed as configuration, so a
staffing change would be a data change, but **nothing consults the table**. It is deliberately
unseeded pending client answers B8, and enforcing an empty rule set would refuse every decision. So
a conflict expressed as a role pair rather than as authorship is not currently caught, and will not
be until the table is both seeded and read. ADR-0005 required follow-up 4.

## Pipeline (Roshan) — data in
```
POST   /api/runs                     create a run (fixes the 24h coverage window)
GET    /api/runs        /api/runs/:id
POST   /api/runs/:id/start | /pause | /resume | /complete
GET    /api/runs/:id/source-checks
POST   /api/runs/:id/source-checks   record a per-source outcome (mandatory sources must have one)
GET    /api/source-library           list source_library rows (id, sip185_code, name). sip185_code is authoritative for source-check resolution; name is display/candidate-capture only and is NOT unique, so never resolve a source-check by name
GET    /api/candidates?run=:id
POST   /api/candidates               capture a candidate (all scoring/verification fields)
PATCH  /api/candidates/:id
POST   /api/candidates/:id/verify | /score | /route | /merge
```

## Registers (#209 — API is Roshan's, `docs/sip/build-plan.md`'s "Registers UI" is Paras's)
```
POST   /api/action-register              record an action; a named owner (owner_id or owner_text)
POST   /api/action-register/:id/status   Open / Closed / Controlled Monitoring; closed_at set only on Closed
GET    /api/action-register  /api/action-register/:id
POST   /api/watch-lists                  Opportunity/Threat/ongoing watch, distinguished by category
POST   /api/watch-lists/:id/status
GET    /api/watch-lists  /api/watch-lists/:id
POST   /api/exceptions                   append-only: never updated in place
POST   /api/exceptions/:id/correct       inserts a new row, correction_ref = the id it corrects
GET    /api/exceptions  /api/exceptions/:id
```
## Approved facts library (#188 — Roshan's)
```
POST   /api/facts                        draft a fact; a named owner (owner_id or owner_text)
POST   /api/facts/:id/approve            Reviewer/SIP Owner only; refuses self-approval
POST   /api/facts/:id/archive            retires a fact; any writer role
GET    /api/facts/:id
GET    /api/facts/by-key/:fact_key/latest    latest *approved* revision, 404 if none approved yet
GET    /api/facts/by-key/:fact_key/history   every revision, newest version first
```
Drafting a new version of an existing fact passes `supersedes_id`; the prior row is never edited,
only chained.

## Control (Paras) — data out + human gates
```
POST   /api/reports                  submit a report version for a run  [BUILT]
GET    /api/reports/:id              the version plus every current decision on it  [BUILT]
POST   /api/reports/daily            build the SIP-186 brief from selected candidates
POST   /api/reports/:id/qa           record SIP-188 QA result (blocks release on Critical)
POST   /api/reports/:id/submit
POST   /api/reports/:id/approval     report-approval stream: Approved | Rejected |
                                     Returned for Correction (the three approval_state values
                                     the schema stores; two endpoints could not express Rejected)
POST   /api/reports/:id/ruling       CEO ruling only: Continue | Continue With Correction | Pause | Stop
POST   /api/reports/:id/distribution distribution authority only: Authorised | Not Authorised
POST   /api/reports/:id/delivery     records an actual send against a current Authorised decision
GET    /api/registers/:name          action | watch | opportunities | threats | exceptions
POST   /api/registers/:name
GET    /api/dashboard                control state, open actions, QA/distribution status  [BUILT]
```

**`GET /api/dashboard` shape**, built for #47:

```json
{
  "run": { "id": "...", "run_number": "RUN-20260813-01", "state": "Candidate Review",
           "version": 3, "prompt_version": "...", "coverage_start_utc": "...",
           "coverage_end_utc": "...", "initiated_by": "..." },
  "gates": { "qa_status": "Passed", "report_approval": "Approved",
             "distribution_authority": "Authorised", "distribution_recipient": "..." },
  "coverage": { "total": 7, "included": 2,
                "by_verification": { "Verified": 5, "Partially Verified": 0,
                                     "Unverified": 2, "Not Required": 0, "Rejected": 0 } },
  "open_actions": [ { "action_code": "ACT-016", "title": "...", "owner": "Executive Sponsor",
                      "priority": "High", "due_date": "2026-08-01", "status": "Open",
                      "overdue": true } ],
  "open_actions_truncated": false
}
```

Three guarantees the UI may rely on, each of which is a rule the client would otherwise own:

**`by_verification` always carries every verification state**, including the ones at zero. A state
absent from the map would force the caller to know the full enum to render the panel.

**`run` is `null` when no run exists, and the status is still 200.** "No run yet" is a state the
dashboard renders, not an error, and the open-actions panel is worth showing regardless.

**`overdue` is computed by the database**, so a client with a wrong clock cannot make a late action
look on time. Actions are ordered overdue first, then by due date with nulls last.

**Every `gates` field is nullable, and null means "not reached yet" rather than "unknown".**
`qa_status` comes from the run; `report_approval` and `distribution_authority` come from the run's
newest report version, because ADR-0005 keys those decision streams to a report version, so they
stay null until one exists.

**Open actions are capped at 200, and `open_actions_truncated` says when the cap bit.**
`action_register` has no retention rule, so nothing in the schema stops it growing. A silently cut
list would read as "these are all the open actions", which is wrong for a screen used to decide
what to work on.

`extra="forbid"` on every model in the response, so a field added server-side cannot reach the UI
unannounced.

**What is built, and what the decision-writing endpoints are waiting on.**

`POST /api/reports` and `GET /api/reports/:id` are mounted. Submitting a version is what makes a
report decidable: a trigger opens the CEO Ruling, Report Approval and Distribution Authority
streams on insert, so a decision can never arrive for a stream nobody created, and there is no
separate call to forget. The version number is assigned by the database, because a caller-supplied
number is a second opinion about the sequence and the one that disagreed would win.

The read returns the version **and** its current decisions **and** the revision each was read at,
in one response. A reviewer cannot act on a version without knowing what has already been decided,
and a caller recording a decision has to pass back the revision it read. Two calls would let a
decision commit in between, which is the race `DecisionRepository.current` closes in a single
statement, so splitting them over HTTP would reopen it one layer up.

`/approval`, `/ruling` and `/distribution` are **specified and deliberately not mounted**.
`decision_role_permissions` is unseeded, and no row means nobody may act, so the repository refuses
every decision by design. Mounting them now would ship three endpoints that answer 403 until INZBC
decides who may approve what. That is a client decision (ADR-0005 required follow-up 4, client
answers B8), not an engineering one, and an endpoint that looks built is worse than one that is
honestly absent.

**Why ruling and distribution are separate commands.** REQ-U-02 requires distribution authority to
be captured as a separate action, and ADR-0005 records the three facts as independent immutable
decision streams, each with its own actor and timestamp. One endpoint writing two fields cannot
satisfy that: a single submission is one action however many rows it writes. `/decision` is gone;
do not reintroduce it.

**Distribution "No" does not stop the run.** An explicit `Not Authorised` is a valid outcome, not a
refusal to proceed: the send is skipped and the run reaches close-out as approved but not
distributed (`docs/sip/operator-guide.md`). Absence of a decision and an explicit `Not Authorised`
are different states and must stay distinguishable.

**Recipient revalidation needs a configuration version, which the schema does not have yet.**
`distribution_configuration` is a mutable singleton that nothing references, so the database cannot
show whether the configured recipient changed between authorisation and send. Comparing the
authority record's recipient against the singleton's *current* value is possible today; proving it
has not moved since is not. Before `/delivery` can enforce the rule below, the configuration needs
an immutable version that both the authority decision and the delivery record cite. Recorded as
required follow-up rather than pretended.

**`/delivery` is execution evidence, not authority.** It records sender, recipient, channel, sent
time and result against the authority that permitted it. The authority check, the delivery record,
the audit row and any state transition commit in one transaction. The recipient is revalidated at
send time, not only at authorisation: if the configured recipient changed since, the authority is
stale and a fresh distribution decision is required.

**Release predicate for `Authorised`.** Current report approval is `Approved`, current ruling is
`Continue`, no open Critical QA failure, and the recipient matches the configured one. These span
rows and tables, so they are enforced by the command inside its transaction, not by a database
CHECK. `Continue With Correction` does not permit release; it requires a corrected report version,
fresh approval and fresh authority.

## Cross-cutting
```
GET    /api/audit                    append-only audit log (read)
GET    /api/config                   server-side control flags (read)
```

## Rules every write endpoint enforces
- Fail-closed: a Critical condition (missing run authority, unapproved version, missing mandatory
  source outcome, unverified Critical claim, tracker/DB contradiction, missing approval,
  unauthorised distribution) returns an error, never a warning.
- Server-side flags stay false unless a controlled approval record exists:
  `production_enabled`, automated/member/external/website/social distribution.
- No secrets in requests, responses, or logs.

Full OpenAPI spec lands here as the app is built. This draft freezes the endpoint shapes so
pipeline and UI can start in parallel.
