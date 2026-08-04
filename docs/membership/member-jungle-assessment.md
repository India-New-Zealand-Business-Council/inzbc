# Member Jungle: retain, integrate or replace

**Status: assessment, not a decision.** Foundation decision F1 belongs to INZBC. This exists so that
deciding is cheap: the options, the criteria, the evidence each one needs, and what follows from
each. It does not decide, and a recommendation here is not an approval.

**Why it is worth doing now.** F1 blocks module 2 (member portal), module 3 (membership and CRM)
and, through the relationship data model, module 4 (sponsors and trade services). It is the single
decision standing in front of the largest block of unstarted work in the programme. Nothing else
unblocks that much.

The four options are from the [programme brief](../inzbc-ai-operating-system.md) §4. This adds the
criteria to judge them against and the facts still missing.

---

## 1. What Member Jungle already does

From the client's Digital System Overview, supplied 3 August 2026. Not verified against the running
system, which is the first gap below.

Membership applications · approvals and member records · renewals · online payments and invoices ·
member communications · event functions · restricted documents · data exports · audit records.

That list matters because it is the replacement cost. Options C and D do not just move a member
table; they take on payments, invoicing, renewals, consent and audit.

---

## 2. Criteria

Weighted toward what is expensive to get wrong rather than what is pleasant to have.

| # | Criterion | Why it decides anything |
|---|---|---|
| C1 | **System of record clarity** | One authoritative store per data type. Any option that leaves the member register in two places fails outright, whatever else it scores |
| C2 | **Migration risk** | Members, payment history, invoices, renewal dates and consent. A partial migration is worse than none, because reconciliation lands on a staff of about five |
| C3 | **Payments and invoicing continuity** | Renewals in flight during a cutover are the highest-consequence failure. A member charged twice, or not at all, is a membership conversation not a support ticket |
| C4 | **Privacy and cross-border processing** | Where member data is stored and processed, and whether that is disclosed. Privacy Act 2020 applies regardless of which platform wins |
| C5 | **Total annual cost** | Licence, transaction fees, support. An earlier review found more than NZ$7,000 in annual subscriptions with overlapping functions, so consolidation is part of the point |
| C6 | **Member experience** | One login or two. Real, but it ranks below C1 to C4: a second login is an irritation, a duplicated register is a defect |
| C7 | **Operability by INZBC after handover** | The team leaves after 16 weeks. An option only a developer can run is not viable at this size |
| C8 | **Exit cost** | Whether the data can be got out again. Choosing a platform you cannot leave is a decision about the next decision too |

---

## 3. The options against the criteria

Assessment, with the reasoning stated so it can be argued with.

| | A — Retain and link out | B — Retain as record, integrate | C — Replace with Wix + internal CRM | D — Replace with a dedicated platform |
|---|---|---|---|---|
| C1 system of record | Clear. Member Jungle owns it | Clear, if integration is one-directional | At risk. Wix Pricing Plans plus a CRM is two stores unless carefully designed | Clear, once migrated |
| C2 migration risk | None | Low, no member data moves | **High** | **Highest** |
| C3 payments | Unchanged | Unchanged | High risk during cutover | High risk during cutover |
| C4 privacy | Existing posture, `[[to confirm]]` | Adds a data flow to assess | New posture to establish | New posture to establish |
| C5 annual cost | `[[current cost to confirm]]` | Current cost plus integration effort | Wix plan plus CRM licence plus build | Highest; procurement required |
| C6 member experience | Two environments, separate login | Improved, single entry point from the site | Single environment | Single environment |
| C7 operability | Already operated by INZBC | Mostly, integration needs monitoring | Needs developer support | Vendor-supported |
| C8 exit | Exports exist | Exports exist | Unclear | Contractual |

**Assessment:** A and B are the only options that do not put payments and consent through a cutover
during a 16-week placement. B is A plus integration work, so A is reachable now and B is where A
grows. C and D are viable positions for INZBC to hold, but not on this timeline and not while the
SIP launch and website rebuild are both in flight.

This matches the brief's preliminary recommendation. It is not new; what is new is the criteria the
recommendation can be checked against.

---

## 4. What INZBC must supply to complete this

The assessment cannot be finished without these, and each is a fact only INZBC holds. Left as
placeholders rather than estimated.

| # | Needed | Blocks |
|---|---|---|
| 1 | `[[Member Jungle annual cost: licence, transaction fees, support]]` | C5 for every option |
| 2 | `[[Current member count, and how many are paid and current]]` | Migration sizing for C and D |
| 3 | `[[Where Member Jungle stores and processes data, and whether members were told]]` | C4, and the privacy assessment |
| 4 | `[[Which Member Jungle functions INZBC actually uses]]`, against the list in §1 | Replacement cost. Paying for unused functions changes the answer |
| 5 | `[[Renewal cycle dates]]` | Any cutover has to avoid them |
| 6 | `[[Whether Zoho Backstage overlaps Member Jungle's event functions]]` | Ties to module 5; the overview says assess them together so INZBC stops paying twice |
| 7 | `[[Contract term and notice period]]` | C8, and whether the decision is even reversible this year |

Items 1, 4 and 6 come from the account and licence register (#204), so that work feeds this
directly.

---

## 5. What follows from each option

So the decision can be made against its consequences rather than in the abstract.

**If A or B:** module 2 becomes a gated shell linking out, which is what
[#217](../modules/member-portal.md) already delivered. Module 3 becomes a relationship database for
everything Member Jungle does *not* hold: prospects, sponsors, government contacts, agencies,
delegation participants, media, universities. It never holds the member register. Module 4 builds
on that same relationship store.

**If C or D:** module 3 becomes a migration project with payments and consent in scope, and the
website rebuild should not run concurrently with it. That is a scope conversation, not a build task.

Under A or B the team can start module 3 immediately, because the part it would build is the part
Member Jungle does not cover. That is the practical reason to close F1 early even if the answer is
"retain for now".

---

## 6. Recommendation

**Option A now, with B as the intended direction**, and revisit after handover once the register in
#204 shows the real cost.

The reasoning is the timeline, not a judgement about the platforms. Replacing a system that already
runs payments, renewals, invoicing and consent, during a 16-week placement that is also launching
SIP and rebuilding the website, spends the team's remaining weeks on a migration instead of on the
four modules INZBC selected. C and D may well be right for INZBC later; they are not right for the
period this team is here.

INZBC may reasonably decide otherwise. If it does, the scope conversation in §5 has to happen first.

---

## 7. Recording the decision

F1 is a foundation decision, so it needs recording rather than mentioning:

- the option chosen, and the date
- who decided, by name and role
- what evidence from §4 was available at the time, and what was still missing
- the review date, since "retain for now" is a position with an expiry

Until it is recorded, Member Jungle remains the **provisional** system of record and membership is
not rebuilt on Wix.

---

## Related

- [Programme brief](../inzbc-ai-operating-system.md) §4 — the four options and the interim position
- [Membership and CRM module](../modules/membership-crm.md) — module 3
- [Member portal module](../modules/member-portal.md) — module 2
- [Project charter](../project-charter.md) §11 — the four foundation decisions
