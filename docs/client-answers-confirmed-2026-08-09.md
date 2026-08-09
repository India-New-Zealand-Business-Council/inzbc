# Confirmed answers from Sunil — 9 August 2026

**Status: CONFIRMED by the Executive Sponsor**, relayed by Bhanu from a live conversation on
9 August 2026. This is the first block of answers in this project that is not `PROPOSED`.

These supersede the matching `PROPOSED` and `OPEN` rows in
[`client-answers.md`](./client-answers.md) and close the corresponding board items. Where an
answer changes something already built, the change is named rather than left implied.

Relayed rather than written by Sunil directly, so treat wording as the team's record of his
decision. Anything that later proves misheard is corrected here, not argued about.

---

## The four foundation decisions

### F1 — Membership platform: **retain, and integrate if the API allows**

Sunil offered his own Member Jungle account. **We declined that deliberately**: using a personal
login would put his credentials in the team's hands and break the separation of duties the whole
SIP approval model rests on.

**Agreed instead:** INZBC asks Member Jungle for **API access and documentation**, with an
integration user rather than a person's login. If an API exists, we integrate — the site reads the
directory and gated content from Member Jungle, which stays the system of record. If it does not,
we retain and link out, which is what the site does today.

Either way **membership is not rebuilt**, so BR9 (one system of record per data type) holds.

- Unblocks: #95, and #46 to the extent that identity allows.
- Next action: draft the API request for INZBC to send Member Jungle.

### F2 / F3 — Identity: **Microsoft 365 exists but is effectively unused**

Sunil has Microsoft 365. In practice **only he logs in**. Other people involved with INZBC
generally create their own Member Jungle accounts instead.

So identity splits in two:

- **Staff and administrative identity** — Microsoft 365, currently a single active user.
- **Member identity** — Member Jungle, self-registered.

**A consequence worth stating plainly.** SIP's separation of duties assumes the analyst who
captures, the reviewer who checks and the approver who releases are *different people*. With one
active account that is impossible, and an approval trail signed by one person proves nothing about
independence.

**Resolved:** SIP will have **Sunil plus one or two staff** (see below), which is enough for a real
separation between capture and approval. If that does not materialise, the controls still exist in
code but are exercised by one person, and the handover pack must say so rather than implying a
control that was never tested.

- Unblocks: #213.

### F4 — Budget: **no paid infrastructure. Free tier, deploy now**

Sunil asked, reasonably, why cloud hosting is needed at all. The answer given: the website is on
Wix and needs nothing, but SIP is a server application — a Postgres database holding runs,
candidates, approvals and the audit log, an API the review screens call, and a scheduled collection
job. None of that can run inside Wix.

**But it does not have to cost anything.** Free tiers cover the engagement: Render free tier for the
API, a free managed Postgres, GitHub Actions for the schedule.

**Decision: deploy to free tiers now.** No INZBC card, no billing owner, no ceiling required. The
cold-start delay on a free tier is accepted for a demo.

Paid hosting becomes a real question only if INZBC runs this in production after handover, which is
a post-handover decision and not a blocker now.

- Unblocks: **#99 (first deployment)**, and removes #93 as a blocker for this engagement.
- ADR-0004's deferral of Cloud Run stands and is now the settled position rather than an interim one.

### The AI model API — **key already held by INZBC**

The OpenAI key is already in the project secrets as an INZBC-held credential, so the one genuine
running cost is already on the right account. No transfer needed at handover for this item.

Still true, and unchanged: the gateway fails closed without a key rather than fabricating output.

---

## Named people

### AI-drafted output reviewer: **Sunil Kaushal**

Every AI-drafted output is approved by Sunil before release. This is the name the fail-closed gate
was waiting for.

- Unblocks: #96. `production_enabled` can move once the launch approval is recorded.
- **Still open:** no deputy named. If Sunil is unavailable, approvals stall and nothing publishes.
  Worth returning to, but it does not block build.

### SIP users: **Sunil plus one to two staff**

Enough for genuine separation of duties. Specific names not yet supplied.

- Next action: get the names so roles can be seeded into the `users` table.

---

## Content and facts

### FTA sectors: **goods first, services second**

