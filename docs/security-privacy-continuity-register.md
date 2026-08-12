# Security, privacy and continuity register

The client's Digital System Overview asks for fifteen things before major migration or automation.
This is the register of all fifteen: what each one is, where it lives, who owns it, and whether it
is actually done.

It is deliberately an index rather than a restatement. Most of these already exist as their own
document, and a register that copies their contents guarantees two versions that drift. Where a
row has no document, the content is in this file.

**The principle underneath the whole table**, taken from the brief and worth stating on its own:
*no important system should be controlled only through a personal email or phone.* Most rows below
are that sentence applied to a different asset.

## The register

| # | Control | Where it lives | Owner | Status |
|---|---|---|---|---|
| 1 | Account and licence register | [`account-licence-register.md`](./account-licence-register.md) | Technical Lead | Done; several cost figures `[[to confirm]]` |
| 2 | Data inventory | [`data/system-of-record-and-retention.md`](./data/system-of-record-and-retention.md) §2 | Privacy Owner | Done, proposed not approved |
| 3 | System-of-record map | [`data/system-of-record-and-retention.md`](./data/system-of-record-and-retention.md) §3 | Privacy Owner | Done, proposed not approved |
| 4 | Named system owners | §1 below | Executive Sponsor | Done |
| 5 | Role-based access | `database/schema.sql`, `services/api/auth.py` | Technical Lead | Enforced in code, see §2 |
| 6 | Multi-factor authentication | §3 below | Executive Sponsor | **Not verified** |
| 7 | Organisational ownership of domains and social accounts | [`account-licence-register.md`](./account-licence-register.md), §4 below | Executive Sponsor | Partly; social accounts **not verified** |
| 8 | Privacy impact assessment | §5 below | Privacy Owner | Screening done; full PIA due before member data |
| 9 | Retention and deletion rules | [`data/system-of-record-and-retention.md`](./data/system-of-record-and-retention.md) §4 | Privacy Owner | Done, proposed not approved |
| 10 | Backup and restore testing | Issue #290 | Technical Lead | **Not done** — see §6 |
| 11 | Incident response | [`incident-response.md`](./incident-response.md) | Executive Sponsor | Done, awaiting approval |
| 12 | Audit records | `audit_log`, `decision_records` in `database/schema.sql` | Technical Lead | Done, append-only |
| 13 | Vendor register | [`account-licence-register.md`](./account-licence-register.md) | Technical Lead | Done |
| 14 | Staff exit and access removal | [`incident-response.md`](./incident-response.md) § Joiners, movers, leavers | Executive Sponsor | Done, awaiting approval |
| 15 | Migration and rollback plans | [`migration-and-rollback.md`](./migration-and-rollback.md) | Executive Sponsor | Done, awaiting approval |

Nine rows point at documents that exist. The six that carry content are below, and two of them —
MFA and social account ownership — are unverified rather than done. That distinction is the point
of keeping the register.

---

## 1. Named system owners

Roles, not people, so the register survives a change of postholder. The Executive Sponsor currently
holds every owner role; there is no deputy.

| System | Owner role |
|---|---|
| `inzbc.org` domain | Executive Sponsor |
| Wix Vibe site and account | Executive Sponsor |
| GitHub organisation and its four repositories | Technical Lead |
| Member Jungle | Executive Sponsor |
| Zoho Backstage | Executive Sponsor |
| EmailOctopus | Executive Sponsor |
| OpenAI credential | Executive Sponsor |
| Render hosting | Technical Lead |
| Social accounts | Executive Sponsor |

**The concentration is the risk.** One person holds nearly all of it and has no deputy, which is a
stated client constraint rather than an oversight. It is recorded here because it is exactly the
situation the register exists to make visible, and because the controls that would normally
mitigate it — a second approver, a separate reviewer — cannot be assumed to exist.

## 2. Role-based access

Four roles, defined in `database/schema.sql` and enforced in `services/api/auth.py`:

| Role | May |
|---|---|
| Analyst | Capture and assess candidates |
| Quality Reviewer | Check sources and classification, stop a run |
| SIP Owner | Approve release |
| Secretariat | Configure, but not approve their own output |

Three things about how this is enforced, because each one is a place small systems usually get it
wrong.

**Every route asserts its roles.** A conformance test enumerates the mounted routes and fails if
any route has no role requirement, so a new endpoint cannot be added without one.

**Separation of duties is enforced against recorded acts, not role membership.** Checking role
membership is not enough here: role checks are an OR over the roles a person holds, so one person
holding both Analyst and Reviewer would pass both gates. The check asks who actually captured this
candidate, and refuses if that is the same person now verifying it (BR8).

