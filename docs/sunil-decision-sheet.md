# Decisions needed from INZBC

Prepared 6 August 2026 for Sunil Kaushal, Executive Sponsor.

> ## Status, 13 August 2026: eight of the nine are settled
>
> **Only item 2 is still open, and only part of it: who owns the platform after the placement
> ends (#97).** Everything else on this sheet was answered between 9 and 12 August.
>
> The sections below are kept as the record of what was asked and why, not as a list of
> outstanding questions. **Nothing on this page needs a fresh decision except #97.** Re-reading it
> as a request would be asking INZBC to answer things it has already answered, which costs more
> than the sheet ever saved.
>
> The summary table at the bottom carries the current state of each item.

**Why this was written.** Build runs to **13 September 2026** (week 9); weeks 10–16 are refinement,
not new work. That left **5.4 weeks of build**, and nine items were waiting on a decision only INZBC
could make, each blocking work that was otherwise ready to start.

**If a decision had not been made by the date shown**, the team would have treated that module as
*specified and handed over* rather than built, and recorded it as such. That did not happen: the
answers arrived.

---

## 1. The live homepage is factually wrong — fix today

**Issue #234. Not a decision. A correction, and it is Sunil's because it is a live-site edit.**

The homepage currently says:

> "With the New Zealand–India Free Trade Agreement **now in effect**, INZBC members gain
> first-mover advantage…"

The agreement is **not in effect**. It was signed 27 April 2026 and awaits domestic ratification in
both countries. That is what MFAT says, and it is what INZBC's own sourced corpus says — every FTA
Explainer answer already carries that status.

So the Council's homepage contradicts the FTA position the Council is the authority on. An exporter
who checks MFAT finds INZBC wrong about the agreement it exists to explain.

**Needed:** change "now in effect" to "signed in April 2026 and awaiting ratification", or
equivalent. One sentence, live site, today.

---

## 2. F4 — Budget, ownership and support model

**Issue #214, with #93 and #97. Blocks: all deployment. Decide by 20 August.**

This is the one that stops the most work. Nothing that costs money is provisioned without it, which
means **nothing is deployed at all** — and a system that is never deployed cannot meet the
objectives about running it or handing it over.

Three questions:

**(a) Who owns the cloud billing account?** A cloud account needs a billing owner and a payment
method. Expected cost is around **$5/month at this traffic** — but that figure is not confirmed,
and the team has deliberately not asserted it. Public sources disagree about whether the free
allowance is region-restricted or a spending discount, and the primary documentation could not be
reached. The plan is to deploy, run for a day, read the actual billing report, and record the real
number before committing.

**(b) What is the monthly ceiling?** A figure INZBC is comfortable with, so a budget alert can be
set.

**(c) Who owns the platform after the placement ends?** The engagement has a fixed end date. Needed:
who holds the cloud account, who holds the repository and can merge, and whether INZBC registers its
**own** OAuth application rather than depending on one tied to an individual. The current default,
if nobody is named, is that the infrastructure is torn down at handover and the system reverts to a
manual process — which is a deliberate default, not an oversight, but probably not what INZBC wants.

---

## 3. F1 — Member Jungle: retain, integrate, or replace

**Issue #95. Blocks: member portal and membership CRM (modules 2 and 3). Decide by 20 August.**

Membership currently runs on Member Jungle. The site links out to it rather than duplicating any
member data, and the team has deliberately built nothing on top until this is settled — because one
data type must have exactly one system of record, and two member registers diverge immediately.

**Team recommendation: retain and integrate for now.** Replacing a working membership system inside
a placement window is high risk for little gain.

**What each choice means:**

- **Retain** — Member Jungle stays authoritative. The website links out. Lowest risk, deliverable.
- **Integrate** — Member Jungle stays authoritative, but the site reads from it for the directory
  and gated content. Needs API access and credentials from Member Jungle.
- **Replace** — membership is rebuilt. **Not deliverable in the remaining window**, and would need
  member data migration, payments and GST handling.

**Honest position:** modules 2 and 3 are already at risk. Even with a decision on 20 August, a
*replace* answer cannot be built by 13 September. Retain or integrate keeps them alive.

---

## 4. F3 — The identity and login model

**Issue #213. Blocks: every login-gated surface, and SIP's separation of duties. Decide by 20 August.**

Which service controls identity for public members, staff, board members, administrators and
service accounts.

This matters more than it sounds. SIP's entire safety model rests on four roles being **different
identities**: the analyst who captures, the reviewer who checks, the approver who releases, and the
administrator who configures but may not approve their own work. If those are not distinguishable
identities, the approval record is decorative — one person could execute the whole chain, and the
audit trail would prove nothing.

**Needed:** which system holds staff and board logins. If INZBC has Microsoft 365, that is the
obvious candidate.

---

## 5. Name the human reviewer for AI-drafted output

**Issue #96. Blocks: publishing anything AI-drafted. Decide by 20 August.**

Every AI-drafted output must be approved by a **named human** before it reaches a member or the
public. That is enforced in code by fail-closed gates — the system refuses to publish rather than
publishing unreviewed.

Nobody has been named, so the gate can never open. `production_enabled` stays `false` until a formal
launch approval exists.

**Needed:** one name (and ideally a deputy) accountable for approving AI-drafted content before
release. Also outstanding: confirmation of the FTA Explainer's disclaimer wording.

---

## 6. FTA sector coverage — settled, no decision needed

**Issue #219. Settled 9 August 2026. Nothing is asked of INZBC here.**

This section previously asked the Council to pick between three disagreeing sector lists, and it was
the highest-risk item on the sheet. It was answered on 9 August and the answer stood; the section
stayed open afterwards, which is a fault in this document rather than a question still outstanding.

**How it was resolved: by scope, not by choosing one of the three lists.** A sector is built when it
has a source, per BR2, so the list grows as material is sourced rather than on further confirmation.

| State | Sectors |
|---|---|
| Built now (`SECTORS_IN_SCOPE`) | Agriculture, Cross-sector, Dairy, Infrastructure |
| Sourced next, from the agreement text | Tourism, education, investment |
| Not dropped, not sourced, not gating the build | Defence and security, immigration, sports |

The ten sectors in the Digital System Overview are not contradicted by that. Nothing is written
about a sector until it has a source, so the shorter list is what is currently *supported*, not a
narrower ambition.

**If INZBC wants a different priority order for the "sourced next" group, that is worth saying.** It
changes what gets built first. It is not a blocking decision, and no one should treat it as one.

---

## 7. Password-protect the staging site

**Issue #229. Blocks the rebuild starting. Only Sunil can do it. Today or this week.**

The staging duplicate was published on 4 August at
`https://inzbcsecretariat.wixsite.com/website-2`. It is now a **public copy of INZBC's content**,
reachable by anyone with the link and indexable by search engines.

The rebuild puts `[[placeholder]]` markers wherever INZBC still owes a fact — the member count, the
fee structure, the patron's details. Those are correct in a draft and indefensible on a page
carrying the Council's name.

**Needed:** set a site password in the Wix dashboard. There is no API for it, so it must be done by
hand by the account owner.

`robots.txt` was considered and rejected — it blocks crawling but not indexing, stops nobody holding
a link, and if it survived cutover it would tell search engines to drop `inzbc.org` entirely.

---

## 8. Phase 1 gate — name the remaining signatories

**Issue #211. Decide by 20 August.**

The Phase 1 gate requires four signatures: Executive Sponsor, **Finance Owner**, **Privacy Owner**,
and Technical Lead. Two have never been named, so the gate is currently unsignable by anyone.

The team has continued building against the specifications rather than stopping, and has recorded
that as a deliberate deviation. Nothing is deployed or given real data while the gate is open. INZBC
should know this is happening rather than find out at handover.

**Needed:** name a Finance Owner and a Privacy Owner. They may be the same person as the sponsor.

---

## 9. F5 — Editor or Studio (likely already resolved)

**Issue #233. Listed for completeness.**

The rebuild is being built on **Wix Studio**, which effectively answers this. Two consequences INZBC
should be aware of, both from Wix's own documentation:

- **Design does not carry over** between Editor and Studio. Pages and content are recreated by hand.
- **Publishing a Studio branch is one-way.** It unpublishes the Editor version and cannot be
  reversed.

**Needed:** confirmation that Studio is accepted, and acknowledgement that cutover is irreversible.

---

## Summary

Every issue below was checked against the tracker on 13 August rather than from memory.

| # | Decision | Issue | Status |
|---|---|---|---|
| 1 | Correct the FTA claim on the live homepage | #234 | Settled |
| 2 | Budget and billing owner | #214, #93 | Settled |
| 2 | **Post-capstone platform owner** | **#97** | **Open — the only one** |
| 3 | Member Jungle: retain / integrate / replace | #95 | Settled: retain, link out, no integration |
| 4 | Identity and login model | #213 | Settled |
| 5 | Name the AI-output reviewer | #96 | Settled |
| 6 | FTA sector list | #219 | Settled 9 Aug, by scope rather than by picking a list |
| 7 | Password-protect staging | #229 | Settled |
| 8 | Name Finance and Privacy Owners | #211 | Settled: the Executive Sponsor holds every owner role |
| 9 | Confirm Wix Studio and one-way cutover | #233 | Settled |

**What is actually left.** One question: who owns the platform after the placement ends (#97). Who
holds the cloud account, who holds the repository and can merge, and whether INZBC registers its own
OAuth application rather than depending on one tied to an individual.

That one does need a conversation, and it is the only item here that does. The default if nobody is
named is that the infrastructure is torn down at handover and the system reverts to a manual
process. That default is deliberate rather than an oversight, and it is probably not what INZBC
wants, which is the reason to decide it rather than let it happen.
