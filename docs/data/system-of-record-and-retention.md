# System-of-record map, data inventory and retention

Two Phase 1 gate deliverables, kept in one document because they answer halves of the same
question: **where does each kind of data authoritatively live, and how long may it stay there.**

Closes #202 and #203. The map is proposed in the programme brief §6; this makes it a standalone
artefact that can be approved, and adds what is actually true today rather than only what is
intended.

**Status: proposed. Not approved.** The brief requires INZBC to approve the map before any data
integration begins.

---

## 1. The finding that shapes everything below

**The system holds no member data at all today.**

Every table in `database/schema.sql` was checked. The only personal data present is:

| Table | Personal data | Whose |
|---|---|---|
| `users` | name, email | Staff and team, not members |
| `user_roles`, `runs`, `report_versions`, `sod_exceptions`, `decision_records`, `audit_log`, `action_register`, `exceptions` | references to `users.id` | Staff, recording who did what |

Everything else is public source material: the FTA corpus, the SIP-185 source register, candidate
articles and the intelligence built from them. `source_library.name` and `roles.name` are
organisation and role names, not people.

Two consequences worth being clear about.

**The privacy exposure today is small**, and stating that plainly is more useful than implying
otherwise. The system processes public information and records which staff member acted.

**The exposure arrives with the member data, not before it.** Whichever way F1 lands, modules 2, 3
and 4 introduce member records, prospects, sponsors, government contacts and delegation
participants. The controls below need to exist *before* that, not alongside it, because
retrofitting retention onto data already collected is how organisations end up holding things they
cannot justify.

---

## 2. System-of-record map

One authoritative store per data type. The rule that makes it worth having: **no integration may
write to a system of record unless its contract, validation, permissions and audit behaviour are
approved.**

| Data type | System of record | Public copy allowed | Owner | State today |
|---|---|---|---|---|
| Legal entity and constitution | INZBC controlled document library | Approved documents only | Board Secretary `[[name]]` | Not in this system |
| Member register, current and former | **Member Jungle, provisionally** | Directory opt-in fields only | Membership owner `[[name]]` | Not in this system. Provisional pending F1 |
| Membership applications and approval | Membership platform | Status only, to the applicant | Membership approver `[[name]]` | Not in this system |
| Payments, invoices, refunds, GST | Payment and membership platform, reconciled to accounting | No | Treasurer `[[name]]` | Not in this system |
| Sponsor contracts and benefits | Internal CRM | Approved sponsor profile only | Sponsorship owner `[[name]]` | Not built |
| Trade-service requests and introductions | Internal CRM | No | CEO or delegate | Not built |
| Event master record | Selected event platform | Event details and registration | Events owner `[[name]]` | Not built. Platform undecided |
| SIP intelligence and source evidence | This repository's database and controlled documents | Approved digest only | SIP production owner `[[name]]` | **Live** |
| FTA corpus and source snapshots | `apps/fta/corpus.py`, under version control | Approved sourced guidance | FTA content owner `[[name]]` | **Live** |
| Website content | Wix CMS, with controlled source documents | Yes | Website content owner `[[name]]` | Live on `inzbc.org` |
| AI prompts, tests and evaluations | This repository | No | AI service owner `[[name]]` | **Live** |
| Audit and incident records | `audit_log`, append-only | No | Security owner `[[name]]` | **Live** |
| Staff and team identity | `users`, `user_roles` | No | Security owner `[[name]]` | **Live** |

Owners are roles, not people. Naming them is part of foundation decision F4, and an owner that is a
job title rather than a person is not an owner when something goes wrong.

### What actually enforces this

Worth separating from what merely documents it.

- **Enforced.** `audit_log` is append-only by trigger and by grant, and cannot be updated, deleted
  or cleared in one statement. Decision records are append-only for the same reason.
- **Convention only.** Nothing in the database stops a second store of the same data type
  appearing. The map is a decision people keep, not a constraint the schema imposes. That is
  honest rather than ideal, and the mitigation is review: a pull request that introduces a second
  home for an existing data type should be refused.

---

## 3. Data classification

Four levels, chosen to be usable rather than exhaustive. A scheme nobody can apply from memory
gets applied inconsistently.

| Level | Meaning | Examples | Handling |
|---|---|---|---|
| **Public** | Published, or intended to be | FTA corpus, approved digest, website content | No restriction |
| **Internal** | Not secret, not for publication | Source register, candidate articles, run records | Team access |
| **Confidential** | Commercial or personal harm if disclosed | Member records, sponsor contracts, trade enquiries, staff identity | Named access, logged |
| **Restricted** | Credentials and anything that grants access | API keys, database credentials, session material | Managed secret storage, never in the repository |

Personal data may appear at Confidential or Restricted, never lower. When in doubt the higher
level applies, because the cost of over-protecting is inconvenience and the cost of
under-protecting is a breach.

---

## 4. Retention

Under the Privacy Act 2020, personal information may not be kept for longer than it is required
for the purpose it may lawfully be used for. That is the test each row below answers.

| Data | Retention | Why |
|---|---|---|
| Staff and team identity (`users`) | While active, plus `[[period]]` after departure | Access removal is immediate; the identity is retained only so historic audit rows remain attributable |
| Audit records | `[[period]]`, minimum the current financial year plus one | An audit trail that expires before the thing it records has no value. Append-only, so deletion is a deliberate act |
| Run and decision records | Retained with the audit trail | Evidence of who approved what. Same reasoning |
| Candidate articles and source snapshots | `[[period]]`. Suggested: 24 months | Public material. Retained for provenance, not for its own sake |
| Approved digests | Indefinite | Published output, and the archive is a member benefit |
| FTA corpus | Indefinite, with verification dates | Superseded entries are retained so a past answer can be explained |
| Member records | Governed by Member Jungle while it is the system of record | Not ours to set while F1 is open |
| Trade enquiries and introductions | `[[period]]` | Contains personal and commercial information; the shortest defensible period is the right one |
| Prospective member and contact data | `[[period]]`, and consent recorded at collection | Data collected without a stated purpose cannot have a defensible retention period |

Periods are placeholders because retention is a business decision with legal consequences, and
inventing one would be worse than leaving it open. What is not open: every category needs an
answer before member data enters the system.

### Deletion

Deletion has to be possible, and for append-only tables it deliberately is not. That tension is
resolved by not putting personal data in them beyond a reference to `users.id`: an audit row
records *who* acted by identifier, and the identity it points at is what gets removed. The row
survives; the person it names does not remain identifiable once the user record is deleted.

This is why `audit_log` carries `user_id` and not a name or an email.

---

## 5. What INZBC must supply

| # | Needed | Blocks |
|---|---|---|
| 1 | A named person for each owner in §2 | The Phase 1 gate. An owner that is a job title is not an owner |
| 2 | Retention periods for each `[[period]]` in §4 | Any collection of member or contact data |
| 3 | Where Member Jungle stores and processes data, and whether members were told | The privacy impact assessment, and F1 |
| 4 | Confirmation of the F1 outcome | Which rows in §2 are provisional and which are settled |

Items 1 and 4 are in the [client decision pack](../client-decision-pack.md).

---

## 6. Related

- [Programme brief](../inzbc-ai-operating-system.md) §6 system-of-record map, §11 privacy controls
- [Member Jungle assessment](../membership/member-jungle-assessment.md) — F1, which settles the
  member register rows
- [Client decision pack](../client-decision-pack.md) — the decisions this waits on
- `database/schema.sql` — where the live rows in §2 actually are
