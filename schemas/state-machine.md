# SIP run state machine — v0.1 draft

The allowed run states and transitions. Enforced server-side; invalid transitions are rejected.
Matches the `run_state` enum in `database/schema.sql` and the SIP spec.

## States
`Draft → Run Authorised → Coverage Locked → Scanning → Candidate Review → Report Drafted →
QA In Progress → Awaiting CEO Decision → Approved for Manual Distribution → Distributed → Closed`

Branches: `QA In Progress → QA Failed` · `Awaiting CEO Decision → {Continue | Continue With
Correction | Paused | Stopped}` · post-close: `Corrected`, `Withdrawn`.

## Allowed transitions
```
Draft                         -> Run Authorised            (launch authority + version check pass)
Run Authorised                -> Coverage Locked           (exact 24h window fixed)
Coverage Locked               -> Scanning
Scanning                      -> Candidate Review
Candidate Review              -> Report Drafted
Report Drafted                -> QA In Progress
QA In Progress                -> Awaiting CEO Decision      (QA pass)
QA In Progress                -> QA Failed                  (any Critical failure)
QA Failed                     -> Report Drafted             (after correction + re-review only)
Awaiting CEO Decision         -> Approved for Manual Distribution  (explicit decision, distribution authorised)
Awaiting CEO Decision         -> Continue / Continue With Correction / Paused / Stopped
Approved for Manual Distribution -> Distributed             (manual send recorded)
Distributed                   -> Closed
Paused                        -> Coverage Locked            (recorded resumption approval only)
```

## Illegal transitions (rejected)
- `Draft -> Distributed` (no skipping gates).
- `QA Failed -> Approved for Manual Distribution` (must correct + re-review).
- `Awaiting CEO Decision -> Distributed` (needs an explicit recorded decision).
- `Paused -> *` without a recorded resumption approval.
- `Stopped -> *` under the same run ID (a stop is terminal for that run).

## Fail-closed
Any Critical condition forces the run to `QA Failed` or `Stopped`, never a silent continue.
Distribution requires `production_enabled=true`-equivalent authority for automated modes, which
stay disabled during the controlled launch.
