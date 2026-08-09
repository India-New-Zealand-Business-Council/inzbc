# Wix rebuild: decisions and their sources

Resolves the `[[decision]]` markers in [`website-redirect-map.md`](website-redirect-map.md) and the
homepage statistics question. Researched against primary sources and comparable organisations on
31 July 2026.

Sunil's `INZBC_Website_Stocktake_Migration_and_Wix_Guide.docx` (7 June 2026) stays the requirements
backlog. It is not an authority for current facts: it predates the live site by seven weeks and
several of its figures come from an older reporting period. This file is the dated correction.

Decisions marked **INZBC** are commercial or governance calls that no amount of research settles.

## 1. Redirects

Two rules drive the table. Google treats many old URLs pointed at one generic destination as soft
404s when that destination does not carry their content, so a hub redirect for tidiness is a
mistake. And a URL that is already short and descriptive gains nothing from being redirected purely
to express hierarchy in its path, because site structure is understood from navigation and internal
linking, not path depth.

| Live URL | Decision | Why |
|---|---|---|
| `/connect` | **Keep** | Contact is a distinct top-level task, and `page-specs.md` retains Connect in the header. |
| `/executive-council` | **Keep**, under About in nav | Already descriptive. Hierarchy belongs in navigation, not the path. |
| `/our-patron` | **Keep**, under About, linked from Partners | Matches `client-answers.md` C8. |
| `/news` | **Keep** as the blog root | Short, meaningful, holds the whole archive. Label it Media in nav without touching the URL. |
| `/members` | 301 → `/membership` | The live page is an empty Wix "Items (All)" shell. |
| `/member-directory` | 301 → `/membership/directory` | Static gateway to Member Jungle, not a second directory. |
| `/member-profile` | 301 → `/membership/member-services` | Replaces the Wix dynamic profile with deep links. See section 3. |
| `/past-events` | 301 → `/events/past` | An archive hub is right, provided it links through to individual event records. |
| `/trade-news` | 301 → `/trade-missions` | This is the Trade Shows page despite the slug; `trade.md` combines missions and shows. |
| `/trade-shows` | 301 → `/trade-missions` | 404s today. Worth keeping to rescue historical inbound links. |
| `/india-x-nz` | 301 → `/events/boardroom-to-border-auckland-2025` | Its own date, venue, agenda, speakers and pricing. |
| `/copy-of-boardroom-to-border` | 301 → `/events/boardroom-to-border-christchurch-2025` | A distinct Christchurch event, not a duplicate despite the editor-generated slug. |

**Reversing an earlier recommendation.** The redirect map previously sent both Boardroom to Border
pages to `/events/past`. That was wrong: they are separate events with distinct content, and
collapsing them loses it. Comparable councils keep a past-events archive *and* permanent detail
pages, and Wix's own guidance is a list page plus a unique URL per event.

**Verify on staging before building:** Wix reserves `/events` when Wix Events is installed and the
classic editor may generate `/events-1/{Title}`. That changes the literal path, not the decision to
keep one URL per event.

## 2. Homepage statistics

The guide's four tiles do not survive contact with primary sources. Three of the four need changing.

| Guide tile | Decision |
|---|---|
| `$3.68b two-way trade` | Replace with **NZ$3.95bn, year ended December 2025** (MFAT key facts). |
| `95% of current NZ exports receiving tariff removal` | Fix the tense **and the denominator**: **95% of New Zealand's current exports to India will receive tariff elimination or reduction over time: 57% duty-free at entry into force, rising to 82%, with a further 13% receiving sharp cuts.** |
| `300,000 strong Indian diaspora` | Replace with **292,092 people identified with the Indian ethnic group, 2023 Census** (Stats NZ). |
| `India middle class growth story` | Replace with **NZ$7bn two-way trade by 2030**, labelled an aspiration. |

**$3.68b was not invented.** It is MFAT's own figure for the year ended June 2025, from the February
2026 economic impact assessment. It is six months older than the $3.95bn series, not wrong. Worth
saying because the repo has been treating it as a suspect number.

**Two things are wrong with that tile, not one.** The denominator first: "95% of NZ exports" reads
as 95% of New Zealand's exports to the world. The figure is 95% of New Zealand's current exports
**to India**. `apps/fta/corpus.py:132` already states it correctly, with the phasing; the homepage
must not state it more broadly than the corpus does.

**And the tense.** The FTA was signed 27 April 2026 and is **not yet
in force**; MFAT still lists it under agreements concluded but not in force. "Receiving" states as
current something that has not happened. `apps/fta/corpus.py` already gets this right, both in its
status line and in phrasing outcomes as "at entry into force", and the FTA Explainer attaches that
status line to every answer. The homepage must match.

**Do not splice the Indian-side figure in.** India's Department of Commerce frames it as 70.03% of
Indian tariff lines covering roughly 95% of bilateral trade. That is a different denominator from
MFAT's "current NZ exports" and the two must not be combined into one claim.

**This resolves `client-answers.md` D7**, which recorded no diaspora number because Stats NZ's
summaries tool would not render one. The figure is 292,092, for the Indian ethnic group, 2023
Census, and people may identify with more than one ethnic group. MFAT itself uses "300,000-strong
diaspora", so the rounded form is defensible as policy shorthand, but the census measure is more
transparent and is what we should publish.

Every tile carries its period and links a source note. On staging an unresolved figure may show a
`[[placeholder]]`; on the public homepage, omit the tile instead.

