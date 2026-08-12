# Platform operator guide

For a competent operator with **no prior involvement** in building this. That is BR12 and charter
objective O6, and it is the test this document has to pass: if you have to ask one of the people who
built it, the document has failed.

**This is the guide for the platform.** The controlled launch runs on a workbook and has its own
guide at [`sip/operator-guide.md`](sip/operator-guide.md). That one assumes an analyst and a
reviewer who are different people. This one does not, because after handover INZBC is one person
holding every role, and a guide that assumes a second person is a guide that cannot be followed.

---

## 1. Before you can do anything

**You need a session.** The platform does not accept a username in a request; identity comes from a
server-side session established from a GitHub sign-in.

**Being signed in to GitHub is not enough.** Your GitHub login has to match an active row in
`users`. If it does not, you get `403` and no session, and the message is deliberately the same
whether the account is unknown or deactivated.

**Your roles decide what you can do**, and they come from `user_roles` in the database, not from
GitHub. Changing who holds a role is a database change, not a deployment.

| Role | What it lets you do |
|---|---|
| Analyst | Create and complete runs; capture, score, route and merge candidates |
| Reviewer | Verify candidates; fail QA on a run |
| SIP Owner | Start, pause, resume and stop a run; approve release |
| Secretariat | Draft comms |
| Administrator, Board Viewer, Auditor | Read |

**Check who you are at any time:** `GET /api/session`. It returns your user id, name, roles, and
the CSRF token you need for writes.

**Every write needs that CSRF token** in an `X-CSRF-Token` header. A write without it returns 403.
This is not optional and it is not a bug.

**Sessions expire two ways:** 12 hours after sign-in no matter what, and 60 minutes after your last
request. Whichever comes first. When one expires you get 401 and sign in again.

## 2. A SIP day, end to end

Eleven states. Three of them wait for a person, and those are the control rather than a delay.

```
Draft → Run Authorised → Coverage Locked → Scanning → Candidate Review → Report Drafted
      → QA In Progress → Awaiting CEO Decision → Approved for Manual Distribution
      → Distributed → Closed
```

| Step | What you do | Endpoint | Role |
|---|---|---|---|
| 1 | Create the run | `POST /api/runs` | Analyst |
| 2 | Authorise it to start | `POST /api/runs/{id}/start` | SIP Owner |
| 3 | Capture each candidate | `POST /api/candidates` | Analyst |
| 4 | Score it | `POST /api/candidates/{id}/score` | Analyst |
| 5 | Verify it | `POST /api/candidates/{id}/verify` | **Reviewer** |
| 6 | Decide inclusion | `POST /api/candidates/{id}/route` | Analyst |
| 7 | Merge duplicates | `POST /api/candidates/{id}/merge` | Analyst |
| 8 | Complete the run | `POST /api/runs/{id}/complete` | Analyst |

**Every write records who did it**, in an audit row that is written in the same transaction as the
change. There is no way to make a change without its audit row, and no way to remove one afterwards.

**Two things you can do at any point:**

- `POST /api/runs/{id}/pause` — stop and come back. SIP Owner.
- `POST /api/runs/{id}/fail-qa` — the quality stop. **Reviewer or SIP Owner**, deliberately: a
  quality gate only the owner can pull is not independent of the owner.

**If nothing happened today, still do the run.** Record the coverage and conclude no material new
signal. That is a complete, correct run, and a day with no record is indistinguishable from a day
nobody worked.

## 3. Refusals, and what each one means

This is the section to read first, because as a single operator you will hit three of these
routinely. **A refusal is the system working.** None of these are faults to be worked around.

### "the person who produced this cannot also review or approve it"

**What happened.** You are verifying a candidate that you captured or scored. BR8: separation of
duties.

**Why it is not negotiable in code.** Holding both the Analyst and Reviewer roles would pass both
role checks, because a role check asks what you hold, not what you did. The system instead asks who
is *recorded* as having captured this, and refuses if that is you.

**What to do.** If someone else can review it, have them. If nobody can — the normal case for INZBC
— record a separation-of-duties exception (§4) and cite it. Do not backfill a different name into
the provenance columns. That is falsifying the record the control exists to produce.

### "cannot establish who produced this, so separation of duties cannot be checked"

**What happened.** The record has no author, so the check cannot run.

**What to do.** Find out who produced it and record it, or raise an exception. The refusal is
correct: the system cannot tell "nobody wrote this" from "we failed to read who wrote it", and
treating the two the same is how someone approves their own work.

