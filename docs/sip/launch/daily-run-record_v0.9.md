# Daily Run Record (v0.9 Review Draft)

Copy this per run day. It is the append-only evidence spine (run authority, coverage, decision,
manual send, audit). Combines the operational fields of SIP-187 with the approval/distribution
and exception records. The Intelligence Database v1.9 remains the authoritative Action Register;
this record links to it, it does not replace it.

## Run authority
- Run ID: `RUN-YYYYMMDD-01`
- Date (27-31 Jul 2026): ____  | Run type: Controlled Launch
- Operator/Analyst: ____  | Reviewer: ____ (must differ from analyst)
- Launch authority: SIP-191 v1.0 active — Yes/No
- Version set confirmed: Yes/No  | Uncontrolled change detected: Yes/No (Yes = Critical stop)

## Coverage window
- Start: ____ 07:00  End: ____ 07:00  TZ: Pacific/Auckland  (inclusive start / exclusive end)

## Source coverage summary
- Mandatory sources scanned: __ / __  | Inaccessible: __ (fallbacks recorded: Yes/No)
- Any mandatory source without outcome: Yes/No (Yes = Critical stop)

## Run state (see state model)
Draft -> Run Authorised -> Coverage Locked -> Scanning -> Candidate Review -> Report Drafted ->
QA In Progress -> (QA Failed?) -> Awaiting CEO Decision -> [Continue | Continue w/ Correction |
Paused | Stopped] -> Approved for Manual Distribution -> Distributed -> Closed
- Current state: ____

## QA
- SIP-188 completed: Yes/No  | Result: Pass/Fail  | Reviewer: ____  | Critical failures: ____

## CEO decision (required daily)
- Decision: Continue / Continue with Correction / Pause / Stop
- Reason: ____  | Conditions: ____  | Next review: ____
- Distribution authorised: Yes/No  | Authorised report version: ____  | Timestamp: ____
- Approval never inferred from silence or a prior day.

## Manual distribution (only if authorised)
- Sent to: sunilkaushalnz@gmail.com  | File version: ____
- Sender: ____  | Channel: ____  | Sent time: ____  | Delivery result: ____

## Exceptions (SIP-189)
- Exception ID: ____  | Type: ____  | Severity: ____  | Owner: ____  | Status: ____
- Original report preserved: Yes/No  | Linked correction/withdrawal: ____

## Close-out
- Evidence pack complete: Yes/No  | DB routing done: Yes/No  | Tracker reconciled: Yes/No
- DB vs tracker contradiction: Yes/No (Yes = Critical stop)
- Next-day carry-forward recorded: Yes/No  | Final status: ____

## Audit (append-only; one line per controlled action)
| Timestamp | User | Action | Old -> New | Record ID | Version | Reason | Approval ref |
|-----------|------|--------|-----------|-----------|---------|--------|--------------|