## 3. Member portal

**Interim position for the staging build: a public Wix shell with deep links to Member Jungle. No
Wix member roles, membership status, renewal dates, invoices, directory preferences or corporate
seats.**

This is what to build on staging now. It is **not** a resolution of the retain/integrate/replace
question, which `PROJECT-RULES.md` reserves to INZBC and which `member-portal-spec.md` still records as
open along with authentication, SSO and directory integration. In particular, **do not apply the
`/member-profile` redirect in production**: that route is member-gated today, and pointing it at a
public page before the privacy and Member Jungle decisions are made would expose a members-only
path. Redirect it on staging only, and revisit at cutover.

This is what comparable organisations do. The British Chamber of Commerce Singapore keeps profiles,
directory consent, membership details, corporate seats, events and payments in its membership SaaS
and presents a branded member-services page. The ASEAN New Zealand Business Council sends the
operational journey to Glue Up. ASAE's guidance is that a custom portal integrates existing CRM data
rather than reproducing it, and uses SSO to cross the boundary.

Member Jungle already provides membership details, renewals, invoices and primary-member group
administration. Rebuilding those displays on Wix adds no authority, only a second copy.

| Wix may hold | Member Jungle must own |
|---|---|
| Public membership value proposition and confirmed tiers | Login, password, account recovery |
| Public member and sponsor spotlights, with consent | Person and organisation records |
| Public events, news, trade resources | Membership status, expiry, renewal |
| Static `/membership/member-services` with deep links | Invoices, receipts, payment history |
| Static `/membership/directory` gateway | Directory records and visibility consent |
| Forms that create no membership record | Corporate primary contacts and seats |

What breaks if Wix displays copied CRM data: renewal drift grants access to former members or blocks
newly renewed ones; invoice and seat state diverges; directory consent changed in one system stays
exposed in the other; and the second store attracts its own Privacy Act accuracy, security and
retention obligations.

**Wix native SSO needs Wix Studio Enterprise or Wix Channels and supports only OpenID Connect.**
There is no public documentation confirming Member Jungle can act as an OIDC identity provider. That
has to come from the vendor in writing, not be assumed.

**INZBC decides:** retain, integrate or replace (#95); whether member-only content justifies the
integration cost; and whether to fund Wix Enterprise or an external identity layer.

## 4. Blog taxonomy

**Decision: adopt the guide's six categories, one primary category per post, and preserve all 154
post slugs.**

FTA Insights (FTA text, implementation, tariff and market access) · India Market Updates (Indian
market, sector and regulatory developments not primarily about the FTA) · INZBC News (announcements,
governance, partnerships, media statements) · Events (invitations, programmes, post-event records) ·
Reports (substantive publications and research) · Commentary (attributed analysis, clearly separated
from official news).

Six siblings is within the normal range; the risk is overlap between labels, not the count. Use tags
rather than more categories for upcoming/past, city, sector, trade show and delegation facets.

**Recategorising does not change a post's URL.** Wix keeps the post slug in a separate SEO field
from its categories, and deleting a category does not delete its posts. Editing the slug does change
the URL and needs a 301. Renamed or removed *category* landing pages need redirects too; do not
assume Wix's automatic page-redirect behaviour covers blog routes.

**Do not prune by age.** Review each post and decide retain, revise, remove or archive. Comparable
councils keep old news and event records permanently. Mark past events as past and disable expired
registration calls to action. Remove only exact duplicates, privacy-problematic material, or
genuinely misleading thin promotions. Where something is removed and has a real replacement, 301 to
it; otherwise return 404 rather than redirecting everything to News.

## 5. Live-site facts that must not be carried across

Found while checking the guide against the live site. Each would otherwise migrate as though true.

1. **The Event Calendar is not current.** `/upcoming-events` still lists 2020 events with expired
   registration links, while the blog carried a June 2026 event. Rebuild from current data.
2. **The member directory is a 4 November 2024 snapshot** and says so. Carrying it into Wix as if
   current would breach the one-system-of-record rule.
3. **No membership prices exist anywhere sourced.** The live Join page announces a new structure from
   1 January 2026 with no amounts. No fee may be reconstructed from an old screenshot.
4. **The About copy contradicts itself**, saying both "over 25 years" and "since 1988", and claims
   "over 160 members" against the proposed "more than 200". Neither figure is confirmed.
5. **The footer says "© INZBC 2025"** in August 2026. Use a generated year.
6. **"India Unplugged" is real.** The repo currently says the name could not be found; the live
   archive has an India Unplugged export/import workshop, a Wellington edition, and a 2019 article
   describing Summit 2019 as part of the India Unplugged Series. What is unverified is whether
   "India Unplugged Summit" was ever the formal event title. Do not erase the brand or assert a
   rename without INZBC records.
7. **The 7 June content snapshot is already stale.** A post was added on 11 June. The 31 July
   inventory is the migration baseline, refreshed once more at cutover.

## 6. Still with INZBC

None of these can be resolved by research or by us.

- Retain, integrate or replace Member Jungle (#95).
- Final navigation: whether Connect stays top-level, and where Patron sits. Sources conflict.
- Whether "India Unplugged" is a current brand, a retired one, or a formal event title.
- Current membership prices and the current member count.
- Whether Reports has enough material to be its own category.
- The two-way trade figure to publish, if they prefer their own over MFAT's.
