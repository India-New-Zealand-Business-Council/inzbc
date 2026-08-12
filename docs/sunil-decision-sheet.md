# Decisions needed from INZBC

Prepared 6 August 2026 for Sunil Kaushal, Executive Sponsor.

**Why now.** Build runs to **13 September 2026** (week 9); weeks 10–16 are refinement, not new
work. That leaves **5.4 weeks of build**. Nine items below are waiting on a decision only INZBC can
make. Each one blocks work that is otherwise ready to start.

Most are a single line of reply. Two need a conversation. One should be fixed today regardless of
everything else.

**If a decision is not made by the date shown**, the team will treat that module as *specified and
handed over* rather than built, and record it as such. That is a worse outcome than deciding, but a
better one than discovering it in week 9.

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

## 6. FTA sector coverage — three lists disagree

**Issue #219. Blocks the FTA Explainer, INZBC's own priority module. Decide by 15 August — the
tightest deadline on this sheet.**

Three different sector lists exist and none is marked settled:

| Source | Content |
|---|---|
| INZBC Digital System Overview, 3 Aug 2026 | Ten sectors: wool, wine, seafood, primary industries, tourism, education, defence and security, investment, immigration, sports |
| `client-answers.md` D19 | A different set and order — status PROPOSED |
| `requirements.md` and `fta-source-corpus.md` | Both record it as awaiting INZBC |

A builder cannot tell which specification governs, and the corpus research is sized differently
depending on the answer — ten sectors is roughly double the work of five.

**Needed: pick one list.** The ten from the Digital System Overview is the obvious default since
INZBC wrote it. If the true priority is narrower, say so — a well-built five is worth more than a
thin ten.

**This is the highest-risk item on the sheet.** The FTA Explainer is one of the four modules INZBC
selected. Every week this stays open is a week the corpus cannot be built, and it is the one item
where delay directly costs a committed deliverable.

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

| # | Decision | Issue | Blocks | By |
|---|---|---|---|---|
| 1 | Correct the FTA claim on the live homepage | #234 | Nothing — it is simply wrong today | **Today** |
| 6 | FTA sector list — pick one of three | #219 | FTA Explainer, a committed module | **15 Aug** |
| 7 | Password-protect staging | #229 | The rebuild starting | This week |
| 2 | Budget, billing owner, post-capstone owner | #214, #93, #97 | All deployment | 20 Aug |
| 3 | Member Jungle: retain / integrate / replace | #95 | Modules 2 and 3 | 20 Aug |
| 4 | Identity and login model | #213 | Every login surface, SIP roles | 20 Aug |
| 5 | Name the AI-output reviewer | #96 | Publishing any AI output | 20 Aug |
| 8 | Name Finance and Privacy Owners | #211 | Phase 1 gate | 20 Aug |
| 9 | Confirm Wix Studio and one-way cutover | #233 | — | 20 Aug |

**Fastest path:** items 1 and 7 are actions Sunil can take today without a meeting. Items 3, 4, 5
and 8 are each a one-line answer. Item 6 needs ten minutes. Item 2 is the only one likely to need a
real conversation.
