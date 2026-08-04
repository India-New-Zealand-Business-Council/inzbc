# Wix Studio build spec

For the standalone Studio site at `inzbcsecretariat.wixstudio.com/my-site`
(id `040b006f-3745-4a4f-ae4d-03aedb08a7b1`), created 4 August 2026.

**This is hand work.** Wix exposes no REST API for creating or arranging pages, and none for the
URL redirect manager. Everything below is done in the Studio editor. The spec exists so the build
is mechanical rather than a series of judgement calls, and so two people building different pages
produce one site.

---

## 0. Before anything else

| # | Task | Why |
|---|---|---|
| 1 | Rename the site from `My Site` | It is the display name and it currently reads as a test site |
| 2 | Set region: **New Zealand**, **Pacific/Auckland**, **NZD**, language **en** | It is currently United States, New York and USD. Dates, currency and formatting all follow this. Dashboard only; there is no API for it |
| 3 | **Do not republish** until §5 is satisfied | The site is already published once, so a republish ships whatever has been saved. Saving is safe; publishing is the irreversible-feeling step |

---

## 1. What changed about the editor decision

Foundation decision **F5** was framed as classic Editor versus a Studio *branch* of the Editor
site. A branch requires a Premium plan on the site being built, which the staging duplicate does
not have.

**A standalone Studio site does not.** This one is on the Free plan. So the path is:

    build fresh in Studio  ->  point inzbc.org at it at cutover

Two things that do not change:

- **Design and content do not carry over** from the Editor site. This is a rebuild, not a
  conversion, whichever route is taken. That was always true and is the reason building on the
  staging duplicate was held.
- **The domain move still needs a Premium plan** on whichever site ends up live, and written
  go-live authority from the account owner.

The irreversibility warning attached to *publishing a Studio branch* does not apply here, because
this is not a branch. The Editor site remains independently publishable.

---

## 2. Design tokens

Set these as Studio global tokens on day one, not per page. That is the single biggest reason to
be on Studio at all: changing a brand value later becomes one edit rather than forty.

From `docs/design-decisions.md`, which transcribes INZBC Brand Guidelines 2026.

### Colour

| Token | Hex | Role |
|---|---|---|
| `navy` | `#160933` | Primary base and background, about half of all colour use |
| `blue` | `#261866` | Secondary base |
| `purple` | `#61145f` | Secondary base |
| `crimson` | `#7e0030` | Accent |
| `tangerine` | `#f05b29` | Accent, primary CTA |
| `forest` | `#1b4640` | Accent |
| `lavender` | `#c1acfb` | Accent |
| `lime` | `#b8f07c` | Accent |

**One accessibility rule that is not negotiable.** White body text on tangerine is **3.37:1**,
below the 4.5:1 AA minimum. Navy on tangerine is **5.56:1** and passes. So a tangerine button
carries navy text, never white. This is the mistake the current site makes and the reason it is
called out here rather than left to be caught in an audit.

### Type

- **Big Shoulders**, Medium to Bold: headings and short high-impact statements only. Uppercase for
  hero and section headings.
- **Merriweather**, Light to Medium: all body copy. Light for paragraphs.

Font files were not supplied with the brand kit. Both are available through Google Fonts; confirm
that matches what the guidelines intend before the site goes live.

Set a fluid type scale rather than fixed sizes. Cap body measure at 55 to 75 characters per line.

---

## 3. Page tree and slugs

Slugs are not free choices. They are the destinations in `docs/website-redirect-map.md`, and every
301 from the old site points at one of them. A slug invented during the build breaks a redirect
that was already decided.

| Page | Slug | Notes |
|---|---|---|
| Home | `/` | |
| About | `/about-inzbc` | `/about-us` 301s here |
| Executive Council | `/executive-council` | Kept, placed under About in the menu |
| Our Patron | `/our-patron` | Kept, under About, linked from Partners |
| Membership | `/membership` | `/join-inzbc` and `/members` 301 here |
| Join | `/membership/join` | `/membership-form` 301s here |
| Member directory | `/membership/directory` | Static gateway that links out to Member Jungle |
| Events | `/events` | `/upcoming-events` 301s here |
| Past events | `/events/past` | `/past-events` 301s here |
| Trade missions | `/trade-missions` | `/trade-shows` and `/trade-news` 301 here |
| India market opportunities | `/india-market-opportunities` | `/trade-bazaar` 301s here |
| FTA Centre | `/fta` | New. The Explainer's home |
| Insights: publications | `/insights/publications` | `/publications` 301s here |
| Insights: newsletters | `/insights/newsletters` | `/newsletters` 301s here |
| News | `/news` | Kept as the blog root, labelled Media in the menu |
| Partners | `/partners` | `/our-sponsors` 301s here |
| Connect | `/connect` | Kept |

**Nested slugs only survive if URL hierarchy flattening stays off.** It is off on the staging
duplicate; check it on this site before building `/membership/join` and `/insights/publications`,
because with flattening on they serve at `/join` and `/publications` and every nested redirect
misses.

### Navigation

Six items, no overflow. The current site runs nine plus a "More..." menu, and anything behind
"More..." is effectively invisible.

    About | Membership | Events | Trade & FTA | News | Contact

Persistent **Join INZBC** button, right-aligned, tangerine with navy text.

---

## 4. Content rules

- **Sourced material only.** Every figure comes from `docs/client-answers.md` or
  `docs/fta-source-corpus.md`. Nothing is written from memory or from the current live site, which
  contains errors.
- **Placeholders stay visible in the build** as `[[like this]]` and are the checklist for §5. They
  must never survive to a published page.
- **The FTA is not in effect.** It was signed 27 April 2026 and is awaiting ratification. The live
  homepage says otherwise and is wrong. Use the wording in `docs/client-decision-pack.md` §1.
- **Member counts:** "more than 200 members". No exact figure until a current Member Jungle report
  exists.
- **Executive Council and Patron:** from `client-answers.md` D1 and D2, which were read from the
  live site on 27 July. Confirm currency with the Board before publishing.
- **Accessibility, built in rather than audited:** one `H1` per page; headings that mean structure
  rather than size; real alt text on meaningful images and empty alt on decorative ones; visible
  focus states; no information carried by colour alone.
- **Each page needs** a search title, a meta description and an Open Graph image. The current site
  declares `twitter:card` with no image behind it, so link previews render blank.

---

## 5. Before the first republish

The site is already published. A republish ships whatever has been saved, so this is the gate.

- [ ] No `[[placeholder]]` remains on any page in the published set
- [ ] FTA status wording is correct and carries a verified date
- [ ] Every slug matches the redirect map
- [ ] URL hierarchy flattening is off; missing pages return 404, not 200
- [ ] One `H1` per page, alt text written, contrast checked on tangerine
- [ ] Region is New Zealand, Pacific/Auckland, NZD
- [ ] Site renamed from `My Site`
- [ ] Named human reviewer has approved the content (`client-answers.md` C9)
- [ ] Editor session logged in `docs/wix-changes-log.md`

Cutover is separate and later: it needs a Premium plan on this site, the 301s entered by hand, and
written go-live authority.

---

## Related

- [`design-decisions.md`](design-decisions.md) — brand tokens and their source
- [`page-specs.md`](page-specs.md) — what each page contains
- [`website-redirect-map.md`](website-redirect-map.md) — every slug and its inbound 301
- [`website-rebuild-plan.md`](website-rebuild-plan.md) — why the build was held, and F5
- [`client-answers.md`](client-answers.md) — the sourced facts
- [`wix-changes-log.md`](wix-changes-log.md) — where every editor session is recorded
