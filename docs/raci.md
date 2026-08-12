# RACI and the governance document set

Two things the brief asks for, kept together because the second is mostly a list of who owns what:
a responsibility matrix for the programme's decisions, and a tracker for whether the governance
documents actually exist.

## How to read the matrix

**R** does the work. **A** is answerable for the outcome and signs it off — exactly one per row,
because two accountable people means none. **C** is consulted before the decision. **I** is told
after.

Roles rather than names, so the matrix survives a change of postholder. During this engagement the
delivery roles map to Bhanu Gupta (Technical Lead), Roshan (Intelligence and Data) and Paras
(Product and User Experience); the Executive Sponsor is Sunil Kaushal, who holds every client-side
owner role with no deputy.

**That last fact makes several rows unusual and they are left that way honestly.** Where the
Executive Sponsor is both A and the only available C, the matrix says so rather than inventing a
consultee who does not exist.

## The matrix

| Decision or deliverable | Exec Sponsor | Technical Lead | Intelligence & Data | Product & UX |
|---|---|---|---|---|
| **Governance** | | | | |
| Scope and priority | **A** | C | C | C |
| The four foundation decisions (F1–F4) | **A/R** | C | C | C |
| Business rules BR1–BR12 | **A** | R | C | C |
| Phase gate sign-off | **A** | R | C | C |
| Architecture decision records | I | **A/R** | C | C |
| **Content and facts** | | | | |
| Factual approval of public content | **A/R** | I | C | C |
| FTA source corpus | C | I | **A/R** | I |
| Information Confidence Standard wording | **A** | C | R | C |
| Release of an AI-drafted output (BR1) | **A** | I | R | R |
| **Platform** | | | | |
| Shared contracts: API, schema, state machine | I | **A/R** | C | C |
| Identity, roles and access model | C | **A/R** | I | I |
| Security and privacy controls | C | **A/R** | C | C |
| Merge to `main` | I | **A/R** | C | C |
| Deployment and hosting | I | **A/R** | I | I |
| **Website** | | | | |
| Site rebuild and content | C | I | I | **A/R** |
| Accessibility to WCAG 2.2 AA | I | C | I | **A/R** |
| Redirect map | C | C | I | **A/R** |
| **Publishing to `inzbc.org`** | **A/R** | I | I | I |
| **Written go-live authority and cutover date** | **A/R** | C | I | C |
| **Data and privacy** | | | | |
| System-of-record map and retention rules | **A** | R | C | C |
| Privacy impact assessment | **A** | R | C | C |
| Breach notification decision | **A/R** | C | I | I |
| Redaction policy | **A** | R | C | I |
| **Operations** | | | | |
| Account, licence and vendor register | **A** | R | I | I |
| MFA on owned accounts | **A/R** | C | I | I |
| Quarterly access review | **A** | R | I | I |
| Incident response | **A** | R | C | C |
| Backup and restore testing | C | **A/R** | I | I |
| Handover pack | **A** | R | C | C |

Three rows are worth reading twice, because they are where the programme's authority actually sits.

**Publishing to `inzbc.org` is A/R on the Executive Sponsor alone.** Not a governance preference —
a technical fact. Publishing is a button in the Wix Vibe editor, there is no API, and only the
account owner has it. The matrix records reality rather than an aspiration.

**Merge to `main` is A/R on the Technical Lead.** A single merger is what keeps the shared
contracts from shifting underneath a dependent lane.

**Breach notification is A/R on the Executive Sponsor.** The Privacy Act obligation sits with the
agency, not with a contractor. The delivery team can assess and advise; the decision is the
client's, and it cannot be delegated to whoever happens to notice the breach.

## The governance document set

The brief lists these with homes but no contents. This tracks the set being complete.

