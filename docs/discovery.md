# INZBC Digital Platform — Phase 1 Discovery

Status: in progress (Discovery, placement Wk 1–2)
Delivery: AIC / Otago Polytechnic internship — Bhanu Gupta, Roshan Aryal, Paras
Client: India New Zealand Business Council (INZBC), NZ India-trade body since 1988

This is a **new, separate site build** (confirmed by client), not an edit of the live
Wix site at https://www.inzbc.org/. The live site is not to be touched without separate
explicit sign-off.

---

## Confirmed scope — four modules

1. Website & Content Refresh — **full new/separate site build** (upgraded from the
   proposal's lighter "refresh key pages" — see Open Item OI-3).
2. FTA Opportunity Explainer — guided, sourced assistant on how the NZ–India FTA affects
   a member's sector (tariffs, market access, next steps).
3. AI Communications Assistant — Claude-powered drafting (newsletters, event
   announcements, LinkedIn, member spotlights). **Adversarial/security tested before staff use.**
4. Trade Intelligence Digest — automated weekly digest from evaluated public India–NZ
   sources, LLM-summarised, **human-reviewed before publication**. Digest page + archive.

Explicitly **out of scope**: AI Readiness Reports (not selected).

---

## Current site audit — inzbc.org (first pass)

Platform: **Wix** (confirmed via `static.wixstatic.com` assets + Wix URL patterns — verified, not assumed).

Page-by-page audit (crawled):

| Current page | New-site decision (draft) | Content & findings |
|--------------|---------------------------|--------------------|
| Home | Rebuild | New IA, exec-level tone |
| About Us | Carry over + rewrite | Est. 1988; "premier NZ trade organisation"; **160+ members** across agriculture, dairy, finance, education, infrastructure; recognised by both governments; 25th anniversary May 2014. Links to Event Reports (2017–2021). |
| Executive Council | Carry over | Board (~9) + Executive/Chapter-head team (~8), each with photo, title, bio, LinkedIn. **Names/bios must be pulled directly from the live source at build time — do NOT reuse crawler output (unverified, may be stale/hallucinated).** See OI-6. |
| Events | Carry over | `/events` slug returned **404** — nav label maps to a different slug (Event Calendar / past-events). Confirm real URLs. INZBC Summit + past/upcoming. |
| Trade | Carry over + expand | Trade Bazaar, Trade Shows → becomes Trade Resources hub; FTA Explainer entry point. |
| Member Directory | Carry over | Alphabetical list, last updated 4 Nov 2024, grows over time; "contact secretariat if missing"; no search/filter today. |
| Join INZBC | Carry over (external) | **New fee structure from 1 Jan 2026.** "JOIN NOW" redirects to external platform **`inzbc.memberjungle.club`** (Member Jungle). Membership managed off-site. |
| Newsletters | Carry over | Archive May 2019–Sep 2023; each links out to external email platforms (**eocampaign1.com, mailchi.mp**). *Kia Ora India* quarterly embedded in newsletters (not standalone PDFs). India Report "Ready For Its Next Phase" (Apr 2023). No on-site signup. |
| Connect | Carry over | Contact form (First/Last name, Email, Subject, Message). Email: Sunil@inzbc.org. PO Box 20092, Glen Eden, Auckland 0641. Socials: X @inzbc, Facebook, LinkedIn, YouTube, Flickr. |
| Our Sponsors | Carry over | Sponsors by tier w/ logos + descriptions + links (Strategic Partners incl. gold tier; Industry/Govt partners). **No "become a sponsor" CTA** — opportunity to add. |
| News Centre | Carry over | Feeds into / sits alongside new Digest. |

### External integrations to account for (not native to a new Wix build)
- **Member Jungle** (`inzbc.memberjungle.club`) — membership join/management + directory source of truth.
- **Email campaign platforms** — eocampaign1.com and Mailchimp for newsletters; new site links out rather than hosting.
- **Publications** — *Kia Ora India* + India Report live inside email campaigns, not as site-hosted PDFs — may want a proper site-hosted publications library.
- These shape how much the new site *owns* vs *links to*, and directly affect the Digest/Newsletter integration in Phase 3.

---

## Proposed new information architecture

- **Home**
- **About** (mission, history since 1988, Executive Council)
- **Events** (calendar, upcoming/past, INZBC Summit)
- **Trade Resources** (existing Trade Bazaar/Shows + FTA Explainer entry point)
- **Members** (directory, Join/membership)
- **Trade Intelligence Digest** (weekly digest page + **archive**) — NEW
- **FTA Opportunity Explainer** — NEW (guided sourced assistant)
- **News Centre / Newsletters** (Kia Ora India, monthly newsletters, reports)
- **Connect / Sponsors**

The three AI modules (Comms Assistant, FTA Explainer, Digest pipeline) are **code +
external services** — Wix cannot host a RAG backend or a scheduled digest pipeline
natively. Architecture decision pending: how the Wix presentation layer integrates with
the AI service layer (embed / iframe / API).

---

## Build order (per placement timeline)

- **Phase 1 — Discovery (Wk 1–2):** this document — IA, page map, content audit.
- **Phase 2 — Build 1 (Wk 3–6):** site scaffold + AI Communications Assistant
  (RAG-backed). **Explicit adversarial/security review step before staff use — not skipped.**
- **Phase 3 — Build 2 (Wk 7–11):** FTA Explainer, Trade Intelligence Digest (with archive),
  integration between AI tools and the site.
- **Handover (Wk 14–16).**

---

## Content & governance standards

- Executive-level tone: professional, data-driven, politically neutral. No AI clichés,
  no unsubstantiated claims. Audience: Ministers, diplomats, exporters, CEOs.
- Never invent statistics, board names, or FTA details — only official/sourced material.
- Every AI-drafted output (digest, explainer, comms) requires a **named human reviewer**
  step before publishing (explicit proposal commitment — do not silently automate past it).
- Public sources + material INZBC provides only. NZ Privacy Act 2020 applies.

---

## Open items / risk register

| ID   | Item | Owner | Status |
|------|------|-------|--------|
| OI-1 | **Wix build tooling not connected.** Sunil granted the *team* access to the INZBC Wix account, but the Wix MCP is still not connected in this build environment (confirmed: no Wix tools available). The team can create/build the new site in the Wix editor now; for programmatic build, connect the Wix MCP (`claude mcp add --transport http wix <url> --headers …`). | Team | Blocking programmatic build |
| OI-2 | **Domain: RESOLVED.** Sunil confirmed the site keeps the **inzbc.org** address. Plan: build a new, separate Wix site in the existing account, then point inzbc.org at it at go-live (cutover). No new domain or DNS purchase needed. | Client | Resolved |
| OI-3 | **Scope/vision outreach started** — message 1 sent to Sunil asking his vision for the new site. Full written scope confirmation pending his reply. | Team | In progress |
| OI-4 | Page-by-page audit done except `/events` (404 on that slug — confirm real Events/Calendar URLs). | Team | Mostly done |
| OI-5 | Named human reviewer for AI-drafted content to be designated. | Client/Team | Open |
| OI-6 | Executive Council names/bios must be sourced from live site or INZBC directly at build time — never from crawler/LLM output (guardrail: never invent board names). | Team | Open |
| OI-7 | Confirm what stays external vs on-site: Member Jungle (membership/directory), Mailchimp/eocampaign (newsletters). Affects integration scope. | Client/Team | Open |
| OI-8 | **Go-live cutover touches the live site.** Same-domain means the new site replaces the current inzbc.org at launch. Before cutover: take a full backup/snapshot of the current site's content, and get explicit written go-live sign-off (guardrail: do not modify live inzbc.org without sign-off). Building the new site separately is fine; the domain switch is the sensitive moment. | Team/Client | Open (go-live) |
