# Migration and rollback plan for cutover

Switching `inzbc.org` from the live Wix site to the rebuilt one. One event, on the account owner's
written authority, per BR6.

The governing fact: **only the account owner can publish, and there is no API for it.** Publishing
is a button in the Wix Vibe editor. So cutover is a manual step taken by one person, and this plan
is written for that person rather than for a deployment pipeline.

## Before the switch

**Record what exists now, because it is what rollback returns to.**

- Note the live site's Wix Site History version, with its date. Site History restores saved page
  versions, which is what makes a page-level rollback possible.
- Export any CMS collections in use. Site History does not reliably restore CMS data or app data,
  so an export is the only copy.
- Save the current DNS records, including TTL. The TTL determines how long a rollback takes to
  propagate, and it is worth lowering it 24 hours in advance so a rollback is minutes rather than
  hours.
- Confirm every redirect in `docs/website-redirect-map.md` has a destination that returns 200 on
  the new site. A redirect to a 404 is worse than no redirect: it tells search engines the page is
  gone rather than moved.

**Confirm the new site is actually ready.**

- All twelve routes return 200.
- Placeholders are either filled or deliberate. BR2 permits a visible `[[placeholder]]` where INZBC
  owes a fact; it does not permit an invented one.
- WCAG 2.2 AA, including the 320px reflow case. The build fails on a contrast failure, so a green
  build is evidence for the palette but not for everything.
- Written go-live authority from the account owner, naming the date. This is a separate document
  from the requirements approval, and approving that one does not authorise this.

## The switch

1. Publish the new site from the Wix Vibe editor.
2. Point the domain at it.
3. Walk the redirect map: every live URL, checked against its destination. Not a sample.
4. Check the pages a member is most likely to arrive on: home, FTA, membership, events, contact.
5. Submit the updated sitemap to Google Search Console.

## Rollback

**Decide the trigger before you start, not while it is going wrong.** Rollback if the site does not
resolve, if a substantial number of live URLs 404, or if content that should be there is missing.
Do not roll back for cosmetic problems: they are cheaper to fix forward than to switch twice.

1. Point DNS back to the previous target. This is the whole rollback for a domain-level problem,
   and it is why the TTL matters.
2. If the live site itself was changed, restore the recorded Site History version.
3. Re-import CMS collections from the export if they were touched.
4. Write down what happened while it is fresh, per `incident-response.md`.

**What rollback cannot recover.** Anything a visitor did on the new site during the window:
form submissions, event registrations, sign-ups. Those live in Wix, Zoho Backstage and Member
Jungle rather than in the site, so they survive the DNS change, but a submission made against a
form that then disappears may have no follow-up path. Keep the window short.

## The risk this plan exists for

Inbound links and search position are an asset accumulated over years and not quickly rebuilt. The
redirect map is the control. Everything else here is recoverable within a day; a lost ranking is
not.

## After

- Watch Search Console for crawl errors over the following fortnight.
- Keep the old site's Site History version recorded until the new one has been stable for a month.
  Deleting it early removes the only route back.
- Record the cutover in `docs/wix-changes-log.md`: what changed, when, and on whose authority.
