# Preliminary privacy and data-flow assessment

Required by the Privacy Act 2020 and BR3, and it has to happen **before** the first real record is
stored rather than after. Verification against the built system is separate (#132).

**Status: assessment complete, not approved.** The Privacy Owner role sits with the Executive
Sponsor. Nothing here is a decision INZBC has made until it is signed.

## The finding that shapes everything

**The system holds no member data today, and that is the cheapest moment to write this.**

Every table in `database/schema.sql` was checked. The personal data present is:

| Table | Personal data | Whose |
|---|---|---|
| `users` | name, email, `github_login`, `last_login_at` | Staff and delivery team |
| `sessions` | `user_id`, session digest, timestamps | Staff |
| `user_roles`, `runs`, `report_versions`, `decision_records`, `audit_log`, `sod_exceptions`, `candidate_sod_exceptions`, `action_register`, `exceptions` | `users.id` references | Staff, recording who did what |
| `candidates` | **incidental** — names appearing in news headlines and summaries | Third parties, from public sources |

Everything else is public source material. `source_library.name` and `roles.name` are organisation
and role names, not people.

Two consequences, and the second is the one that matters.

**Today's exposure is small**, and saying so plainly is more useful than implying otherwise.

**The exposure arrives with modules 2, 3 and 4**, which introduce members, prospects, sponsors,
government contacts and delegation participants. The controls below need to exist *before*
collection begins, because retrofitting retention onto data already held is how an organisation
ends up keeping things it cannot justify — and the Act's answer to "why do you still have this" is
not "we never got round to deleting it".

---

## 1. What personal data can be captured, and which fields are necessary

### Staff and delivery team — `users`

| Field | Necessary? | Why |
|---|---|---|
| `name` | Yes | An audit trail reading `a3f2…` identifies nobody |
| `email` | Yes | Unique account key; the only contact route |
| `github_login` | Yes | The authentication match. Nothing works without it |
| `active` | Yes | The offboarding switch |
| `mfa_enabled` | **No** — nothing reads it | Declared and never used. Either enforce it or drop the column; an unused personal-data field is collection without purpose |
| `last_login_at` | Marginal | Overwritten each login, so it is a weak audit signal and a mild monitoring one. Keep, but see §5 |

### Acts — `audit_log` and the decision tables

Who did what, when. This is employee activity data and there is no point pretending otherwise.

**It is necessary**, because it is the entire control: BR1 requires a permanent approval record,
and BR8 needs to know who captured a thing in order to refuse them verifying it. An approval
record that can be edited afterwards is not a record.

**It is append-only, so it cannot be deleted on request.** That is a genuine tension with
correction and deletion rights, and the resolution is stated rather than hidden: the record stands
as the record of what happened, and a correction is appended rather than applied. Personal
information that forms part of a business record of a decision is not the same as personal
information held for its own sake, and this is the former.

**The limit worth holding to:** the log records *acts*, not behaviour. It should never accumulate
into general monitoring — session duration, idle time, page views. If a field would only ever
answer "how hard is this person working", it does not belong here.

### Third parties — `candidates`

Incidental and unavoidable. A news headline about a trade delegation names people. `headline`,
`summary` and `url` can each carry a name, a job title and an employer.

**It is necessary**, because the candidate *is* the article. **It is public**, sourced from
published material, which is what makes it proportionate. **It should not become a profile**: the
system stores articles, and building a person-keyed index across them would be a different
collection with a different purpose, and would need its own assessment.

### Members — not yet, and this is the gate

Modules 2, 3 and 4. Before the first member record is stored:

- Name each field and why it is necessary. The Act's principle 1 test is whether the agency
  *needs* it, not whether it is useful.
- Decide the collection notice wording — currently unwritten (see [`raci.md`](./raci.md), and the
  reason it is deliberately not drafted yet).
- Decide retention per field.
- Confirm the lawful basis for reusing data INZBC already holds for a different purpose. The
  Council has a membership register collected for membership administration; using it to drive an
  AI-assisted communications system is a new purpose and needs to be squared with principle 10.

That last point is the one most likely to be skipped and the most likely to matter.

## 2. Retention and deletion

Authoritative table: [`data/system-of-record-and-retention.md`](./data/system-of-record-and-retention.md)
§4. The reasoning behind the shape of it:

| Data | Retention | Why |
|---|---|---|
| `audit_log`, `decision_records` | Permanent | BR1. Deleting the record of an approval defeats the control |
| `candidates`, `runs`, `report_versions` | Life of the programme, then review | Working intelligence; no reason to keep indefinitely once superseded |
| `sessions` | 12 hours absolute, 60 minutes idle | Deleted on expiry, sign-out, or by `purge_expired()` |
| `users` | Deactivate, never delete | The audit trail references `users.id`; deleting the person removes the meaning from every action they recorded |
| Member data | Per-field, decided before collection | Not yet applicable |

**`purge_expired()` is written but nothing calls it on a schedule.** So an abandoned session row
survives until that same token is presented again. The session is not *valid* — every request
re-checks expiry — but the row persists, which is retention of personal data past its purpose.
Small, and worth a scheduled call. Recorded here rather than filed separately because it belongs
with the retention story.

## 3. External model calls

The highest-risk flow, and the only one where data leaves INZBC's control.

**The control is refusal, not masking.** `services/api/redaction.py` refuses outright when
`REDACTION_POLICY_PATH` is unset. Absence of a policy means refusal rather than permission,
because a redaction layer satisfiable by a rule set matching nothing gives false assurance, which
is worse than none.

**What redaction can do:** formatted identifiers — email, NZ and India phone numbers, IRD, NZBN,
GSTIN, PAN, passport numbers, payment cards, bank accounts, member identifiers, addresses,
credential shapes.

**What it cannot do, and no set of regexes will:** a person's name, job title or employer carried
in ordinary prose.

    Delegation lead: Priya Sharma, Chief Executive, Koru Exports Ltd

That passes through untouched. The control for prose is **not to send it** — prohibited inputs and
structured-field removal, so a brief's member fields are dropped before assembly rather than masked
afterwards. Tracked as #223, and until it exists this layer must not be described as making it safe
to send member data to a model.

**Review before publication is not the fallback.** Review happens after the payload has already
reached the provider. Publication review cannot undo a disclosure. The earlier version of the
policy document said otherwise and that error mattered.

**Retention at the provider** is a question INZBC must answer before member data is in scope, not
after: how long the provider retains prompts, whether they are used for training, and which region
they are processed in. The current answer is that no member data reaches a model, which makes the
question tractable rather than resolved.

## 4. Per-record visibility

Read access is role-gated but not row-gated: every staff role can read every candidate and every
run. For public source material that is right — withholding published articles from an auditor
serves nobody.

**It stops being right when member data lands.** A membership register readable by every role is
not proportionate, and row-level or field-level restriction has to be part of the module 3 design
rather than added afterwards. Flagging it now because the current model will look like a
precedent.

## 5. Logging and what ends up in it

| Concern | Position |
|---|---|
| Session tokens | Never logged. Only the SHA-256 digest is even stored |
| Credentials | Never in the database; environment only, `gitleaks` on every commit |
| Request bodies | Not logged wholesale |
| `audit_log` free text | `reason` is operator-written and *can* carry whatever they type — the one place personal data could enter without anyone deciding it should |
| Model prompts and responses | Not persisted today. #36 proposes usage logging, and that proposal is where this assessment applies |

Two of those rows deserve attention rather than a tick.

**`audit_log.reason` is unbounded operator text**, and it is append-only, so a name typed into it
cannot be removed. Worth an operator-guide line: reasons state what and why, not who beyond the
actor already recorded.

**#36's usage logging is the next real privacy decision.** Persisting prompts means persisting
whatever was in them, in a table nobody is currently thinking of as personal data. It should not
land without deciding what is retained and for how long.

## 6. Synthetic versus real data per environment

**There is no environment separation today.** Development, test and production are the same thing,
which means there is nowhere to test a migration that is not production. Tracked as #205, and it
is a privacy problem as much as an operational one.

The rules that should hold once #205 lands:

- **Production data never leaves production.** Not into a development database, not into a test
  fixture, not into a screenshot in a document.
- **Test data is synthetic.** The suite already works this way — fixtures construct users and
  candidates rather than copying real ones — and that should be a stated rule rather than a
  happy accident.
- **Demonstrations use synthetic data**, including client demonstrations. A demo is the most likely
  place real member data gets shown to someone who should not see it.
- **Each environment holds its own credentials.** A development environment holding the production
  OpenAI key is a production credential with development access controls.

## 7. Backup retention

Backups are copies of everything above, including the append-only tables, and they inherit the
retention question rather than escaping it.

**The honest status: untested.** Whatever the host provides has never been restored into an empty
database, so the restore path is a belief. Tracked as #290.

Three things to decide with the backup design (#48):

- **How long backups are kept.** A backup retained for two years holds personal data two years
  after its retention period ended everywhere else, which quietly defeats the deletion rules above.
- **Where they are stored**, and whether that is organisation-owned. BR11 applies to the backup
  location as much as to the live account.
- **Whether a deletion propagates.** If a member exercises a deletion right, a copy in a backup is
  still a copy. The usual and defensible answer is that backups are not amended, but that
  restoring one re-applies pending deletions — which only works if that step is written down and
  someone actually does it.

## 8. What must happen before member data is stored

The gate, in one list:

1. The full PIA for the specific module, naming each field and its necessity.
2. Collection notices written and published at the point of collection.
3. Retention decided per field, not per table.
4. Row-level visibility designed (§4).
5. #223 landed — prohibited inputs refused at the boundary (§3).
6. #205 landed — environments separated, production data staying in production (§6).
7. A restore proven, not assumed (#290).
8. Principle 10 squared: reusing INZBC's existing membership register for a new purpose.

**Items 5, 6 and 7 are open engineering work, not paperwork.** That is the honest summary of this
assessment: the privacy position today is defensible because the system holds almost nothing, and
three of the eight things standing between here and holding member data are unbuilt.
