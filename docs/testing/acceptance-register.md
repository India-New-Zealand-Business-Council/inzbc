# Acceptance register (#210)

One row per acceptance criterion in `docs/testing/master-test-plan.md`, tracked as it moves from
"criterion exists" to "exercised" to "signed". Empty until INZBC actually runs UAT — this is the
register the sessions get logged against, not a record of anything that has happened yet.

**Do not backfill a row from assumption.** A criterion is `Not run` until someone with authority
to judge it actually ran it and recorded the result — the same rule the SIP register itself
follows for source-check outcomes: blank is the only acceptable state for something nobody
checked.

## Status legend

| Status | Meaning |
|---|---|
| `Not run` | No UAT session has exercised this yet |
| `Blocked` | Cannot be run — see the blocker in the Notes column |
| `Pass` | INZBC exercised it and it met the criterion |
| `Fail` | INZBC exercised it and it did not — corrective action owed before re-test |

## SIP

| # | Criterion | Status | Evidence | Signed by | Date | Notes |
|---|---|---|---|---|---|---|
| S1 | Full SIP-184 run completes end to end | `Blocked` | — | — | — | Needs a fresh SIP-191 window |
| S2 | Every mandatory source has a recorded outcome | `Blocked` | — | — | — | Same window blocker |
| S3 | Separation of duties holds with real distinct people | `Blocked` | — | — | — | Needs named SIP staff (docs/client-answers-relayed-2026-08-09.md) |
| S4 | QA reviewer independently blocks a Critical-defect run | `Blocked` | — | — | — | Same staffing blocker |
| S5 | `production_enabled` stays false pre-closeout | `Not run` | — | — | — | Can be checked now — code-level, not staffing-dependent |
| S6 | Run audit trail complete and Auditor-readable | `Blocked` | — | — | — | Needs a real run to audit |
| S7 | No automated distribution occurs | `Not run` | — | — | — | Can be checked now — gate is code-level and tested (`test_distribution_gate.py`) |

## FTA Implementation Centre

| # | Criterion | Status | Evidence | Signed by | Date | Notes |
|---|---|---|---|---|---|---|
| F1 | Confirmed-match query returns a sourced answer | `Not run` | — | — | — | Nothing blocks scheduling this |
| F2 | No-match query escalates, never guesses | `Not run` | — | — | — | |
| F3 | No answer exceeds Tier-1 sourcing | `Not run` | — | — | — | |
| F4 | Usable at 320px | `Not run` | — | — | — | Playwright coverage exists (#100); INZBC's own device/browser check is separate |

## AI Communications Assistant

| # | Criterion | Status | Evidence | Signed by | Date | Notes |
|---|---|---|---|---|---|---|
| C1 | No automatic distribution of a draft | `Not run` | — | — | — | |
| C2 | Author cannot approve their own draft | `Not run` | — | — | — | |
| C3 | Create/approve are both audited | `Not run` | — | — | — | |
| C4 | Reviewer UI workflow end to end | `Blocked` | — | — | — | #60 not built |
| C5 | Free-text brief prohibited-data handling | `Blocked` | — | — | — | #303 open, no structural control yet |

## Phase 1 gate (separate from the criteria above)

| Signatory role | Named? | Source |
|---|---|---|
| Executive Sponsor | Referred to generically as "the Executive Sponsor" in prior approvals (e.g. the redaction policy, 9 Aug) — not confirmed by name in any doc reviewed for this register | — |
| Technical Lead | Bhanu (`docs/inzbc-ai-operating-system.md` §"Bhanu: Technical lead...") | Named |
| Finance Owner | Not named | `docs/client-answers-relayed-2026-08-09.md` item 11 |
| Privacy Owner | Not named | `docs/client-answers-relayed-2026-08-09.md` item 11 |

The gate cannot be signed with two of four signatories unnamed, independent of how many rows
above read `Pass`.
