# Wix Studio paste-ready snippets

Ready-to-paste code blocks for the INZBC Studio site
(`040b006f-3745-4a4f-ae4d-03aedb08a7b1`).

These are **design-system scaffolding and section HTML**, not a replacement for
building pages in the Studio editor. Paste each snippet into the location noted.
Every snippet uses inline CSS so it works as a standalone embed.

## Files

| File | Paste location | What it does |
|---|---|---|
| `site-head.html` | Studio → **Settings** → **Custom Code** → `<head>` | Loads Google Fonts (Big Shoulders, Merriweather) and global CSS variables/colours. |
| `organization-schema.html` | Same, once details are final | JSON-LD `Organization` schema. |
| **Homepage** |
| `home-hero.html` | Home page → **Add** → **Embed** → **Embed HTML** | Hero section with headline, sub, and CTAs. |
| `fta-feature-band.html` | Home page embed | Lavender→Blue→Navy gradient FTA announcement band. |
| `trade-stats.html` | Home page embed | Trade-opportunity statistics grid. |
| `credibility-strip.html` | Home page embed | Established / members / recognised-by-govts line. |
| `join-cta.html` | Home or Membership page embed | Final conversion band. |
| **About** |
| `about-hero.html` | About page embed | About hero section. |
| `executive-council.html` | `/executive-council` page embed | Board and executive team grid. **Carries real names. Do not publish without Board confirmation** (`client-answers.md` D1). |
| `our-patron.html` | `/our-patron` page embed | Patron profile. |
| **Membership** |
| `membership.html` | `/membership` page embed | Value proposition and tiers placeholder. |
| `membership-join.html` | `/membership/join` page embed | Application gateway to Member Jungle. |
| `member-directory.html` | `/membership/directory` page embed | Static gateway to Member Jungle directory. |
| **Events** |
| `events.html` | `/events` page embed | Upcoming events grid. |
| `events-past.html` | `/events/past` page embed | Past events archive. |
| **Trade & FTA** |
| `trade-resources.html` | Trade Resources page embed | Trade hub with four pathway cards. |
| `trade-missions.html` | `/trade-missions` page embed | Trade missions and shows. |
| `india-market-opportunities.html` | `/india-market-opportunities` page embed | Sector opportunity grid. |
| `fta-centre.html` | `/fta` page embed | FTA Centre landing page. |
| `fta-explainer.html` | `/fta/explainer` page embed | Wrapper for the deployed FTA Explainer app. |
| **Insights** |
| `insights-publications.html` | `/insights/publications` page embed | Publications library. |
| `insights-newsletters.html` | `/insights/newsletters` page embed | Newsletters, Digest and Kia Ora India. |
| `digest.html` | Trade Intelligence Digest page embed | Digest landing + archive. |
| **Other** |
| `news.html` | `/news` page embed | Blog/news landing. |
| `partners.html` | `/partners` page embed | Sponsor/partner logos and become-a-sponsor CTA. |
| `connect.html` | `/connect` page embed | Contact details and form placeholder. |

## Rules enforced in the CSS

- Tangerine (`#f05b29`) buttons use **navy** text, not white (white-on-tangerine
  is 3.37:1, below WCAG AA).
- Big Shoulders is used for headings/short statements in uppercase.
- Merriweather is used for body copy.
- Max content width ~1160px, body measure capped.
- `[[placeholder]]` markers are left visible for items that still need INZBC input.

## Before publish

- Replace every `[[placeholder]]` with sourced copy.
- Confirm the two-way trade figure: `$3.68b` (migration guide) vs `NZ$3.95bn`
  (FTA corpus) — see `docs/design-decisions.md`.
- Confirm member count with INZBC.
- Add JSON-LD `Organization` schema once logo/contact details are final.