The three conflicting lists (#219) are resolved by scope rather than by picking one, because the
lists are different kinds of thing. Sunil's ten are broad sectors; the corpus is organised by
**tariff outcomes** — the specific things the agreement changes.

Sunil asked whether honey was included. **It is** — Mānuka honey is already sourced and in
`apps/fta/corpus.py`, along with wool, wine, seafood, forestry, sheepmeat, kiwifruit and apples,
cherries/avocados/blueberries/persimmons, dairy across four lines, and coal.

**Agreed:**

1. **Build now** on the goods sectors already sourced.
2. **Add next**, sourced from the agreement text before publication: **tourism, education,
   investment**.
3. Defence and security, immigration and sports are **not** dropped, but are not sourced yet and do
   not gate the build.

Nothing is written about a sector until it has a source, per BR2.

- Unblocks: #219, #185, #186, #187, #194.

### Two-way trade figure: **NZ$3.95bn confirmed**

`trade-stats.html` and `apps/fta/corpus.py` keep **NZ$3.95bn**, MFAT-sourced for the year ended
December 2025. The migration guide's `$3.68b` is superseded — it is a June document and the corpus
figure is later and sourced.

This closes the conflict recorded in `ARCHITECTURE.md` §2 and the one PR #28 was pulled up on.

### Homepage leads with the FTA

Confirmed. The live site leads with Events; the rebuild leads with the FTA. This is the intended
repositioning and the most visible change a stakeholder will notice.

### The live homepage FTA error: **fixed**

The homepage previously stated the FTA was "now in effect". Sunil has corrected it. The agreement
was signed 27 April 2026 and awaits ratification in both countries.

- Closes: #234.

---

## Tools and subscriptions

### Email: **EmailOctopus**

INZBC uses EmailOctopus, not Mailchimp.

**Scope deliberately limited:** the newsletter archive links out to EmailOctopus, and that is all.
**SIP will not send through EmailOctopus yet** — Sunil wants the digest properly tested first, and
integration is a later step once there is confidence in the output.

That is the right call and it matches the fail-closed posture: a distribution path that does not
exist cannot be triggered by mistake.

- Next action: obtain the archive URL. No API key needed for now.

### Zoho Backstage: **in use for events**

INZBC uses Zoho Backstage. Event pages link out to Zoho for registration, as the migration guide
§7 step 7 specifies. Registration is **not** rebuilt on Wix.

- Next action: Bhanu to supply the per-event Zoho URLs so the event cards stop being placeholders.
- **Still open:** whether Zoho Backstage overlaps Member Jungle's event functions, and whether INZBC
  is paying for both. Feeds the licence register (#204).

### Wix Premium: **main site has it; the build site does not**

`inzbc.org` is on a Premium plan. The Studio site we are building is a separate free site. INZBC
expects to buy Premium for it **after the work is done**, not before.

Consequences, both already worked around:

- **Custom elements stay unavailable**, so pages render through Embed Code driven by page code. The
  20 built React bundles remain in `react-elements/` unused.
- **No custom domain** until Premium, so the demo runs on the `wixstudio.com` URL.

---

## Brand

### Palette: **the purple and green set, confirmed**

The brand palette in `docs/design-decisions.md` is confirmed: navy `#160933` base, purple `#61145f`,
forest `#1b4640`, lime `#b8f07c`, tangerine `#f05b29` for CTAs, lavender `#c1acfb`.

**This corrects a change made earlier the same day.** The site had been switched to the *live site's*
colours (indigo `#1B1464`, gold `#F8C70C`) on the reasoning that the live site was authoritative.
That was wrong: the live site is the thing being replaced, and `design-decisions.md` records what
INZBC specified, including usage percentages. The build now defaults to `purpleGreen` in
`scripts/build-sections.js`, with the live and provisional sets kept switchable behind
`INZ_PALETTE`.

Contrast re-measured against the confirmed set — all pairs pass AA except white on tangerine
(3.37:1), which is why navy on tangerine (5.56:1) is the specified CTA pairing. That exception was
already documented and still holds.

The provisional bicultural palette (Deep Navy / Marigold / Teal) is **not adopted**.

### Typography: **unresolved, flagged**

Bhanu's instruction was to revert to Big Shoulders per `design-decisions.md`. In parallel, the
studio-site build has moved to **Poppins** and added a build-failing check that rejects
Big Shoulders, Merriweather and Impact.

**These conflict.** Not resolved here, and deliberately not resolved by one side silently
overwriting the other. Needs a single decision, then one change across `design-decisions.md`,
`build-sections.js` and `site-head.html` together.

---

## Delivery scope

**Full scope retained.** The risk was put to Bhanu — 5.4 weeks of build to 13 September against an
estimated 8–10 weeks of remaining work — with a recommendation to drop modules 2, 3, 4, 5 and 9 to
specification only, which is the charter §6 position anyway.

**Bhanu's decision: build them.** Recorded as an informed choice, not an oversight. The consequence
is that either the build window extends past 13 September or some modules land partially complete.

---

## Still open after this conversation

| # | Item | Needed from |
|---|---|---|
| 1 | Member Jungle API access and documentation | INZBC → Member Jungle |
| 2 | Names of the one or two SIP staff users | Sunil |
| 3 | A deputy approver for AI output | Sunil |
| 4 | Per-event Zoho Backstage URLs | Bhanu |
| 5 | EmailOctopus archive URL | Sunil |
| 6 | Which of the 154 blog posts matter | Sunil |
| 7 | Sources for tourism, education, investment | Team, from the agreement text |
| 8 | Typeface: Big Shoulders or Poppins | Bhanu |
| 9 | Member count, membership tiers and fees, patron details | Sunil |
| 10 | Whether Zoho and Member Jungle duplicate event functions | INZBC |
| 11 | Finance Owner and Privacy Owner for the Phase 1 gate | Sunil |
| 12 | Post-capstone platform owner | Sunil |
