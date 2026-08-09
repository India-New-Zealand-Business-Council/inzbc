# Website rebuild: the plan, and what the research got wrong

Written 4 August 2026 against two external research documents. Their analysis is largely sound and
some of it is very good. Their headline recommendation is not executable as written, and the reason
matters enough to lead with.

Everything here is scoped to the **staging duplicate**. The live `inzbc.org` site is not edited,
and no redirect work is proposed for search-ranking reasons.

---

## 1. What I verified, and what I did not

Claims were checked rather than accepted. This matters because both documents contain a mix of
things that are checkable, things that are vendor-sold, and things that are simply asserted.

### Verified by direct query

| Claim | Verdict | Evidence |
|---|---|---|
| `inzbc.org` runs classic Wix Editor, not Studio | **True** | Site API: editor type `Editor`, created 18 Feb 2019, Premium, custom domain, Velo enabled |
| The staging duplicate is also classic Editor | **True** | Site API: editor type `Editor` |
| Multiple other sites sit in the account | **True** | `inzbc-website-old`, `inzbc-summit`, and two summit copies |
| The homepage says the FTA is "now in effect" | **True, and it is wrong** | Fetched: "With the New Zealand–India Free Trade Agreement now in effect…" |
| Footer reads © 2025 | **True** | Fetched: "© INZBC 2025 \| All Rights Reserved" |
| Kia Ora India is described as quarterly, latest issue Dec 2023 | **True** | Fetched |

### Not verified, and treated accordingly

