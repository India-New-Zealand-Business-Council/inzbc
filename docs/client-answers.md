# Client answers — proposed, pending INZBC confirmation

**Status of this document: none of it is confirmed by INZBC.** Every answer below was drafted by
the project team from public sources and reasonable inference. It is written down so that Sunil has
something concrete to correct rather than a blank list, which is faster for him and for us.

Read the status column before using anything here.

| Status | Meaning |
|---|---|
| `PROPOSED` | Drafted by us. Sunil confirms or corrects. **Not a sourced fact.** |
| `PUBLIC-SOURCE` | Taken from a public page or official statistic. Cite the source; still confirm currency. |
| `OPEN` | We have nothing. INZBC must supply it. |

`apps/site/content/*.md` draws on this file. Anything carried into content keeps a
`[[proposed — pending INZBC confirmation]]` marker until Sunil signs it off, because
`production_enabled` stays `false` and every member-facing line needs a named reviewer
([CLAUDE.md](../CLAUDE.md)).

Numbering matches the client-asks list so replies can be pasted straight back.

---

## A. First deployment

Superseded in part by [ADR-0004](decisions/0004-platform-graduation.md): INZBC has asked for a
zero-cost build, so the paid Cloud Run path is deferred and A2 no longer applies to the next
deployment.

| # | Answer | Status |
|---|---|---|
| A1 | All accounts, project ownership and data are INZBC-owned. Sunil is initial administrator. No student or contractor personal account holds anything of record. | `PROPOSED` |
| A2 | **Withdrawn.** INZBC has asked for no recurring cost. The staging stack is free-tier with no payment method, so there is no budget to set. Revisit only if Phase 2 needs paid hosting. | — |
| A3 | The INZBC GitHub organisation registers two OAuth apps, staging and UAT, both org-owned. Free. | `PROPOSED` |
| A4 | INZBC owns the system after the capstone. Sunil is initial System Administrator. Handover covers documentation, repositories, credentials, recovery procedures and account access. Without a named owner the recorded default is export, revoke and tear down. | `PROPOSED` |

## B. SIP pipeline and backup

| # | Answer | Status |
|---|---|---|
| B1 | Production model API usage bills to a dedicated INZBC-owned account, managed initially by Sunil. Developer accounts are for development only. **This is the one genuine recurring cost.** | `PROPOSED` |
| B2 | Free-tier equivalent of the original proposal: automated database backup on the managed Postgres free tier, plus a daily encrypted `pg_dump` written by a scheduled job to an INZBC-controlled location. No backup depends on a personal account. | `PROPOSED` |
| B3 | Maximum acceptable data loss (recovery point objective): **24 hours.** | `PROPOSED` |
| B4 | Maximum acceptable outage (recovery time objective): **24 hours, or one business day.** | `PROPOSED` |
| B5 | Restore owner: Sunil Kaushal as System Administrator. A trained secondary owner should be appointed before production. | `PROPOSED` |
| B6 | If the hosted system is unavailable, fall back to the approved SIP controlled workbook: source scanning, report preparation, reviewer checks and CEO approval run manually; distribute only to the authorised recipient; enter records after restoration, labelled as recovery entries. | `PROPOSED` |
| B7 | No restore has been tested. A test restore must be completed and recorded before hosted production begins. This does not block the workbook-based controlled launch. | `OPEN` |
| B8 | Sole authorised recipient: Sunil Kaushal, as CEO and SIP Owner. Distribution stays manual email during the controlled launch. | `PROPOSED` |
| B9 | Controlled launch approved through SIP-191 subject to recorded conditions; the launch pack moves to v1.0 Approved. Approval covers the five-day internal controlled launch only, not wider publication. | `PROPOSED` — **verify against the actual SIP-191 record before relying on this** |

## C. Build decisions

These are ours to propose; Sunil approves.

| # | Answer | Status |
|---|---|---|
| C1 | **Retain and integrate Member Jungle** as the membership system of record. No second membership register on the website. | `PROPOSED` |
| C2 | Use the INZBC Brand Guidelines 2026 — logos, palette, gradients, photography rules, typography. Fonts noted as Big Shoulders and Merriweather. | `PROPOSED` — brand kit not yet received |
| C3 | External: member records, renewals, directory and event registration (Member Jungle); newsletter distribution (Mailchimp). Internal: public site content, FTA Explainer, SIP workflow and records, approval and audit. | `PROPOSED` |
| C4 | **Mailchimp** for newsletters, delivery kept outside the website. Confirm it holds the current newsletter contact list and engagement history before migration. | `PROPOSED` |
| C5 | **Link** to the Member Jungle directory. Do not copy or embed a separate directory database. | `PROPOSED` |
| C6 | Member Jungle is the normal event registration platform. Zoho only where a major event needs functions Member Jungle cannot provide. | `PROPOSED` |
| C7 | External registration via Member Jungle. No second native event-registration form. | `PROPOSED` |
| C8 | "Our Patron" sits in **About** — it is an organisational leadership role, not a commercial partnership. Link to it from Partners. | `PROPOSED` |
| C9 | Primary AI content reviewer: Paras. Backup: Roshan. Final publication approval: Sunil Kaushal. Nothing AI-drafted publishes automatically. | `PROPOSED` — **Sunil must name this; it is a governance requirement** |

