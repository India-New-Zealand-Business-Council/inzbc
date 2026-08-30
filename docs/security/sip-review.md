# SIP adversarial security review

`docs/sip/README.md` requires an adversarial security review before any staff use. This is that
review: what was examined, what it found, what was fixed, and what is still open.

**Status: review complete, sign-off outstanding.** The Executive Sponsor signs off before
staff-facing use. Nothing here is that signature.

**Scope.** The SIP pipeline and control plane: the run state machine, candidate lifecycle,
decision records, the model gateway, and the authentication and authorisation that sit in front of
all of it. The public FTA read path is out of scope — it holds no personal data, takes no writes
and carries no session.

The design this reviews against is [`README.md`](./README.md). The threat model and abuse cases
are in [`../raci.md`](../raci.md#threat-model). This document is the review, not a restatement of
either.

---

## 1. How the review was run

Repeated adversarial passes against each security-touching change, plus attacks executed against
the running code rather than read off the diff. Reviews ran both before and after merge; the ones
that ran after merge found live defects, which is the argument for running them before.

**Every review returned findings, and every finding named below was reproduced by execution before
it was fixed.** Nothing here is a theoretical concern that was tidied away.

The honest summary of the method: reading the diff found almost nothing. Running the attack found
everything.

## 2. Findings

Each row is a defect that existed in merged code, with the property it broke.

| # | Finding | Why it mattered | Closed by |
|---|---|---|---|
| 1 | `require_roles` was written, tested and **wired to no route** | Every authenticated caller could do everything regardless of role. Authentication without authorisation | #278 |
| 2 | `canonical_actor` was written, tested and **not used** by `decisions.py` | An uppercase or unhyphenated UUID compared unequal to itself, so self-approval passed the check | #280 |
| 3 | `sod_exception_id` was **stored and never checked** | An exception field that authorised nothing, while reading as though it did | #280 |
| 4 | Separation of duties was checked against **role membership** | Role checks are an OR over roles held, so one person holding Analyst and Reviewer passes both gates and satisfies the control alone | #284 |
| 5 | `_get_locked` did not lock | The name promised `FOR UPDATE`; the SQL was a plain `SELECT`, and three comments cited a lock never taken | #285 |
| 6 | The verification gate ran at scoring, **not at inclusion** | `record_routing` could set `included = true` unguarded, which is the decision that actually reaches a reader | #285 |
| 7 | Two run stops were **specified and never mounted** | The reviewer's independent QA stop and the CEO's terminal stop had no route, so the only refusals in the state machine could not be exercised | #285 |
| 8 | A gated transition accepted **any non-empty string** as authority | Launch and resumption authority had nowhere to be recorded, so the two gates deciding whether a run may run at all took free text | #227 / #301 |
| 9 | `captured_by` was nullable, and the check tested `is not None` | Whoever captured a candidate could verify it by omitting one column on insert | #297 / #300 |
| 10 | Boundary refusal did not exist; redaction was described as the control | Regex cannot catch a name, job title or employer in prose, and review after the fact cannot undo a disclosure | #223 / #300 |
| 11 | `PromptSource` subclasses `str`, so a **bare string** satisfied the closed set | `"public_source" in PERMITTED_SOURCES` is `True` by string equality; a prohibited bare string crashed with `AttributeError` instead of refusing | #300 |
| 12 | `minimise()` filtered **one level deep** | Allowlisting a key kept its whole subtree, so the promise that an unnamed field cannot reach a prompt was false | #300 |
| 13 | The nested check was a **denylist** of four container types | Pydantic models, dataclasses, `bytes` and `frozenset` passed through carrying a name | #300 |
| 14 | The scalar allowlist used `isinstance`, which admits subclasses | A `str`-based enum passed as a string, which is finding 11 by another route | #300 |
| 15 | `candidate_sod_exceptions` had a row trigger and **no whole-table guard** | One statement could clear the exceptions evidencing single-operator work | #298 |
| 16 | Session cleanup was **rolled back by its own raise** | Every expiry path refused the call and left the row in place, so a re-activated account revived its old session | #272 |
| 17 | Rehydration **fabricated** a decision for a gated transition with no recorded authority | Replay waved through exactly the history that proves something went wrong | #116 / #305 |
| 18 | Rehydration accepted an **unknown run id** | A typo replayed to an empty history and returned a valid Draft run | #305 |

## 3. What the findings have in common

Three patterns account for nearly all of them, and they are worth more than the individual fixes.

**A control that was built, tested in isolation, and never connected.** Findings 1, 2, 3 and 7.
The unit test passed because the function worked; nothing asserted the function was *reached*. This
is why every control now ships with a conformance test that enumerates the real application and
asserts the wiring — `test_router_auth.py` walks the mounted routes and asserts each one's exact
role set, and it is what caught the audit endpoint's missing declaration during development rather
than after merge.

**A list written by hand, in a test, that silently stopped covering everything.** Finding 15, and
the route matrix before it. A test that names its subjects passes when someone adds a subject it
does not know about, so the one table missing its guard was the one the test had never heard of.
Conformance lists are now derived from the artifact: the append-only guard test reads the table
names out of `schema.sql`.

**A denylist, or an allowlist that was not closed.** Findings 11, 13 and 14. The failure mode of
forgetting an entry in a denylist is disclosure; in an allowlist it is refusal. Where an allowlist
was used, `isinstance` re-opened it, because subclassing is a way in that nobody enumerated.
Membership is now tested by exact type.

**The residual risk this leaves.** These three patterns are the ones that were *found*. A control
that is unwired, a list that has stopped covering, and a set that is not closed all read as correct
in review, which is precisely why they survived. The countermeasure is not vigilance; it is that
each class now has a test that fails structurally rather than by someone remembering.

## 4. Authorisation matrix

In [`README.md`](./README.md) §3, and asserted in `test_router_auth.py` rather than only written
down. Summary of the separation the matrix encodes:

- **Analyst** captures, scores, routes and merges; creates and completes runs.
- **Reviewer** verifies candidates, and can stop a run independently of the owner.
- **SIP Owner** launches, pauses, resumes and stops; approves release.
- **Secretariat** drafts comms.
- **Administrator, Board Viewer, Auditor** read.

Two rows are deliberate and would be wrong if simplified. `fail-qa` includes Reviewer, because a
quality gate only the owner can pull is not independent of the owner. Reads are open to all seven
roles, because withholding the record from an auditor defeats the purpose of keeping it.

## 5. Audit coverage

**No write path bypasses the audit log, and this is enforced structurally.**
`test_audit_coverage.py` walks the AST of every write function in `services/api` and fails if one
commits without a `record_audit` call in the same transaction. It also asserts `record_audit` never
commits on its own, which is what makes the audit row atomic with the mutation rather than merely
adjacent to it.

Immutability is a database property, not an application convention: an INSERT/SELECT-only
application role, plus triggers that block UPDATE, DELETE and whole-table clears on every evidence
table. `verify_restore.py` checks in CI that those triggers survive a restore and, more
importantly, that they still *fire* — a trigger restored without its function is present in
`pg_trigger` and does nothing.

**Two coverage gaps, both stated rather than closed.**

Session establishment and sign-out write no audit row. `users.last_login_at` is overwritten each
time, so "who was signed in when this happened" is not fully answerable. Every *action* is
attributed; the sessions around them are not.

`audit_log.reason` is unbounded operator text in an append-only table, so a name typed into it
cannot be removed. The operator guide says reasons state what and why, not who beyond the actor
already recorded.

## 6. Open items, with owners

| Item | Owner | Note |
|---|---|---|
| Sign-off on this review before staff use | Executive Sponsor | The remaining acceptance criterion. Everything else here is delivered |
| Comms brief is free prose, so refusal cannot bound it (#303) | Technical Lead | The one path reaching a model with staff-typed text. Bounded by procedure today, which is what this control existed to replace |
| `minimise()` has no production caller | Technical Lead | The mechanism exists; no module handles member records yet |
| A hollowed-out prompt is sent rather than refused | Executive Sponsor | ADR-0006 §5. The threshold is a judgement about output quality, not an engineering constant |
| Session establishment and sign-out unaudited | Technical Lead | §5 above |
| MFA on owned accounts unverified | Executive Sponsor | Five-minute check nobody outside INZBC can perform |
| Backup never restored from a production backup | Technical Lead | The checker runs in CI; there is no production database yet (#99) |
| ~~No migration mechanism (#44)~~ | Technical Lead | **Closed 20 Aug 2026.** `scripts/migrate.py` plus `database/migrations/`; a schema-level control can now reach an existing database instead of binding new ones only |

## 7. Conclusion

**The controls the SIP non-negotiables require are built and enforced**, and each is held by a test
that fails structurally rather than by convention: server-side model calls, redaction before every
call with refusal when unconfigured, human gates that cannot be crossed without a recorded and
verified authority, separation of duties checked against recorded acts, and an append-only audit
trail immutable in the database.

**Two qualifications belong on the same page as that sentence.** The Comms brief remains bounded by
procedure rather than by a boundary, and it is the only path where staff-typed prose reaches a
model. And this review reflects the system as at the date it was written; the reason it found
eighteen defects is that adversarial review works, which is an argument for running it again on the
next security-touching change rather than treating this document as a certificate.

**Recommended for staff use** once the Executive Sponsor signs off and #303 is either closed or
accepted in writing as a known limitation.