- **Performance figures** ("6.8s average LCP", "Lighthouse 35 to 55", "38KB saved, 320ms LCP
  improvement"). Every one of these comes from a firm selling migrations or performance work. The
  underlying constraint is real, the numbers are marketing. Not used as planning inputs.
- **Specific Google announcement dates** for AI-search guidance and FAQ rich-result deprecation.
  Plausible, uncited beyond the claim itself, and nothing in the plan depends on them.
- **Wix Harmony's existence and limits.** Irrelevant either way: nobody proposed building on it.

---

## 2. The finding that actually governs the plan

Both documents say: move to Wix Studio, and do it now before more work accumulates.

**The staging duplicate cannot be switched to Studio.** A Studio branch of a Wix Editor site
requires a **Premium plan**. The staging duplicate is on the **Free** plan. The instruction as
written has no execution path.

Two further facts from the same Wix documentation change the shape of the decision:

**Design and content do not carry over.** "The design of the Wix Editor site is not carried over to
the Studio branch." Pages, elements and written content are recreated by hand. A Studio branch is
not a conversion; it is a rebuild that happens to share business data.

**Publishing a Studio branch is one-way.** Publishing it automatically unpublishes the Editor
version, and "once you publish the Studio branch, it is not possible to go back and republish the
original Wix Editor branch."

That last point is the one to sit with. The cutover plan in `discovery.md` OI-8 assumes the switch
is recoverable, with Site History as the fallback. On the Studio route it is not. Wix's own
mitigation is to duplicate the Editor site before publishing the Studio branch, which preserves a
copy but does not restore the live site.

### What survives from the research's argument

Its timing logic holds, for a reason it did not give. Because design does not carry over on either
route, **anything built on staging now is thrown away if Studio is chosen later**. We have built
nothing on staging yet. So this genuinely is the cheapest moment to decide, even though the
mechanism is a rebuild rather than a switch.

### This is a new foundation decision

It has a budget consequence, an irreversibility consequence and a scope consequence, so it belongs
with F1 to F4 rather than in a backlog.

> **F5. Editor or Studio for the rebuild.**
> Staying on classic Editor accepts a 980px canvas, no design tokens, no custom CSS and no custom
> breakpoints. Moving to Studio requires a Premium plan on the site being built, means recreating
> every page by hand, and makes go-live irreversible: the Editor site cannot be republished
> afterwards.

Until F5 is decided, no page building happens on either. The work in §3 is deliberately chosen to
be worth doing whichever way it goes.

---

## 3. Work that is right regardless of F5

Ordered by value per hour, and none of it is wasted by either answer.

### 3.1 Content correctness, which is our own rule

**The homepage states the FTA is "now in effect". It is not.** The repository's own sourced corpus
records it as signed 27 April 2026 and awaiting domestic ratification, and every FTA Explainer
answer already carries that status line. So the live site contradicts the verified corpus this team
built.

This is not an SEO issue or a design issue. It is the exact failure `PROJECT-RULES.md` forbids: an FTA
detail stated without support, on the homepage of a body whose authority rests on FTA currency. A
sceptical export head who checks MFAT finds the Council wrong about the agreement it exists to
explain.

The rebuild must carry the corpus status line verbatim. **Correcting the live site is Sunil's call**
and is listed in §6.

### 3.2 The content model, which is the actual product

Both documents converge on the same conclusion from different directions, and it matches
`page-specs.md`: the FTA centre is the site's main product, and the research is trapped in the wrong
container.

India Report 2.0 and Kia Ora India exist only as Issuu embeds and PDF downloads. That is original
research, which is the strongest asset INZBC has, published in the least readable format available.
Publishing HTML versions with real headings, real figures as text, and charts as images with
descriptive alt does not depend on Editor or Studio. It is content work.

Sector pages should answer the five questions the second document proposes, because they are the
questions an exporter actually has: what changes at entry into force, who benefits, what to do now,
what risks remain, and which official document supports it.

This is where the effort belongs. Both documents agree, and so does our own module map.

### 3.3 Structured data, share images, headings, alt text

- No `og:image` or `twitter:image` while declaring `twitter:card` as `summary_large_image`. Link
  previews on LinkedIn, which is where INZBC actually posts, render arbitrarily. Cheapest fix on the
  list.
- No `H1` on the homepage; headings used for styling rather than meaning.
- Filename alt text on several homepage images. The blog does this correctly already, so the
  standard exists in the team and simply has not been applied backwards.
- `Organization`, `Event` and `Article` JSON-LD, hand written and verified in the Rich Results Test.

All of it is page-level work that transfers to whichever editor wins.

### 3.4 Information architecture

Both documents independently propose roughly the same six-item navigation, and both flag the same
three defects: events split across two top-level items, member directory absent from the nav, and
three competing membership routes.

The third is not a navigation problem. Three routes exist because **F1 is undecided** and the site
is hedging. Fixing the nav without deciding F1 just hides the ambiguity. The
[Member Jungle assessment](./membership/member-jungle-assessment.md) is what unblocks it.

---

## 4. Where I disagree with the research

**On React.** Both documents land on Studio plus custom elements, and the second is right that
React should not build the header, hero, cards or content pages. We already have a stronger reason
to keep React narrow: the FTA Explainer is a **deployed application** with its own API, corpus and
no-match guarantees, verified working. It does not need to become a Wix custom element to be
valuable, and embedding it would put the safety properties behind a boundary that is harder to test.
Link to it or embed the deployed app. Do not rebuild it inside Wix.

**On unpublishing the other sites.** `inzbc-website-old` and the old summit site are genuinely
competing copies of INZBC content. But unpublishing another published property is an outward-facing
change to the client's estate, and the two summit drafts may exist for reasons nobody has recorded.
This goes to Sunil as a recommendation, not a task we execute.

**On performance targets.** The Core Web Vitals thresholds are right and worth adopting. The
supporting numbers are not evidence. Measure our own build; do not plan against a migration firm's
averages.

**On "switch to Studio this week".** Covered in §2. It is not executable on staging, and the
irreversibility of the Studio cutover deserves a decision rather than a sprint.

---

## 5. Sequence

Nothing here starts page building before F5.

| Order | Work | Depends on | Lane |
|---|---|---|---|
| 1 | Put F5 to Sunil with the cost and the irreversibility stated | nothing | Client |
| 2 | Default share image, `H1`, alt text, heading structure on the rebuild spec | nothing | Product & UX |
| 3 | `Organization`, `Event`, `Article` JSON-LD blocks, verified in Rich Results Test | nothing | Product & UX |
| 4 | Content model for the FTA centre: sector pages answering the five questions | corpus | Intelligence & Data |
| 5 | HTML edition of India Report 2.0, PDF kept as download | INZBC supplying the source | Intelligence & Data |
| 6 | Page tree and navigation, six items | F5, F1 | Product & UX |
| 7 | Design tokens, type scale, spacing scale | F5 = Studio | Product & UX |
| 8 | Page build | F5 | Product & UX |

Steps 2 to 5 are real work available today. Steps 6 to 8 are blocked, and pretending otherwise is
how a rebuild ends up thrown away.

---

## 6. What only Sunil can decide

1. **F5, Editor or Studio.** Premium plan required for Studio; go-live becomes irreversible.
2. **The FTA status on the live homepage.** It is factually wrong today and contradicts the
   Council's own verified corpus. Correcting it is a live-site edit, so it is his.
3. **The other published sites.** `inzbc-website-old` (last updated March 2024, country set to
   United States) and `inzbc-summit` are live on `wixsite.com` addresses and read as INZBC content.
4. **Footer year, and the Kia Ora India cadence claim.** The site says quarterly and links a
   December 2023 issue as "latest". Either publish a current issue or change the label.
5. **F1**, which decides the membership route and therefore the navigation.

Items 2 and 4 are content accuracy, not design, and they undercut the FTA-currency argument the
homepage itself makes.

---

## Related

- [Wix staging readiness](./wix-staging-readiness.md) — what the duplicate supports
- [Wix rebuild decisions](./wix-rebuild-decisions.md) — the eleven resolved decisions
- [Page specs](./page-specs.md) — what each page contains
- [Member Jungle assessment](./membership/member-jungle-assessment.md) — F1
- [Project charter](./project-charter.md) §11 — foundation decisions
