# Decisions for INZBC

**Prepared for:** Sunil Kaushal, Executive Sponsor
**Date:** 5 August 2026, end of Week 3
**Purpose:** six decisions that belong to INZBC, in one place, so they can be worked through in a
single sitting.

Each one below states the question, the options, what it costs to leave open, and what the team
recommends. **None of them is decided here.** The recommendations exist so the decision is quick,
not so it is pre-empted.

Between them these six are holding up **17 tracked items**, including the deployment due this
Friday. That is why they are presented together rather than raised one at a time.

Where a figure is missing it is marked `[[like this]]` rather than estimated, because a decision
taken on an invented number is worse than a decision deferred.

---

## Summary

| # | Decision | Blocks | Urgency |
|---|---|---|---|
| 1 | The homepage says the FTA is in effect. It is not. | Nothing technical. It is wrong today | **Immediate** |
| 2 | Where the system lives after the placement, and who owns those accounts (F4) | Handover, not M1 | Medium |
| 3 | Named reviewer for AI-drafted output | Anything the Digest or Comms Assistant would publish | **This week** |
| 4 | Member Jungle: retain, integrate or replace (F1) | Member portal, membership and CRM, sponsors | High |
| 5 | Website editor: classic Editor or Wix Studio (F5) | The entire website rebuild | High, and irreversible later |
| 6 | Identity and login model (F3) | Every login-gated page, and SIP's separation of duties | Medium |

---

## 1. The homepage states the FTA is in effect

**Status: factually incorrect today.**

The live homepage reads:

> With the New Zealand–India Free Trade Agreement now in effect, INZBC members gain first-mover
> advantage through trade intelligence, policy access and business networks.

The agreement is **not in effect**. MFAT lists it as concluded but not yet in force. INZBC's own
verified source corpus, which the FTA Explainer answers from, already records the correct position:

> Signed 27 April 2026. Negotiations concluded 22 December 2025. Not yet in force, awaiting
> domestic ratification in both countries. Benefits are agreed and apply once the agreement enters
> into force, not as current access.

**Why this one is listed first.** It is the cheapest to fix and the most damaging to leave. INZBC's
standing rests on being the authority on this relationship. Being wrong about the status of the
agreement it exists to explain is the kind of error a sceptical export head or a journalist checks
first, and it undercuts every other claim on the page.

**Suggested replacement wording**

> The New Zealand–India Free Trade Agreement was signed on 27 April 2026 and is progressing toward
> entry into force. INZBC helps businesses prepare now, through trade intelligence, policy access
> and trusted networks.

Adding a visible status line with a "last verified" date and a link to the MFAT page would make the
currency itself a credibility signal rather than a liability.

**Why the team has not fixed it.** It is an edit to the live site. Publishing rights sit with the
account owner, and the agreed rule is that the live site is not touched by the team.

**Decision:** approve the wording, or supply your own, and confirm who applies it.

Recorded as issue #234.

---

## 2. Account ownership after the placement

**Correction to an earlier version of this pack.** This section previously said milestone M1 was
blocked on a billing decision. That was wrong, and the error was ours: ADR-0004 was amended on
27 July to record INZBC's zero-cost constraint, deferring the paid hosting option entirely. The
deployment runs on free tiers with no payment method, so **nothing about M1 waits on INZBC.**

What remains is not urgent and is not about spend.

**The question.** The system currently runs on free-tier services and a GitHub organisation. After
the placement ends, INZBC holds it. Accounts registered to an individual are a system INZBC does
not control, and the team leaves in twelve weeks.

Needed:

1. An INZBC-owned account for each service the system depends on, rather than an individual's.
2. A named owner for each, so there is a person to ask when something stops.

**Cost of leaving it open.** Nothing stops today. It becomes a problem at handover, and the cost of
fixing it then is higher than the cost of setting it up now, because credentials and data have to
move rather than simply being created in the right place.

**One genuine running cost.** Model API usage is the only recurring charge, and it is accepted as
such. Everything else is free tier.

**What free tiers cost instead of money**, recorded honestly: the API sleeps after about 15 minutes
of inactivity and takes close to a minute to wake. Fine for a demo that is warmed beforehand, poor
for an unattended session. If INZBC later wants that removed, it becomes a paid conversation about
a system it has already used, which is the better time to have it.

**Recommendation.** Create the accounts under an INZBC identity now, while there is nothing to
migrate.

Recorded as issues #93 and #214.

---

## 3. Named reviewer for AI-drafted output

Every AI-drafted output requires a **named human reviewer** before it can publish. That is INZBC's
own commitment from the proposal, and the system enforces it: there is no path that distributes
anything without a recorded approval, and production stays disabled until one exists.

The rule is built. The person has not been named.

**Cost of leaving it open.** The Trade Intelligence Digest and the Communications Assistant cannot
reach production at all. Not "should not" — the gates refuse, by design.

**What the role involves.** Checking that each output is supported by its cited sources, that
nothing unverified has crept in, and recording the approval. It is a judgement role, not a
technical one.

**Recommendation.** Name a primary and a backup. A single named reviewer becomes a single point of
failure the first week they are on leave.

Note one related matter: the SIP launch configuration currently assigns the same person as both
Primary Analyst and CEO approver. The system allows a recorded exception for this, naming the
approver, the reason and a review date, because in a small organisation the same person genuinely
holds both roles. It needs to be recorded as a deliberate exception rather than left as an
oversight.

**Decision:** name the reviewer and backup, and approve the separation-of-duties exception.

Recorded as issue #96.

---

