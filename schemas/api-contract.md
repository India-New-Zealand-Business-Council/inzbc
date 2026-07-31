# SIP API contract — v0.1 draft

The interface Roshan (pipeline, writes) and Paras (UI, reads) build against. REST, JSON. Every
write requires authentication, role permission, validation, and an audit-log entry. The
Intelligence Database is the single Action Register — no endpoint creates a competing one.

Auth: bearer token. Roles come from `user_roles`, not `users.role_id`, which ADR-0005 removed:
one principal may hold several roles, because the steady state after the placement is one person
holding every one of them.

Separation of duties is enforced server-side and binds to the **role held at the time of the act**,
not to a person. The required-distinct pairs are configuration (`decision_sod_role_pairs`), so a
staffing change is a data change. `runs.analyst_id <> runs.reviewer_id` is a database constraint and
still holds. Where one principal necessarily holds both sides of a required-distinct pair, the
decision still commits, but only against a recorded `sod_exceptions` row naming the approver, the
reason and a review date. An unrecorded self-approval is refused.

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

## Control (Paras) — data out + human gates
```
POST   /api/reports/daily            build the SIP-186 brief from selected candidates
GET    /api/reports/:id
POST   /api/reports/:id/qa           record SIP-188 QA result (blocks release on Critical)
POST   /api/reports/:id/submit
POST   /api/reports/:id/approve | /request-changes   report-approval stream
POST   /api/reports/:id/ruling       CEO ruling only: Continue | Continue With Correction | Pause | Stop
POST   /api/reports/:id/distribution distribution authority only: Authorised | Not Authorised
POST   /api/reports/:id/delivery     records an actual send against a current Authorised decision
GET    /api/registers/:name          action | watch | opportunities | threats | exceptions
POST   /api/registers/:name
GET    /api/dashboard                control state, open actions, QA/distribution status
```

**Why ruling and distribution are separate commands.** REQ-U-02 requires distribution authority to
be captured as a separate action, and ADR-0005 records the three facts as independent immutable
decision streams, each with its own actor and timestamp. One endpoint writing two fields cannot
satisfy that: a single submission is one action however many rows it writes. `/decision` is gone;
do not reintroduce it.

**Distribution "No" does not stop the run.** An explicit `Not Authorised` is a valid outcome, not a
refusal to proceed: the send is skipped and the run reaches close-out as approved but not
distributed (`docs/sip/operator-guide.md`). Absence of a decision and an explicit `Not Authorised`
are different states and must stay distinguishable.

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