## D. Organisation and website information

> **Everything in section D concerns real people, real prices and real partners.** None of it is
> confirmed. Treat each row as a question with a suggested answer attached.

### People and organisation

| # | Answer | Status |
|---|---|---|
| D1 | **Read from [inzbc.org/executive-council](https://www.inzbc.org/executive-council) on 27 July 2026.** Board: Edwin Paul (Chair), Tony Martin (Deputy Chair), Bharat Chawla (Treasurer), Antje Fiedler, Prince Kumar, Jonathan Manuel, Rachel Lynch, Jenny McGregor, Sumant Khedkar (Board Members). Executive team: Sunil Kaushal (Chief Executive), Sreedhar Venkatram (Mumbai Chapter Head), Kanwaljit Singh Bakshi (Ex-Officio), Dr Pushpa Wood (Wellington Chapter Head), Bharat Joshi (Delhi Chapter Head), Clive Antony (Strategic Communications Officer), Michael Henstock (Christchurch Chapter Head), Sandeep Sharma (Strategy and Trade Officer). Bios and photos migrate from that page. | `PUBLIC-SOURCE` — Board confirms currency before publication |
| D2 | **Read from [inzbc.org/our-patron](https://www.inzbc.org/our-patron) on 27 July 2026.** Patron: **Bhav Dhillon**. Managing Director of Cemix and Dunlop Drymix; former Honorary Consul of India in Auckland; Chair of the Indian Weekender, Kiwi Indian Hall of Fame and the "There's a Better Way" Foundation; former Chair of Foundation North. **The page states no appointment date**, so the "Patron since 2023" claim is unsupported. | `PUBLIC-SOURCE` — appointment date `OPEN` |
| D3 | Public-facing wording: **"more than 200 members"**. Do not publish an exact figure until a current Member Jungle report is produced — earlier records disagree. | `PROPOSED` |
| D4 | Draft milestone list from 1988 onward: founding, sustained FTA advocacy from the mid-2000s, past and current Patrons, the 25th anniversary summit, the India delegation and expanded India presence, FTA conclusion, and business engagement around the Indian Prime Minister's visit. **Dates and events to be checked against INZBC records.** | `PROPOSED` |
| D5 | INZBC is a member-based, independent, not-for-profit incorporated society governed by its Executive Council under its constitution. Purposes include informing government on trade matters, sharing information on doing business between India and New Zealand, and supporting member business development. | `PUBLIC-SOURCE` — current constitution or approved governance summary still needed (`OPEN`) |

### Claims we could not source

| # | Answer | Status |
|---|---|---|
| D6 | Replace the unsupported "majority of delegations" claim with: *"Since 1988, INZBC has hosted and supported numerous government, business and sector delegations between India and New Zealand."* | `PROPOSED` — drafting suggestion, safe because it asserts nothing countable |
| D7 | Replace the unsourced "300,000" with the Stats NZ 2023 Census count for the Indian ethnic group, cited and linked. **Could not verify the figure: the Stats NZ summaries tool renders its data in JavaScript and returned no numbers, and the direct 2023-census URL 404s.** So no number is recorded here. Any long-range projection is shown separately and never as the current population. | `OPEN` — figure must be read off Stats NZ directly before publication |
| D8 | Use **"INZBC Summit"**. "India Unplugged Summit" appears in no sourced document. Do not use it unless INZBC confirms a rename. | `PROPOSED` |

### Membership and partners

| # | Answer | Status |
|---|---|---|
| D9 | A tiered annual fee structure exists covering student, individual, small business, MSME, educational institution, medium business and corporate in New Zealand, plus MSME and corporate for India. Fees exclude taxes and transaction charges. **Exact figures must come from the Member Jungle portal at publication time, not from this document.** | `OPEN` for exact figures |
| D10 | A five-level annual sponsorship structure exists for FY27. **Tier names, exact amounts, benefits and exclusivity terms must come from the final sponsorship prospectus.** | `OPEN` for detail |
| D11 | **Read from [inzbc.org/our-sponsors](https://www.inzbc.org/our-sponsors) on 27 July 2026.** Strategic Partners: BNZ; High Commission of India in Wellington; University of Auckland. Strategic Partner (Gold): Duco Consultancy. The page also shows unlabelled partner images with no identifying text, so the industry and government partner lists cannot be read from it. **Check against current signed agreements before migration** — showing a lapsed partner as current is a commercial problem. | `PUBLIC-SOURCE` — confirm currency; industry/government lists `OPEN` |
| D12 | No approved testimonials. Publish only attributed quotes with written consent. | `OPEN` |
| D13 | No approved member spotlight. Select a member, obtain written consent, confirm the story. | `OPEN` |

### Contact details

| # | Answer | Status |
|---|---|---|
| D14 | **Read from [inzbc.org/connect](https://www.inzbc.org/connect):** `sunil@inzbc.org`. The page also states "We prefer e-mail contact". | `PUBLIC-SOURCE` |
| D15 | Use the same address as the Secretariat contact until a dedicated `secretariat@inzbc.org` exists. | `PROPOSED` |
| D16 | **No phone number appears on the live contact page.** Keep the site email-first, matching its stated preference. | `PUBLIC-SOURCE` (absence verified) |
| D17 | **Read from [inzbc.org/connect](https://www.inzbc.org/connect) on 27 July 2026:** PO Box 20092, Glen Eden, Auckland 0641, New Zealand. | `PUBLIC-SOURCE` — confirm current |
| D18 | **Read from [inzbc.org/connect](https://www.inzbc.org/connect) on 27 July 2026:** X/Twitter `twitter.com/inzbc`; Facebook `facebook.com/inzbc`; LinkedIn `linkedin.com/company/india-new-zealand-business-council`; YouTube `youtube.com/channel/UC9MQW-VliLqOdT4GUktKfZQ`; Flickr `flickr.com/photos/inzbc`. **Flickr is still linked on the live site** — decide whether it carries over rather than assuming it is dead. | `PUBLIC-SOURCE` — confirm current |

### FTA Explainer

| # | Answer | Status |
|---|---|---|
| D19 | Priority order for coverage: primary industries first (wool, wine, seafood), then technology and services, education, tourism, investment, fintech, sports diplomacy. Specialist subjects follow only where official material supports reliable answers. | `PROPOSED` |
| D20 | A disclaimer is already implemented in code (`apps/fta/standards.py`, `AI_INFORMATION_STANDARD`) and carried on every answer. **The ask is approval of the existing wording, not new wording.** An alternative shorter draft is available if Sunil prefers it. | `PROPOSED` |
| D21 | Heading: *"New Zealand–India FTA Explainer."* Intro: *"Get clear, source-backed information about what the New Zealand–India Free Trade Agreement may mean for your sector. Each answer links to official sources and shows when the information was checked. If a reliable answer cannot be verified, the Explainer will say so and direct your enquiry to INZBC."* | `PROPOSED` |

### Events

| # | Answer | Status |
|---|---|---|
| D22 | Carry over all five annual event reports (2017–2021) into a Past Events archive rather than the About page. | `PROPOSED` |
| D23 | Feature **three** upcoming events on the homepage, with a link to the full calendar. | `PROPOSED` |

## E. Later sign-offs

| # | Answer | Status |
|---|---|---|
| E1 | Foundation decisions: membership platform — retain and integrate Member Jungle; internal platform — free-tier hosting now, paid hosting revisited only when Phase 2 stores member data ([ADR-0004](decisions/0004-platform-graduation.md)); identity — INZBC-controlled GitHub OAuth, separate staging and UAT apps; budget and ownership — INZBC owns all accounts and data, and the build carries no recurring infrastructure cost. | `PROPOSED` |
| E2 | The new site retains `inzbc.org`. Before cutover: record the live site's Site History version and export CMS collections where applicable (Wix offers no complete external site backup, so "full backup" is not an instruction anyone can carry out), UAT complete, all account and integration details recorded, and written cutover approval from Sunil. | `PROPOSED` |
| E3 | Client acceptance session as recorded in the plan. Sunil attends, with the named reviewer; the team participates where backup roles are tested. | `PROPOSED` |
| E4 | Provider addresses are fine for development, staging and assessment. Production: `inzbc.org` public, and a subdomain for the internal SIP platform. | `PROPOSED` |

---

## Still needed from INZBC

Nothing above is settled until Sunil confirms it. These are the items where we have **nothing at
all** and no amount of drafting helps:

1. **A named reviewer for AI-drafted content** (C9) — governance requirement, currently unowned.
2. **Brand kit** (C2) — logos, palette, typography, approved photography.
3. **Exact membership fees** (D9) and **sponsorship tiers and benefits** (D10).
4. **Current constitution or approved governance summary** (D5).
5. **Confirmation that listed partners are current** (D11).
6. **Approved testimonials** (D12) and a **member spotlight with written consent** (D13).
7. **A tested backup restore** (B7) before hosted production.
8. **Member Jungle direction confirmed in writing** (C1).
9. **Post-capstone owner named** (A4) — without it, the recorded default is tear-down.
