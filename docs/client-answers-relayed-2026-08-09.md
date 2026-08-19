# Answers relayed from Sunil — 9 August 2026

**Status: RELAYED, and mixed.** Sunil answered verbally; Bhanu relayed the answers; this document
is the team's record of that conversation. There is no transcript, no client-written confirmation
and no signature in the repository, so **nothing here is independent evidence of a client
decision.** The board comments that cite this document were written by the same person who relayed
it, which is corroboration in a circle, not verification.

Each item below is tagged:

| Tag | Meaning |
|---|---|
| `CLIENT ANSWER` | Sunil said this. Still relayed, not written by him |
| `TEAM DECISION` | The team decided this, in light of what he said |
| `TEAM INTERPRETATION` | The team's reading. **Needs his confirmation** |
| `REPO FACT` | Verified against the repository, independent of the conversation |
| `OPEN` | Still unanswered |

Items marked `TEAM INTERPRETATION` should be put back to Sunil in writing before anything depends
on them.

**Corrected 9 August 2026** after an adversarial review found the first version of this document
overstated several answers as settled. The corrections are marked inline. Issues #213 and #219 were
reopened as a result.

These supersede the matching `PROPOSED` and `OPEN` rows in
[`client-answers.md`](./client-answers.md) — though that file has **not yet been updated row by
row**, so it still shows the older `PROPOSED` status in places.

---

## The four foundation decisions

### F1 — Membership platform: retain; integration proposed, not agreed

`CLIENT ANSWER` — Sunil offered his own Member Jungle account, and said retaining Member Jungle
is acceptable.

`TEAM DECISION` — **We declined the account offer.** A personal login in the team's hands would
break the separation of duties the SIP approval model rests on, and would leave his credentials
with us.

`TEAM INTERPRETATION` — **needs his confirmation.** In place of the login we propose INZBC asks
Member Jungle for **API access and documentation** with an integration user. If an API exists we
integrate, with Member Jungle staying the system of record; if not, we retain and link out as
today.

**This was the team's pre-existing recommendation** (`docs/client-decision-pack.md`), not something
Sunil proposed. Recording it as "agreed" in the first version of this document overstated what he
said. He agreed to *retain*; the integration route is ours to put back to him.

`REPO FACT` — `docs/modules/membership-crm.md` and `client-answers.md` still describe Member Jungle
as provisional and decision-gated. Those are not yet updated.

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

`TEAM INTERPRETATION`, **and the first version of this document was wrong to call it resolved.**

It said "Sunil plus one or two staff" is "enough for genuine separation of duties". Two people
cannot cover three roles — capture, review and approval — without one person holding two of them.
That is a smaller claim than the document made, and #266 already concedes that without names the
separation stays nominal.

**#213 has been reopened.** What it asked for is still outstanding:

- which service authenticates the *application* — ADR-0004 still selects organisation-owned GitHub
  OAuth, not Microsoft 365, and that conflict is unresolved
- named, distinct accounts for analyst, reviewer, approver and administrator
- service accounts
- role assignment, and enforcement

`REPO FACT` — `database/schema.sql` records decision-level separation of duties as **not enforced
yet**. ADR-0005 binds separation to roles and permits single-principal operation only through a
recorded exception. So the control is designed, not operating.

### F4 — Budget: **no paid infrastructure. Free tier, deploy now**

Sunil asked, reasonably, why cloud hosting is needed at all. The answer given: the website is on
Wix and needs nothing, but SIP is a server application — a Postgres database holding runs,
candidates, approvals and the audit log, an API the review screens call, and a scheduled collection
job. None of that can run inside Wix.

**But it does not have to cost anything.** Free tiers cover the engagement: Render free tier for the
API, a free managed Postgres, GitHub Actions for the schedule.

**Decision: deploy to free tiers now.** No INZBC card, no billing owner, no ceiling required. The
cold-start delay on a free tier is accepted for a demo.

Paid hosting becomes a real question only if INZBC runs this in production after handover.

- Unblocks: **#99 (first deployment)**, and removes #93 as a blocker for this engagement.

**Correction.** The first version said ADR-0004's free-tier position "is now the settled position
rather than an interim one". `REPO FACT`: ADR-0004 says the opposite — it leaves the managed-Postgres
provider and region **unconfirmed**, and expressly calls free-tier hosting *an interim position*
whose limits change without notice. `render.yaml` currently deploys only the FTA slice, which
touches no database.

So the zero-cost constraint is confirmed and deployment is unblocked, but **free-tier feasibility
end to end is not proven** until a no-card Postgres provider and region is named and tested.

### The AI model API — **key already held by INZBC**

`CLIENT ANSWER` / relayed — Bhanu reports the OpenAI key is already held as an INZBC credential, so
the one genuine running cost is on the right account.

**Not verifiable here.** The only configuration in this repository is an empty `.env.example` entry.
Whose account the live key belongs to cannot be checked from the repo, so this stays a report rather
than a fact until someone confirms it in the provider console.

`REPO FACT` — the gateway does fail closed: a missing `OPENAI_API_KEY` raises
`GatewayNotConfiguredError` (`services/api/model_gateway.py`), with a direct test in
`apps/sip/core/tests/test_model_gateway.py`. It will not fabricate output.

---

## Named people

### AI-drafted output reviewer: **Sunil Kaushal**

Every AI-drafted output is approved by Sunil before release. This is the name the fail-closed gate
was waiting for.

- Unblocks: #96. `production_enabled` can move once the launch approval is recorded.
- **Still open:** no deputy named. If Sunil is unavailable, approvals stall and nothing publishes.
  Worth returning to, but it does not block build.

### SIP users: Sunil plus one to two staff