### The candidate is not verified, and you are trying to include it

**What happened.** Inclusion in a report requires verification first (REQ-G-02). The gate sits at
inclusion, not only at scoring, because inclusion is the decision that actually reaches a reader.

**What to do.** Verify it, or exclude it. **Excluding is never gated** — taking something out of a
report needs no second signature, only putting it in does.

### "no approved redaction policy" — every model call refuses

**What happened.** `REDACTION_POLICY_PATH` is not pointing at a policy file in this environment.

**Why it refuses rather than sending unredacted text.** An environment nobody configured must fail
closed. A redaction layer satisfiable by an empty rule set would give false assurance, which is
worse than none.

**What to do.** Point `REDACTION_POLICY_PATH` at the approved policy file and restart.
[`redaction-policy.md`](redaction-policy.md) names it and records who approved it. If you are being
asked to approve a *different* policy, that is a business decision rather than an engineering one,
and the same document sets out what changing a rule requires.

**What this does not make safe.** The policy matches formatted identifiers: emails, phone numbers,
tax and company numbers, cards, bank accounts. It cannot catch a person's name, job title or
employer in ordinary prose, and no set of regexes will. `Delegation lead: Priya Sharma, Chief
Executive, Koru Exports Ltd` passes through untouched. **Do not paste member details into a brief
and rely on redaction.** Reviewing the output afterwards does not help either, because the text
already reached the provider.

### "may not be sent to an external model"

**What happened.** The call declared a prohibited origin: a member record, a CRM note, Board
material or a private message. It was refused before a policy was read or a key was looked up, so
nothing left the process.

**Why configuring redaction does not fix it.** This is the refusal working. The policy matches
formatted identifiers and cannot catch a name or job title in prose, so for that data the answer
is not to send it at all.

**What to do.** Build the prompt from an explicit list of the fields you actually need, and send
that instead of the whole record. If you cannot do the task without the prohibited fields, the
task needs a decision from the Executive Sponsor, not a workaround.

**The one case with no automatic protection** is the Comms Assistant brief, because you type it
yourself and nothing can tell a member's name from any other words. That is why the warning above
matters: there is no refusal waiting to catch that one.

### 401 "no session" / "session expired" / "session idle too long"

Sign in again. Nothing is wrong.

### 403 "requires one of: ..."

You are signed in and do not hold a role for this operation. Signing in again will not help. Either
someone grants you the role, or the right person does the step.

### 403 "missing or invalid CSRF token"

You did not send `X-CSRF-Token`, or it was stale. Fetch a current one from `GET /api/session`.

### 503 "DATABASE_URL is not configured"

An environment problem, not yours. The service is running without a database.

## 4. Recording a separation-of-duties exception

**For INZBC this is the normal path, not the exceptional one.** One person holds every role, so a
strict reading of BR8 would block all work. The exception exists so that single-operator work is
*recorded* rather than *unenforced*, and the difference between those two matters more than it
sounds: a soft warning would mean the control was never really there.

An exception is a row in `candidate_sod_exceptions`. It authorises **one act on one candidate by
one person**, not a category and not a standing waiver.

Each one needs:

| Field | Meaning |
|---|---|
| The candidate | Which one. An exception does not cover the next candidate |
| The actor | Who is being exempted |
| The approver | Who authorised it. **Cannot be the actor** |
| Review date | When it lapses. A lapsed exception authorises nothing |

Four ways it will be refused, each closing a real hole:

- **The approver is the actor.** A self-approved exception is self-approval with an extra step.
- **The approver's account is inactive.** An approval from someone who has left is not a current
  approval.
- **The review date has passed.** A lapsed approval is not a current one.
- **It names a different candidate or actor.** An exception authorises one act, not a category.

**Cite it on the call** that would otherwise be refused, by passing its id. The exception and the
act it permitted are both in the audit trail, so "one person did this alone, and here is who said
they could" is answerable later.

**If the only available approver is also the actor**, you do not have an exception, you have a gap.
Record the work as not done rather than manufacturing an approval. That is the honest state and it
is recoverable; a falsified approval is not.

## 5. Rotating a credential

Every 90 days, and immediately if one is exposed. The register is
[`secrets-register.md`](secrets-register.md).

**The order matters:** create the new credential, put it in the environment, restart, confirm it
works, *then* revoke the old one. Revoking first means an outage while you find out whether the new
one works.

