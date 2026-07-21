# New Site — Page Specs (Phase 1 → 2 bridge)

Per-page content specs for the new INZBC site, derived from the IA and audit in
[discovery.md](./discovery.md). These define what each page contains so the Phase 2 scaffold
can be built directly. Tone: executive, data-driven, politically neutral.

Conventions:
- **Source** = `carry-over` (exists on inzbc.org, rewrite for new tone) / `new` / `INZBC input`
  (content we must request, do not invent).
- `[[placeholder]]` marks anything requiring sourced material — never fill with invented
  facts, names, or figures.
- External integrations (Member Jungle, Mailchimp/eocampaign) are linked, not rebuilt.

---

## 1. Home
- **Purpose:** Position INZBC as NZ's premier India-trade body; route visitors to Join,
  Events, Trade Resources, Digest.
- **Sections:** Hero (one-line positioning + primary CTA); credibility strip (est. 1988,
  `[[member count — confirm current figure]]`, recognised by both governments); featured
  Events; latest Digest teaser; Trade Resources entry (incl. FTA Explainer); sponsors strip.
- **Primary CTA:** Join INZBC. **Secondary:** Read the latest Digest.
- **Source:** carry-over (rebuild). Hero copy `INZBC input` / drafted for review.

## 2. About
- **Purpose:** Mission, history, governance credibility.
- **Sections:** Mission; history since 1988 (`[[milestones — confirm dates/events]]`);
  what INZBC does (advise government, share knowledge, facilitate business development);
  **Executive Council** (board + executive/chapter heads, each photo/title/bio/LinkedIn).
- **Source:** carry-over. **Executive Council names/bios pulled live from INZBC at build
  time — never from crawler output (guardrail: never invent board names). See discovery OI-6.**

## 3. Events
- **Purpose:** Drive attendance; archive past events; showcase the INZBC Summit.
- **Sections:** Upcoming events (cards: title, date, venue, register link); Event Calendar;
  Past events / reports (2017–2021 reports exist — confirm which carry over); INZBC Summit feature.
- **Primary CTA:** Register / RSVP (mechanism `[[confirm — native form vs external ticketing]]`).
- **Source:** carry-over. Note: `/events` slug 404'd on the live site — confirm real URLs (OI-4).

## 4. Trade Resources
- **Purpose:** Hub for trade tooling and the FTA Explainer entry point.
- **Sections:** Overview; Trade Bazaar; Trade Shows; **FTA Opportunity Explainer** launch card
  (links to / embeds page 7); downloadable reports (e.g. India Report, Apr 2023).
- **Source:** carry-over + expand. FTA Explainer card is `new`.

## 5. Members
- **Purpose:** Show the membership base; convert prospects.
- **Sections:** Value proposition; **Member Directory** (alphabetical, source of truth is
  Member Jungle); membership tiers + fees (`[[new fee structure from 1 Jan 2026 — request final tiers/pricing]]`);
  how to join.
- **Primary CTA:** Join Now → **external Member Jungle** (`inzbc.memberjungle.club`).
- **Source:** carry-over (external). Decision (OI-7): embed/iframe the directory vs link out.

## 6. Trade Intelligence Digest — NEW
- **Purpose:** Weekly LLM-summarised, human-reviewed digest of India–NZ trade news + archive.
- **Sections:** Latest issue (summary cards with source citations); **Archive** (filter by
  date/topic); "how it's produced" note stating the human-review step for trust.
- **Publishing gate:** renders **only** items with CMS `status = published`; a named reviewer
  approves drafts before they appear (see ai-service-architecture.md). Reviewer name = OI-5.
- **Primary CTA:** Subscribe (routes to existing newsletter platform, `[[confirm Mailchimp vs eocampaign]]`).
- **Source:** new. Content produced by the digest pipeline; never auto-published.

## 7. FTA Opportunity Explainer — NEW
- **Purpose:** Guided, sourced assistant explaining how the NZ–India FTA affects a member's
  sector (tariffs, market access, next steps).
- **Sections:** Intro + scope/disclaimer; guided input (sector/product); sourced answer with
  **citations to official FTA material**; "next steps" + contact INZBC CTA.
- **Guardrail:** answers cite an approved corpus only; never invents tariff lines or FTA terms.
  Source corpus scoping is a separate task (`[[FTA source list — official MFAT/govt docs]]`).
- **Source:** new. Embedded on Trade Resources via iframe/custom element (Option B).

## 8. News Centre / Newsletters
- **Purpose:** Publications archive and news.
- **Sections:** News posts; **Kia Ora India** quarterly; monthly newsletters (archive links out
  to email platforms today); reports library (India Report, etc.).
- **Decision:** whether to host a proper on-site publications library vs continue linking to
  email campaigns (OI-7). **Source:** carry-over.

## 9. Connect / Sponsors
- **Purpose:** Contact + sponsor recognition.
- **Sections:** Contact form (First/Last name, Email, Subject, Message); details
  (`[[confirm current preferred contact + PO Box]]`); socials (X, LinkedIn, Facebook, YouTube,
  Flickr); **Sponsors** by tier with logos/links; **add a "Become a sponsor" CTA** (missing today — opportunity).
- **Source:** carry-over + small addition.

---

## Global
- Header nav: Home · About · Events · Trade Resources · Members · Digest · News · Connect
  (FTA Explainer surfaced under Trade Resources; Join persistent in header).
- Footer: contact, socials, membership, sponsors, privacy (NZ Privacy Act 2020).
- Every AI-surfaced page (Digest, FTA Explainer) carries a visible note that content is
  human-reviewed / sourced — trust is the product for this audience.

## Open content requests to INZBC (blockers to finalising copy)
- Current member count and key history milestones (Home, About).
- Final membership tiers + pricing (new structure from 1 Jan 2026).
- Executive Council names/bios/photos from the live source (OI-6).
- Named content reviewer for Digest/FTA (OI-5).
- Which publications/reports carry over; hosting vs link-out decision (OI-7).