`CLIENT ANSWER` — Sunil expects one or two staff to use SIP alongside him.

`OPEN` — **this does not establish separation of duties**, and an earlier version of this document
said it did. Capture, review and approval are three roles; two people cannot hold three without one
person doubling up. No names have been supplied, so no roles can be seeded.

`REPO FACT` — `database/schema.sql` states decision-level role separation is not enforced by the
schema, and that unrecorded self-approval is not yet refused. The control is designed, not
operating. See the reopened #213.

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

- Unblocks: #185, #186, #187, #194.

**#219 stayed open after this decision, and has since been reconciled.** The scope decision alone
did not close it, because #219 asked for the three conflicting lists to be *reconciled in the same
change* — and at the time of writing they still disagreed: `apps/fta/corpus.py` named its list
`PROVISIONAL_SECTORS_IN_SCOPE` pending INZBC confirmation, and `docs/fta-source-corpus.md` and
`docs/requirements.md` both still recorded the scope as awaiting INZBC. Adding a fourth statement of
scope without updating those three is the exact failure #219 exists to prevent.

`REPO FACT`, re-checked 13 Aug 2026 — all three now agree with this document: `corpus.py` names the
list `SECTORS_IN_SCOPE` (no longer provisional), `apps/fta/README.md:11` and
`docs/fta-source-corpus.md`'s member-facing mapping both cite it as settled 9 Aug 2026 under #219,
and `docs/requirements.md:305` strikes the open question through as resolved by scope rather than by
a single list. Nothing in the tree still describes the sector list as awaiting INZBC.

`REPO FACT` — the corpus product list checks out. All named entries exist in `apps/fta/corpus.py`,
are `confirmed=True`, and carry MFAT National Interest Analysis citations. Note the code spells it
`Manuka honey` without the macron.

### Two-way trade figure: **NZ$3.95bn confirmed**

`REPO FACT` — the value, period and MFAT attribution check out in `apps/fta/corpus.py` and
`docs/fta-source-corpus.md`. The migration guide's `$3.68b` is superseded: it is a June document and
the corpus figure is later and sourced.

Two corrections to the first version:

- It cited `trade-stats.html` without a path. The file is at
  `docs/wix-studio-snippets/trade-stats.html` and **does** exist on `main`. (A later correction
  claiming it was absent was itself wrong — it was looked for at the repository root.)
- `apps/site/content/home.md` and `trade.md` still say "NZ$3.95bn annually" **without the period**.
  The figure is for the year ended December 2025; "annually" is not the same claim. That wording
  still needs fixing.

### Homepage leads with the FTA

Confirmed. The live site leads with Events; the rebuild leads with the FTA. This is the intended
repositioning and the most visible change a stakeholder will notice.

### The live homepage FTA error: **reported fixed**

The homepage previously stated the FTA was "now in effect". **Sunil reported that he has corrected
it.** The agreement was signed 27 April 2026 and awaits ratification in both countries.

Not verified from the repository — no post-fix check, screenshot or log exists here. Worth loading
the page once to confirm before treating #234 as done.

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

`CLIENT ANSWER` — Sunil confirmed the purple-and-green palette.

`REPO FACT`, and a correction: `docs/design-decisions.md` lists **eight** colours, not six. The
first version of this document omitted Blue `#261866` and Crimson `#7e0030`. The full set is navy
`#160933`, blue `#261866`, purple `#61145f`, crimson `#7e0030`, tangerine `#f05b29`, forest
`#1b4640`, lavender `#c1acfb`, lime `#b8f07c`.

That file also says the usage percentages are **indicative** — the source wording totals 105% — and
that tangerine-as-CTA is a team design choice still needing Sunil's confirmation. Neither caveat
survived into the first version of this document.

**This corrects a change made earlier the same day.** The site had been switched to the *live site's*
colours (indigo `#1B1464`, gold `#F8C70C`) on the reasoning that the live site was authoritative.
That was wrong: the live site is the thing being replaced, and `design-decisions.md` records what
INZBC specified, including usage percentages. The build now defaults to `purpleGreen` in
`scripts/build-sections.js`, with the live and provisional sets kept switchable behind
`INZ_PALETTE`.

**Contrast — the first version's claim was wrong and this matters.** It said "all pairs pass AA
except white on tangerine".

The two quoted figures are right: white on tangerine **3.37:1** (fails), navy on tangerine
**5.56:1** (passes). But "all other pairs pass" is false.

Across white plus **all eight** palette colours, **20 of 36 pairs fail** the 4.5:1 normal-text
threshold. (Restricted to white plus the six colours the earlier version named, it is 11 of 21 —
the smaller figure quoted before, which understated the problem by leaving blue and crimson out.)
Examples: white on lime 1.33:1, white on lavender 1.99:1, navy on purple 1.58:1, purple on tangerine
3.51:1, forest on tangerine 3.12:1, lime on lavender 1.50:1.

That does not mean the palette is unusable — those are pairs nobody would set body text in. It
means **the safe pairings have to be stated explicitly** rather than assumed. Correct statement:
navy on tangerine passes and is the CTA pairing; white body text on tangerine fails. A full
foreground/background matrix is owed before any broader claim.

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
| 13 | Written confirmation of every `TEAM INTERPRETATION` above | Sunil |
| 14 | Reconcile the three FTA sector lists in one change (#219) | Team |
| 15 | A no-card Postgres provider and region, named and tested | Team |
| 16 | Full contrast matrix for the eight-colour palette | Team |
| 17 | Row-by-row update of `client-answers.md` to point here | Team |
| 18 | Fix "NZ$3.95bn annually" → "year ended December 2025" in `home.md` and `trade.md` | Team |