| Document | Where | Owner | Status |
|---|---|---|---|
| Decision register | [`decisions/`](./decisions/) | Technical Lead | Done, 6 ADRs |
| RACI | this file | Executive Sponsor | Done |
| Licence and account register | [`account-licence-register.md`](./account-licence-register.md) | Technical Lead | Done |
| Vendor register | [`account-licence-register.md`](./account-licence-register.md) | Technical Lead | Done |
| Privacy notices | — | Privacy Owner | **Not written** — due with the first member-data collection point |
| Privacy impact assessment | [`security-privacy-continuity-register.md`](./security-privacy-continuity-register.md) §5 | Privacy Owner | Screening done; full PIA due before modules 2–4 |
| Threat model | §below | Technical Lead | Done |
| Incident response | [`incident-response.md`](./incident-response.md) | Executive Sponsor | Done |
| Staff exit and access removal | [`incident-response.md`](./incident-response.md) | Executive Sponsor | Done |
| System-of-record map | [`data/system-of-record-and-retention.md`](./data/system-of-record-and-retention.md) | Privacy Owner | Done, proposed |
| Data inventory | [`data/system-of-record-and-retention.md`](./data/system-of-record-and-retention.md) | Privacy Owner | Done, proposed |
| Retention and deletion | [`data/system-of-record-and-retention.md`](./data/system-of-record-and-retention.md) | Privacy Owner | Done, proposed |
| Migration and rollback | [`migration-and-rollback.md`](./migration-and-rollback.md) | Executive Sponsor | Done |
| Test plans | [`requirements.md`](./requirements.md) traceability matrix, plus CI | Technical Lead | Done for built modules |
| Operational runbooks | [`sip/operator-guide.md`](./sip/operator-guide.md), [`sip/launch/`](./sip/launch/) | Technical Lead | Done for SIP; #289 covers the rest |
| Security, privacy and continuity register | [`security-privacy-continuity-register.md`](./security-privacy-continuity-register.md) | Technical Lead | Done |

**One document is genuinely missing rather than merely unapproved: privacy notices.** That is not a
gap to fill now. A collection notice has to name what is collected, why, and who it is shared with,
and none of those are known until the F1 decision settles how membership data is held. Writing one
against a hypothetical data model would produce a notice that is wrong on the day it matters, which
is worse than a blank, because a published notice is a representation to the person reading it.

## Threat model

Deliberately short. A threat model that lists every conceivable attack is a document nobody reads;
this lists what would actually go wrong here, in the order it is likely to.

| What could happen | How likely | Where it hurts | What stops it |
|---|---|---|---|
| An AI-drafted output publishes an invented or wrong fact | **Most likely thing on this list** | Credibility with ministers and exporters — the asset the Council actually has | BR1 named human approval, BR2 no invented facts, BR5 corpus-only answers with a distinct no-match |
| A credential leaks through the repository | Moderate — it is the common failure | Whatever the credential reaches; the OpenAI key is the billable one | `gitleaks` on every commit, 90-day rotation, secrets register |
| A departing person keeps access | Moderate, and rises at week 16 | Quiet, total, and discovered late | Leaver checklist, quarterly access review, `users.active = false` |
| One person performs capture, review and approval alone | **Certain** — INZBC is one person | The audit trail becomes decorative | BR8 enforced against recorded acts; sole-operator work needs a recorded, expiring, approved exception |
| Member data reaches an external model | Low today (no member data), rising with modules 2–4 | Privacy Act exposure and member trust | BR4 redaction, refusal when no policy exists, ADR-0006 model/data boundary |
| The domain or Wix account is taken over | Low | Total loss of the public presence | MFA — **unverified, see the register** — and organisational ownership under BR11 |
| Cutover loses inbound links and search position | Moderate without the control | Years of accumulated ranking | BR7 redirect map, verified before cutover, rollback plan |
| Postgres is lost and the backup does not restore | Low, but untested | Every run, decision and audit record | Nothing yet — **this is the open one**, issue #290 |

Two honest notes about this table.

**The top row is not a security threat in the usual sense**, and it is first anyway. The realistic
worst outcome for INZBC is not an intruder; it is the system confidently publishing something
false under the Council's name. Most of the controls in this repository exist for that row.

**The bottom row is the only one with no control at all.** It is low likelihood, which is why it
has not been done, and it is total loss if it happens, which is why it should not stay that way.