## 4. Member Jungle: retain, integrate or replace

**Foundation decision F1.**

Member Jungle currently provides membership applications, approvals, member records, renewals,
online payments, invoices, member communications, event functions, restricted documents, data
exports and audit records.

| Option | Description | Main benefit | Main risk |
|---|---|---|---|
| **A** | Retain Member Jungle, link to it from the rebuilt site | Lowest risk, keeps every existing function | Two environments, separate login |
| **B** | Retain as system of record, integrate selected data | Preserves operations, better reporting and experience | Integration effort, cross-border data controls |
| **C** | Replace with Wix pricing plans plus an internal CRM | More control inside one environment | High migration, payment, renewal and consent risk |
| **D** | Replace with a dedicated association platform | Strongest long-term model | Highest cost and procurement effort |

**Cost of leaving it open.** The member portal, the membership and CRM module and the sponsors
module are all held. That is the largest block of unstarted work in the programme.

**Recommendation: A now, B as the direction.** The reasoning is timing, not a judgement about the
platforms. Replacing a system that already runs payments, renewals, invoicing and consent, during a
16-week engagement that is also launching the intelligence platform and rebuilding the website,
spends the remaining weeks on a migration instead of on the four modules INZBC selected.

**The part worth knowing:** under A or B the team can start the CRM work immediately, because what
it would build is the relationship data Member Jungle does *not* hold — prospects, sponsors,
government contacts, agencies, delegation participants, media, universities. Under C or D it
becomes a migration project. So closing this is worth doing even if the answer is "retain for now".

Full assessment, including the seven facts still needed from INZBC:
[`membership/member-jungle-assessment.md`](membership/member-jungle-assessment.md).

**Decision:** choose A, B, C or D, and set a review date.

Recorded as issues #95 and #231.

---

## 5. Website editor: classic Editor or Wix Studio

**Foundation decision F5. This is the one with a door that closes.**

Both `inzbc.org` and the staging duplicate run on the **classic Wix Editor**. Wix Studio is the
newer professional editor, and it offers design tokens, custom CSS, custom breakpoints and a
modern responsive canvas. The classic Editor offers none of those and works to a fixed 980-pixel
canvas, which is why the current homepage image softens on large screens.

External advice recommended switching to Studio immediately. Checking that against Wix's own
documentation found three things that change the decision:

1. **A Studio branch requires a Premium plan** on the site being built. The staging duplicate is on
   the Free plan, so the switch as described cannot be performed today.
2. **Design and content do not carry over.** Pages are recreated by hand. It is a rebuild, not a
   conversion.
3. **Publishing a Studio branch is one-way.** It automatically unpublishes the Editor version, and
   the Editor version cannot be republished afterwards.

Point 3 matters most. The agreed cutover plan assumes go-live is recoverable. On the Studio route
it is not.

**What is genuinely true about the timing.** Because design carries over on neither route, anything
built on staging now is discarded if Studio is chosen later. Nothing has been built yet. So this
is the cheapest moment to decide, which is the one part of the external advice that holds.

| | Stay on classic Editor | Move to Studio |
|---|---|---|
| Cost | None | Premium plan on the build site `[[cost]]` |
| Design ceiling | 980px canvas, no tokens, no custom CSS | Modern responsive, tokens, custom CSS |
| Go-live | Reversible via Site History | **Irreversible** |
| Rebuild effort | Pages built once | Pages built once, same effort |

**No recommendation offered.** This is a genuine trade between design quality and reversibility,
with a cost attached, and it is a business judgement rather than a technical one. The team can
execute either. What it should not do is start building before the answer, because that work is
thrown away.

Full analysis: [`website-rebuild-plan.md`](website-rebuild-plan.md).

**Decision:** Editor or Studio. If Studio, confirm the Premium plan.

Recorded as issue #233.

---

## 6. Identity and login model

**Foundation decision F3.**

Which service controls identity for public members, staff, board members, administrators and
service accounts.

**Cost of leaving it open.** Every login-gated page waits on it. It also gates the separation of
duties inside the intelligence platform: analyst, reviewer, approver and administrator have to be
distinguishable identities before an approval record means anything.

This interacts with decision 4. If Member Jungle is retained, member identity most likely stays
there and this decision narrows to staff and administrator identity only.

**Recommendation.** Take this after decision 4, because that answer removes most of the question.

**Decision:** defer explicitly until F1 is settled, or name the identity service now.

Recorded as issue #213.

---

## What the team is doing in the meantime

Work chosen because it holds whichever way these land:

- Hardening the FTA Explainer service so it is ready to deploy the moment decision 2 is answered.
- The FTA content model: sector pages, and the tariff data with a verification date on every entry.
- Accessibility and search structure for the rebuild, which apply on either editor.
- The security, privacy and data groundwork the programme needs before any real member data moves.

Not started, deliberately: any page building on either editor, and any membership build.

---

## Approval

| Decision | Answer | Name | Date |
|---|---|---|---|
| 1. FTA status wording | | | |
| 2. Account ownership after handover | | | |
| 3. Named reviewer and backup | | | |
| 4. Member Jungle: A / B / C / D | | | |
| 5. Editor or Studio | | | |
| 6. Identity model | | | |

---

## Related

- [Project charter](project-charter.md) — scope, phases and the foundation decisions
- [Member Jungle assessment](membership/member-jungle-assessment.md) — decision 4 in full
- [Website rebuild plan](website-rebuild-plan.md) — decision 5 in full
- [Programme brief](inzbc-ai-operating-system.md) — the nine-part system and its phase gates
