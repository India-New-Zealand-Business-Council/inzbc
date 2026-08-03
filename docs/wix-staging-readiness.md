# Wix staging: what is verified, what must be done by hand

Read before starting the rebuild on the duplicate. Written 4 August 2026 against
`INZBC Staging` (site id `5ba17306-89ea-4d17-a67d-47dcb21ba20c`), the duplicate created 24 July.

Nothing on the site was changed to produce this. Every result below is a read.

---

## The duplicate, as it stands

| Property | Value | Why it matters |
|---|---|---|
| Status | **Draft**, never published | Wix serves nothing at all for an unpublished site. There is no public exposure today |
| Plan | Free | Publishing gives a public `wixsite.com` address. No custom domain needed for that |
| Created / updated | 24 Jul 2026, same minute | Confirms nobody has edited it since duplication |
| Editor | Wix Editor (not Studio) | Determines which editor instructions apply |
| Apps present | Promote SEO, Blog, Forms & Payments, Invoices, **Members Area**, Video | Members Area came across with the duplicate. See the warning below |

---

## Verified: two preconditions the redirect map silently depends on

[`website-redirect-map.md`](./website-redirect-map.md) assumes both of these. Neither was
written down anywhere, and both would have broken it quietly.

    GET /seo/user-config/v1/seo-user-config
    { "shouldFlattenUrlHierarchy": false, "shouldUsePartialRouteMatch": false }

**`shouldFlattenUrlHierarchy: false`** — correct, and it must stay that way. If flattening were
enabled, `/membership/join` would serve at `/join`, `/insights/publications` at `/publications`,
and `/media/news` at `/news`. Every nested target in the redirect map would point at a path that no
longer exists, and the map's whole purpose is that those paths resolve.

**`shouldUsePartialRouteMatch: false`** — correct, and this one is subtler. If enabled, a request
for a page that does not exist returns `200` instead of `404`. The cutover plan is to monitor 404s
for the observation window afterwards. With partial route matching on, a broken redirect returns
`200` and the monitoring reports everything as healthy while inbound links quietly land on the
wrong page.

Neither needs changing. Both should be re-checked immediately before cutover, because they are
site-level settings that a later editor session can flip without anyone noticing.

---

## Cannot be scripted: the page tree

**Wix exposes no REST API for creating or arranging editor pages.** The API surface covers CMS
collections, SEO configuration, blog, forms, media and business data. The page tree, slugs,
navigation menu and layout are Editor operations only.

So the rebuild is hand work in the Wix Editor, against [`page-specs.md`](./page-specs.md) and the
slugs in [`website-redirect-map.md`](./website-redirect-map.md). It cannot be automated, generated
or reviewed as a diff, which makes the editor log the only record of what changed.

The same applies to the 301 redirects themselves. Wix's URL redirect manager is a dashboard
feature with no public API, so each redirect in the map is entered by hand.

---

## The publish trap

The duplicate is safe while it stays unpublished. The risk begins the moment anyone clicks
**Publish**, and it is not primarily an SEO risk.

A free Wix site publishes to a public `<account>.wixsite.com/<site>` address. No domain, no DNS,
nothing to buy. Anyone with the link reaches it, and search engines can index it.

**The real exposure is draft content, not search ranking.** The rebuild will carry
`[[placeholder]]` markers wherever INZBC still owes a fact: the member count, the milestone dates,
the fee structure, the Executive Council entries. Those are correct in a draft. On a public page
carrying INZBC's name, in front of a member, a journalist or a board member, they are not.
`CLAUDE.md` requires sourced material only with placeholders where facts are owed; that convention
assumes the placeholders never reach publication.

Duplicate-content damage is the lesser worry. `inzbc.org` is older, stronger and more linked, so a
search engine would almost certainly treat it as canonical over a fresh `wixsite.com` subdomain.

**Any collaborator on the duplicate can publish it.** This is one accidental click, not a
hypothetical.

### Before sharing any preview URL

Set a **site password** on the staging duplicate. It is the right control for two reasons: a
crawler that gets an authentication challenge indexes nothing, and a person without the password
sees nothing either, which is the actual exposure. It also carries no cutover trap, because
removing the password is inherently part of going live.

**Do not use `robots.txt` for this.** It was considered and rejected. `Disallow: /` blocks
*crawling*, not *indexing*: a URL that is linked from anywhere can still be listed, and worse,
blocking the crawl prevents a search engine from ever reading a `noindex` instruction, so it
actively obstructs later removal. It also stops nobody with a link. And because the duplicate
*becomes* `inzbc.org` at cutover, a `Disallow: /` left in place would tell every search engine to
drop the live site, with symptoms appearing weeks later.

Site passwords are an Editor and dashboard setting. There is no API for them, so this is Sunil or
a collaborator, by hand.

---

## Warning: the Members Area app came across

The duplicate carries the **Wix Members Area** app. Nothing has been built on it, and nothing
should be.

`CLAUDE.md` and [`modules/membership-crm.md`](./modules/membership-crm.md) are explicit: Member
Jungle is the provisional system of record and membership is not rebuilt on Wix before the
retain / integrate / replace assessment closes. The app being installed is not permission to use
it. It arrived with the duplicate.

Leave it alone rather than removing it. Uninstalling an app on a Wix site is not cleanly
reversible, and Site History does not reliably restore apps.

---

## Order of work

1. Sunil sets a site password on the duplicate, before any preview URL is shared.
2. Page tree, slugs and navigation by hand in the Editor, against `page-specs.md` and the redirect
   map. Every session logged in [`wix-changes-log.md`](./wix-changes-log.md) with before and after
   text, because Wix records *that* something changed and not what it said.
3. Content, with `[[placeholders]]` wherever INZBC still owes a fact.
4. The 301 redirects by hand, from the map.
5. Immediately before cutover: re-check both SEO settings above, record the Site History version,
   export CMS collections, confirm the password is removed, and get written go-live sign-off.

---

## Related

- [`website-redirect-map.md`](./website-redirect-map.md) — the URLs and their destinations
- [`wix-rebuild-decisions.md`](./wix-rebuild-decisions.md) — the eleven decisions and their sources
- [`page-specs.md`](./page-specs.md) — what each page contains
- [`wix-changes-log.md`](./wix-changes-log.md) — the editor session record
- [`discovery.md`](./discovery.md) — OI-8 cutover, OI-9 duplicate