**Sole-operator reality is handled explicitly, not by leaving a hole.** INZBC is one person, so a
strict BR8 would block all work. A recorded, expiring, approved exception permits it, and the
exception is itself an audited row. The alternative — a soft warning — would mean the control was
never really there.

## 3. Multi-factor authentication

**Status: not verified.** MFA is enabled per-account by whoever owns the account, and the team has
not seen the account settings for the services owned by the Executive Sponsor. Recording this as
unverified rather than assuming it is on.

What matters most, in order of what an attacker would actually target:

| Account | Why it is first |
|---|---|
| The registrar holding `inzbc.org` | Control of the domain is control of the address, email, and any certificate issued for it |
| Wix | Publishes the public site |
| GitHub | Source, CI, and any deployment credential |
| The email account used for password resets | Resets bypass every other control on this list |

The last row is the one usually missed. Every other account's recovery path runs through it, so
MFA on it is worth more than MFA on the accounts it protects.

**To close this row:** the Executive Sponsor confirms MFA is on for each account above, and the
date is recorded here. This is a five-minute check that no amount of documentation substitutes for.

## 4. Organisational ownership of domains and social accounts

Domains and paid services are covered in the account register. Social accounts are not, and they
are the classic gap: created by whoever ran communications at the time, on a personal login, and
still working years later so nobody notices.

**Status: not verified.** The team has not been given an inventory of INZBC's social accounts.

To close this row, for each of LinkedIn, Facebook, X, Instagram and YouTube — whichever exist:

- Does the account exist, and what is its handle?
- Is it owned by an INZBC-controlled login, or a personal one?
- Who has admin, and is that list current?

A LinkedIn *page* is the case worth naming: it has no independent login, and admin rights are held
by personal profiles. Organisational ownership there means more than one current person holds
super-admin, so a single departure does not orphan the page.

## 5. Privacy impact assessment

BR3 requires a PIA before member data or AI use. This is the screening; the full PIA is due before
module 2, 3 or 4 lands.

**The screening finding: the system holds no member data today.** Every table in the schema was
checked. The only personal data present is staff names and emails in `users`, plus references to
`users.id` recording who did what. Everything else is public source material.

So the current exposure is small, and saying so plainly is more useful than implying otherwise.

**Two things do need assessing now, because they exist now.**

*Staff personal data.* Names, emails and a complete record of every action each person took. That
record is the point — it is what makes the audit trail meaningful — but it is also employee
monitoring data, and it is append-only by design, so it cannot be deleted on request. That is a
deliberate trade-off between BR1's permanent approval record and an individual's correction rights,
and the resolution is that the record stands as the record of what happened, with corrections
appended rather than applied.

*Data sent to an external model.* BR4 requires redaction against an approved policy, and refusal
when no policy exists. The Comms Assistant is the path where member-identifying text could
plausibly reach a model. The control is that absence of a policy means refusal rather than
permission.

**What triggers the full PIA:** the first module that collects member data. That is modules 2, 3
and 4, and the assessment must be complete before collection begins — retrofitting retention onto
data already held is how organisations end up keeping things they cannot justify.

## 6. Backup and restore testing

**Status: not done.** Tracked as issue #290. It is on the register rather than only on the board
because BR12 makes a *tested* restore part of handover, and an untested backup is a belief rather
than a control.

Three distinct things need restoring, and only one of them has a real backup story today:

| What | Backup today | Gap |
|---|---|---|
| Postgres database | Whatever the host provides | Never restored into an empty database, so unproven |
| The Wix site | Wix Site History | Does not reliably cover CMS or app data; no complete external export exists |
| The repositories | GitHub, plus every clone | Genuinely fine |

The test that closes this: restore into an empty database, run the schema, and confirm the API
starts and serves. Anything short of that tests the backup file's existence, not the restore.

## 7. Annual supplier and integration review

Once a year, over the account register:

- Is each service still used? Cancel what is not.
- Is it still organisation-owned?
- Has its pricing or free-tier limit changed in a way that would break the zero-cost basis?
- For each integration, is the data flow still what the system-of-record map says it is?

The last question is the one with teeth. Integrations accumulate quietly, and a service that
started as a link-out can end up holding a second copy of the member register, which is a BR9
breach nobody decided to make.

## Approval

Rows 11, 14 and 15 are written and await the Executive Sponsor's approval. Rows 2, 3 and 9 are
proposed and await approval before data integration begins. Rows 6, 7 and 10 need INZBC to check
something the team cannot see from here.

Recording those three separately is deliberate: a document awaiting a signature and a control
nobody has verified are different kinds of incomplete, and only the second one is a live risk.