| Credential | What stops while it is wrong | Notices how? |
|---|---|---|
| `DATABASE_URL` | Everything. Reads and writes both | Immediately, 503 |
| `OPENAI_API_KEY` | The FTA Explainer and Comms Assistant | The call fails; it does not degrade quietly |
| GitHub OAuth secret | New sign-ins. **Existing sessions keep working** | Only when someone tries to sign in |
| NewsAPI key | One collection source | The collector records the failure rather than skipping it silently |

**The GitHub row is the one that will confuse you.** Sessions are server-side and do not consult
GitHub after sign-in, so rotating the OAuth secret breaks *new* sign-ins while everyone already
signed in carries on. It can look fine for hours.

**Never commit a credential.** `gitleaks` runs on every commit and will block it. If one does reach
git history, rotating is necessary and not sufficient: the value stays in the history.

**If a credential is exposed, follow [`incident-response.md`](incident-response.md)**, which starts
with containment rather than investigation.

## 6. Reading the audit trail

The system exists to answer *who approved this, and when*. Here is how to ask.

**`audit_log`** — every write. Columns: `at`, `user_id`, `action`, `record_type`, `record_id`,
`old_value`, `new_value`, `reason`, `approval_ref`.

**`decision_records`** — the recorded human decisions, including who approved a release.

Actions you will see: `run.create`, `run.transition`, `candidate.capture`, `candidate.score`,
`candidate.verify`, `candidate.route`, `candidate.merge`.

Useful questions and how to ask them:

| Question | Where to look |
|---|---|
| Who verified this candidate, and when? | `audit_log` where `record_id` is the candidate and `action = 'candidate.verify'` |
| Who authorised this run to start? | `run.transition` rows for that run; `approval_ref` points at the decision |
| What did this person do on Tuesday? | `audit_log` filtered by `user_id` and date |
| Was anything approved by its own author? | Compare the actor on `candidate.verify` against `captured_by` on the candidate |

**You cannot edit or delete an audit row.** A trigger blocks UPDATE and DELETE, and the application
role only holds INSERT and SELECT. If you need to correct the record, add to it. A record that can
be edited afterwards is not a record.

**`old_value` and `new_value` tell you what changed**, so you do not have to reconstruct state from
the current row. The current row tells you where things ended up; the log tells you how they got
there.

**One honest limit:** signing in and out are not audited. `users.last_login_at` is overwritten each
time, so "who was signed in when this happened" is not fully answerable today. Every *action* is
attributed; the sessions around them are not.

## 7. When to stop

Stop the run, and do not work around it, when:

- A mandatory source is unreachable and the fallbacks are exhausted. Record it as inaccessible.
  Blank is the only unacceptable answer.
- You cannot verify something you believe is important. Capture it, mark it unverified, and do not
  let it carry a high-confidence claim.
- The redaction policy is not configured and you are being asked to send text to a model anyway.
- You are being asked to approve your own work without an exception.

**A stopped run with a recorded reason is a good outcome.** A completed run that skipped a gate is
not, and it is worse for being invisible.

## 8. Where things are

| What | Where |
|---|---|
| This guide (the platform) | `docs/operator-guide.md` |
| The controlled launch on the workbook | [`sip/operator-guide.md`](sip/operator-guide.md) |
| The data model | `database/schema.sql` |
| The API contract | `schemas/api-contract.md` |
| Run states and legal transitions | `schemas/state-machine.md` |
| Credentials | [`secrets-register.md`](secrets-register.md) |
| Accounts and vendors | [`account-licence-register.md`](account-licence-register.md) |
| When something goes wrong | [`incident-response.md`](incident-response.md) |
| Security design | [`security/README.md`](security/README.md) |
| Backup and monitoring | [`backup-and-monitoring.md`](backup-and-monitoring.md) |
| What the redaction policy does and does not do | [`redaction-policy.md`](redaction-policy.md) |

## 9. What this guide cannot yet tell you

Stated so you find out here rather than at the moment you need it.

- **How to sign in through the browser.** The OAuth handshake is not merged (#99, #296). Sessions
  are currently issued out of band by `scripts/dev_session.py`, which needs database access.
- **How long a restore takes.** Never tested (#290). Until it is, the recovery position is a belief.
- **Who owns the platform after the placement.** Still an INZBC decision (#97), and the handover
  pack has no named recipient without it.
