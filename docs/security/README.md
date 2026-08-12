# Security design

The design the adversarial review (#40) checks against, and what a future maintainer needs in
order to change any of it safely.

**One honest note about this document.** Issue #112 asked for it *before* the auth code existed.
It was written after, so it records what was built rather than what was planned. That ordering was
a mistake and it cost something real: `require_roles` was written, unit-tested and left unwired to
any route for the whole of #42, so for a period every authenticated caller could do everything
regardless of role. A design document would not have caught that on its own — the conformance test
in §3 is what catches it — but writing the matrix down first is how you notice you never applied
it.

The threat model and abuse cases live in [`../raci.md`](../raci.md#threat-model), with the rest of
the governance set. Everything below is the design that answers it. The review itself, with the
eighteen findings it produced and what they had in common, is
[`sip-review.md`](./sip-review.md).

---

## 1. Authentication architecture

**GitHub authenticates; it never authorises.** That sentence is the whole design.

A successful GitHub sign-in proves someone controls a GitHub account. It says nothing about
whether that person may use this system. So the login is matched against `users.github_login`, and
no row — or `active = false` — means refusal with no session issued.

```
GitHub OAuth  ──►  verified github_login  ──►  users allowlist  ──►  session  ──►  user_roles
   (who you are)                                (may you be here)     (opaque)      (what you may do)
```

Four properties worth understanding, because each one is load-bearing.

**Logins are matched case-insensitively.** GitHub treats `Alice` and `alice` as one account.
Matching the raw string would let provisioning create two rows for the same person, with different
roles, and which one you got would depend on how you typed it.

**"No such user" and "inactive user" return the same error.** Distinguishing them would tell an
unauthenticated caller whether a given GitHub login is registered here, which is an account
enumeration oracle for free.

**Roles are data, not deployment.** They come from `user_roles`, so changing who holds a role is a
database change rather than a release.

**`resolve()` re-reads `users.active` and `user_roles` on every single request**, rather than
trusting what was true when the session was issued. This is what makes offboarding immediate:
setting `active = false` takes effect on the next call, with no session cleanup and no deploy. It
costs a query per request and it is worth it — the alternative is a window between "we revoked
their access" and "their access stopped working", and that window is exactly when it matters.

**What is not built yet.** The OAuth handshake itself. `establish_session` takes an
already-verified GitHub login, so the exchange can be added without touching any authorisation
rule. Until then sessions are issued out of band by `scripts/dev_session.py`, which needs database
access and cannot be reached over the network.

There is deliberately **no sign-in route** in the mounted API. An earlier version had
`POST /api/session` accept a `github_login` behind an environment flag. That is account
impersonation one config line away: anyone who copied the flag into a deployed environment would
let an attacker post an allowlisted approver's public GitHub username and receive that person's
session. A gate whose failure mode is "become the CEO" does not belong in a mounted router.

## 2. Session and CSRF design

Opaque server-side sessions, not JWTs. The reason is revocation: a JWT is valid until it expires
because the server does not consult anything to accept it, and the whole point of §1 is that the
server re-checks on every request. Deleting a row is the entire sign-out mechanism.

| Property | Value | Why |
|---|---|---|
| Token | 32 random bytes from `secrets` | Not derived from user id or timestamp — nothing guessable |
| Stored as | SHA-256 digest, never the token | A database snapshot or backup would otherwise hand over live sessions |
| Cookie | `HttpOnly`, `Secure`, `SameSite=Lax`, host-only | Not readable by script, does not cross an origin |
| Absolute lifetime | 12 hours | ADR-0004 |
| Idle timeout | 60 minutes | ADR-0004; whichever expires first wins |
| CSRF | Double-submit token in `X-CSRF-Token` | See below |

**Why the digest and not the token.** If `sessions.id` held the cookie value, anyone with read
access to the table — a backup, a snapshot, a support query — could copy it, send it as the
cookie, call `GET /api/session` for the CSRF token, and act as that user until expiry. Storing
only the digest makes a leaked table useless for replay.

Plain SHA-256 with no salt is correct here, unlike for passwords. The input is 32 random bytes, so
there is no dictionary to attack and nothing a per-row salt would defend against.

**Why CSRF protection on top of `SameSite=Lax`.** Lax still permits a top-level cross-site POST
navigation, which is precisely the shape of a form-submission CSRF. An attacker who can make the
browser send the cookie still cannot supply the header, because reading the token requires a
same-origin `GET /api/session`. The comparison uses `compare_digest` — the timing leak is not
credibly exploitable behind a database round trip, but a constant-time compare on a secret costs
nothing and removes the question.

**Sign-out is deliberately not behind the CSRF check.** A forged sign-out is a nuisance; refusing
to sign someone out because a token was missing is the worse failure.

**A fixed bug worth recording**, because it is the kind that hides. When a session failed
validation, the code deleted the row and raised. The raise propagated out of the connection
context, which rolled the transaction back and took the delete with it — so every expiry path
refused the call and left the row in place. A re-activated account would have revived its old
session. The fix is an outright `conn.commit()` before the raise; a `conn.transaction()` block
there is nested and committing it only releases a savepoint. Two separate attempts got this wrong
the same way before the third worked.

## 3. Authorisation matrix

Every mounted business route, and the roles that may call it. Read roles are
`STAFF_READ` = all seven, because reading is how a reviewer, an auditor or the board sees what the
platform did. It is still an allowlist: a user holding no role reads nothing.

| Route | Roles |
|---|---|
| `POST /api/runs` | Analyst, SIP Owner |
| `GET /api/runs`, `GET /api/runs/{id}` | all staff roles |
| `GET /api/runs/{id}/audit` | all staff roles |
| `POST /api/runs/{id}/start` | SIP Owner |
| `POST /api/runs/{id}/pause` | SIP Owner |
| `POST /api/runs/{id}/resume` | SIP Owner |
| `POST /api/runs/{id}/stop` | SIP Owner |
| `POST /api/runs/{id}/fail-qa` | **Reviewer**, SIP Owner |
| `POST /api/runs/{id}/complete` | Analyst, SIP Owner |
| `POST /api/candidates` | Analyst, SIP Owner |
| `GET /api/candidates`, `GET /api/candidates/{id}` | all staff roles |
| `POST /api/candidates/{id}/score` | Analyst, SIP Owner |
| `POST /api/candidates/{id}/route` | Analyst, SIP Owner |
| `POST /api/candidates/{id}/merge` | Analyst, SIP Owner |
| `POST /api/candidates/{id}/verify` | **Reviewer**, SIP Owner |
| `POST /api/comms/draft` | Secretariat, SIP Owner |
| `GET /api/dashboard` | all staff roles |
| `POST /api/reports` | Analyst, SIP Owner |
| `GET /api/reports/{id}` | all staff roles |
| `GET /api/source-library` | all staff roles |
| `POST /api/runs/{id}/source-checks` | Analyst, SIP Owner |
| `GET /api/runs/{id}/source-checks` | all staff roles |

Five rows are deliberate rather than obvious.

**`fail-qa` includes Reviewer, and that is the point.** REQ-U-01 gives the reviewer an independent
stop. A quality gate that only the owner can pull is not independent of the owner.

**`verify` is the reviewer's job, and role membership is not sufficient** — see §4.

**`comms/draft` is narrower than the other writes** because it spends money per call.

**`{id}/audit` is readable by every staff role**, including Auditor and Board Viewer, which exist
for precisely this. Narrowing it to the owner would mean the person most likely to be audited
controls who sees the record, and an audit trail nobody can read is not an audit trail.

**`source-checks` writes sit with the Analyst, not the Reviewer.** Recording whether a mandatory
SIP-185 source was covered for a run is the same act as capture — the analyst working the run
states what they found — so it carries the same authority as `POST /api/candidates`. Giving it to
the Reviewer instead would make the reviewer author the evidence they are supposed to verify. The
read side follows `{id}/audit`'s reasoning: coverage is exactly what an auditor checks a run
against, so restricting it to the role being audited defeats the purpose.

**How this is enforced, and how it stays enforced.** `read_access(*roles)` and
`write_access(*roles)` are dependency factories, so a route declares its authority *in its own
signature* rather than calling a check in its body. A check in the body is one a new route can
forget. A dependency is visible in the route's dependency graph — and `test_router_auth.py`
enumerates every mounted route and asserts the exact role set above. Widening a route to an extra
role fails the test, so changing who may do what requires a deliberate edit to the map as well as
to the route.

`write_access` bundles authentication, CSRF and authorisation into one declaration, because
separating them is how a route ends up with two of the three.

**Fail-closed throughout.** `require_roles` with an empty role list refuses rather than permits,
because the likeliest way that happens is a caller forgetting to name the roles. A misspelt role
name refuses everyone, which looks like a permissions bug rather than silently granting access.

**401 and 403 are kept distinct.** 401 means no session and invites a retry. 403 means the
identity is known and refused — an allowlist miss, a missing role, or a bad CSRF token — and
signing in again will not help.

## 4. Separation of duties

BR8 and ADR-0005. A control one person can execute end to end is not a control.

**The rule is enforced against recorded acts, not role membership.** This distinction is the
single most important thing in this document, and getting it wrong was a real finding rather than
a hypothetical one.

Role checks are an **OR over the roles a person holds**. So a person holding both Analyst and
Reviewer passes the Analyst gate on `capture` and the Reviewer gate on `verify` — both checks
succeed, and separation of duties has been satisfied on paper by one person doing both jobs.

The actual check asks a different question: *who is recorded as having captured and assessed this
candidate?* `candidates` carries `captured_by`, `assessed_by` and `verified_by`, and
`refuse_self_review` refuses when the principal matches the recorded author.

Two details that each closed a real bypass:

**Actor ids are canonicalised before comparison.** `A1B2…`, `a1b2…`, the unhyphenated form and a
`uuid.UUID` object are all the same principal. Comparing raw strings let an uppercase UUID slip
past the self-review check — a silent authorisation bypass rather than an error. `canonical_actor`
is shared rather than reimplemented, which is how the two call sites drifted apart in the first
place.

**Unknown authorship refuses — on the decision path.** `refuse_self_review`, used by
`decisions.py`, treats a null author as a refusal. An earlier version permitted it, reasoning that
records with no recorded author should not become unreviewable. That was fail-open: the check
cannot distinguish "nobody wrote this" from "we failed to read who wrote it", and anyone able to
arrange a null author could approve their own work.

**The candidate path answers a different question, and the fix was at the column.**
`record_verification` checks `performer is not None and performer == verifier`, so a candidate with
a null `captured_by` used to pass unconditionally: whoever captured it could verify it by arranging
for the column to be empty, which cost one `insert` omitting it. The schema justified the null with
legacy rows, and that turned out to be hypothetical, because no production database exists yet.

So `captured_by` is now `NOT NULL`. The case cannot be created, and the check cannot be skipped by
omission. Fixing it at the column rather than in the check matters: a guard in
`record_verification` would still leave the bad row in the table for every other reader.

**`assessed_by` and `verified_by` stay nullable, and that is not the same compromise.** A candidate
that has not been scored genuinely has no assessor; a candidate not yet verified has no verifier.
Null there means "this has not happened", not "we failed to record it", so there is no act to
conflict with and `is not None` is the correct test. The two paths were never applying opposite
rules to the same question, which is what the original finding (#297) claimed.

**The sole-operator exception.** INZBC is one person, so a strict BR8 would block all work.
`candidate_sod_exceptions` permits it — but the exception is a row: it names an approver, it
expires, its approver must be active, and it is itself audited. A soft warning instead would mean
the control was never really there.

**The gate applies at inclusion, not only at scoring.** Enforcing it at scoring alone left
`record_routing` able to set `included = true` unguarded, which is the decision that actually
matters. REQ-G-02 is the requirement; the gate now runs at the inclusion point under the same row
lock. Exclusion is deliberately never gated — removing something from a report needs no second
signature.

## 5. Audit event catalogue

`audit_log` is append-only in the database, not by convention: an INSERT/SELECT-only application
role plus a trigger that blocks UPDATE and DELETE (`database/audit_role.sql`).

**Audit rows share the mutation's transaction.** `record_audit` takes the caller's open
connection and never commits or rolls back. A function that committed would make the audit row
durable independently of the thing it records; one that opened its own connection could not share
the transaction at all. They commit together or not at all — so there is no such thing as a change
without its audit row, or an audit row for a change that did not happen.

| Action | Record | `old_value` → `new_value` | Notes |
|---|---|---|---|
| `run.create` | `runs` | → `Draft` | `reason` carries the run number |
| `run.transition` | `runs` | previous state → new state | Carries `approval_ref` for gated transitions |
| `candidate.capture` | `candidates` | → headline | |
| `candidate.score` | `candidates` | previous signal → new signal | |
| `candidate.verify` | `candidates` | previous verification → new | The BR8-gated one |
| `candidate.route` | `candidates` | previous routing → new | Includes the inclusion decision |
| `candidate.merge` | `candidates` | previous `duplicate_of` → new | |

Columns: `at`, `user_id` (the actor, or null for a system action), `action`, `record_type`,
`record_id`, `old_value`, `new_value`, `reason`, `approval_ref`.

**`approval_ref` is verified, not decorative**, and it points at one of two append-only tables
depending on when the gate happens.

| Gate | Verified against |
|---|---|
| `Draft → Run Authorised` (launch authority) | `run_authorisations`, kind `Launch` |
| `Paused → Coverage Locked` (resumption authority) | `run_authorisations`, kind `Resumption` |
| Every other human gate | `decision_records` |

The split exists because ADR-0005's decision streams are all keyed to `report_version_id`, and the
two run-level gates happen before any report version exists. Until `run_authorisations` was added
(#227) there was nowhere to record them, so `approval_ref` for exactly those two was unverifiable
free text — the two gates deciding whether a run may run at all accepted anything a caller typed.

**The run-level check matches run and kind, not just the id.** An authorisation recorded for
yesterday's run does not launch today's, and a resumption authorisation does not authorise a
launch. "Somebody authorised something about this run" is not the claim the state change makes,
which is the same rule the separation-of-duties exceptions follow: authority is granted for one
act, not a category.

A separate table rather than generalising `decision_streams`. Making that table reference either a
run or a report version would loosen ten foreign keys and checks that currently make an impossible
decision record unrepresentable, and weakening a working model in order to extend it is the wrong
trade.

**What is not audited, and should be.** Session establishment and sign-out write no `audit_log`
row; `users.last_login_at` is the only trace, and it is overwritten each time. That is thin for
answering "who was signed in when this happened", and it is worth closing before handover.

## 6. Data classification

Four levels. The classification drives retention and what may leave the system; the authoritative
inventory is [`../data/system-of-record-and-retention.md`](../data/system-of-record-and-retention.md).

| Level | What | Where |
|---|---|---|
| **Public** | FTA corpus, published content, source register | `fta_facts`, `source_library`, the website |
| **Internal** | Candidates, scores, routing, draft intelligence | `candidates`, `runs`, `report_versions` |
| **Restricted** | Staff identity and the record of who did what | `users`, `user_roles`, `audit_log`, `decision_records` |
| **Secret** | Credentials | Environment only, never the database, registered in [`../secrets-register.md`](../secrets-register.md) |

**The system holds no member data today.** Every table was checked. The only personal data is
staff names and emails in `users`, plus `users.id` references recording who acted. Everything else
is public source material.

**The exposure arrives with the member data, not before it.** Modules 2, 3 and 4 introduce member
records, prospects and delegation participants. The controls need to exist before that, because
retrofitting retention onto data already collected is how organisations end up holding things they
cannot justify.

## 7. Abuse cases

Ordered by how likely they are here, not by how alarming they sound.

| Abuse case | Control |
|---|---|
| One person captures, reviews and approves their own work | §4 — checked against recorded acts, exception must be a recorded, expiring, approved row |
| A caller claims to be someone else by supplying an `actor_id` | Identity comes from the session, never the request body. This was the state of the world before #42 |
| A new route ships with no role requirement | `test_router_auth.py` enumerates every mounted route and fails |
| A route is quietly widened to an extra role | Same test asserts the *exact* role set, not merely non-empty |
| A leaked database backup is used to resume live sessions | Only the SHA-256 digest is stored |
| A cross-site form POST performs a state change | Double-submit CSRF token; `SameSite=Lax` alone does not stop this |
| A departed person's session keeps working | `active` and roles re-read every request |
| Member-identifying prose reaches an external model | Boundary refusal by declared `PromptSource`, live on every call. `minimise()` exists for structured records but no module calls it yet. BR4 redaction as defence in depth |
| An audit row is edited to hide an action | Append-only trigger plus an INSERT/SELECT-only role |
| A session id is guessed | 32 random bytes |

The prose row is the one to understand properly, because it is the one where the obvious control is
the wrong one. No set of regexes catches a person's name in ordinary prose:
`Delegation lead: Priya Sharma, Chief Executive, Koru Exports Ltd` passes redaction untouched. And
review before publication is *not* the fallback, because review happens after the payload has
already reached the provider.

So the control is not to send it (`services/api/prompt_boundary.py`). Two halves, and they are
worth keeping distinct:

**`minimise()` is enforcement, and it is available rather than applied.** A caller names the fields
it needs, everything else is dropped before assembly, and a value that is not a scalar is refused
rather than passed through, so a field nobody named cannot reach the text. **No module calls it
yet**, because none handles member records yet. It is the rule the first one must follow, not a
control running today, and this table would be misleading if it implied otherwise.

**`PromptSource` is a declaration.** The gateway receives a string, so nothing about it reveals its
origin and a caller naming the wrong source is not caught. It is keyword-only with no default, so a
new call site cannot be written without answering the question and the answer shows up in review.
That is weaker than verification and much stronger than nothing.

**One path has no structural control**, and it is the only one reaching a model with staff text
today: the Comms Assistant brief is prose a staff member typed, so there is no record to minimise
and nothing can tell a member's name from any other words. A brief reading `Board minutes: Priya
Sharma, Chief Executive at Koru Exports, opposed the offer` satisfies `check_source`, survives
redaction untouched, and violates ADR-0006 §1 and §3 while every automated control reports success.

What bounds it is the operator being told not to. That is a procedure, not a boundary, and
procedures are what #223 existed to replace. Closing it means the request carrying named fields
instead of prose, so there is something to minimise. Tracked as #303.

## 8. Known gaps

Listed rather than implied, because a design document that only describes what works is a
marketing document.

| Gap | Issue |
|---|---|
| OAuth handshake not merged; sessions issued out of band | #99 |
| No module builds prompts through `minimise()` yet | ADR-0006 §2 |
| The Comms brief is free prose, so refusal cannot bound it; procedure only | #303 |
| A hollowed-out prompt is sent rather than refused | ADR-0006 §5, threshold is INZBC's to set |
| Session establishment and sign-out are not audited | this document, §5 |
| `users.mfa_enabled` exists but nothing reads or enforces it | this document, §1 |
| MFA on owned accounts unverified | register §3 |
| Backup never restored into an empty database | #290 |
| Semgrep rule sets are fetched at scan time, so an upstream rule change can fail an unrelated PR | CI `sast` job |

**One caveat that applies to every schema-level control above.** There is no migration mechanism
yet (#44): editing `schema.sql` changes freshly-provisioned databases only. Nothing is stale today,
because no production database exists (#99) and CI applies the schema from scratch on every run.
But a constraint added here is a guarantee about new databases, not about one already running, and
that stops being a technicality the moment there is a database to migrate.
