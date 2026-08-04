# Wix editor changes log

Tracks content and layout changes made directly in the Wix editor for `inzbc.org`, outside
this repo's version control. Log each session here before or immediately after editing so
changes are reviewable and reversible.

[CLAUDE.md](../CLAUDE.md) is explicit that a full external Wix backup is not a thing that exists, so
"take a backup first" is not an instruction anyone can follow. What is actually available: Site
History restores saved page versions, so page edits are recoverable, but apps, some components and
CMS data may not restore cleanly. Before cutover, record the Site History version and export CMS
collections where applicable. Publishing still needs explicit written sign-off from Sunil.

## 2026-08-04 — INZBC Staging published

**Site:** `INZBC Staging` (duplicate), site id `5ba17306-89ea-4d17-a67d-47dcb21ba20c`
**Public URL:** https://inzbcsecretariat.wixsite.com/website-2
**Editor:** Bhanu, via the Wix API
**Authority:** Bhanu, 4 August 2026. The live `inzbc.org` site was not touched.

| # | Change | Before | After |
|---|--------|--------|-------|
| 1 | Site publish state | Draft, never published since duplication on 24 July | Published, reachable at the URL above |

No page, content or setting was edited. The site still carries the copy of `inzbc.org` it received
when it was duplicated on 24 July, so what is now public is last month's live content on a
`wixsite.com` address, not the rebuild.

**Why:** the duplicate exists to be shared as a preview (`discovery.md` OI-9), and an unpublished
Wix site serves nothing at all, so there was no URL to share.

### What this changes, and what to do about it

Publishing made a second public copy of INZBC's content. Two consequences follow, and the first is
now live rather than hypothetical.

**Anything saved here from now on is one click from public.** The rebuild will carry
`[[placeholders]]` wherever INZBC still owes a fact: member count, milestone dates, fee structure,
Executive Council. Those are correct in a draft and indefensible on a page carrying the Council's
name. Publishing is no longer a step someone has to decide on, because the site is already
published; the next publish simply ships whatever has been saved.

**Recommended before the rebuild starts:** set a site password on the duplicate. It is the only
control that stops a person holding the link, which is the actual exposure, and it carries no
cutover trap because removing it is inherently part of going live. `robots.txt` was considered and
rejected, for the reasons in [`wix-staging-readiness.md`](./wix-staging-readiness.md). Site
passwords have no API, so this is Sunil or a collaborator in the dashboard.

**At cutover:** this site becomes `inzbc.org`. Confirm the password is removed, both SEO settings
are still as recorded, and go-live sign-off is in writing.

---

## 2026-07-28 — Homepage

**Page:** Homepage (inzbc.org)
**Editor:** Paras
**Status:** Saved in Wix editor, not published. Pending review — Sunil.

| # | Section | Change |
|---|---------|--------|
| 1 | Hero | Text changed from "CONNECTING NEW ZEALAND AND INDIA SINCE 1988" to "New Zealand's Gateway to India" |
| 2 | HOME 8 | Heading changed from "What's the latest?" to "Latest Insights" |
| 3 | HOME 8 | Body text updated to focus on India-NZ trade and FTA developments — **[[before and after text owed]]**, see note below |
| 4 | HOME 8 | Button text changed from "NEWS CENTRE" to "VIEW ALL INSIGHTS" |
| 5 | HOME 4 | "Why choose us?" heading and body paragraphs updated with FTA-focused content — **[[before and after text owed]]**, see note below |
| 6 | HOME 5 | "TRADE BAZAAR" renamed to "TRADE WITH INDIA" |
| 7 | New section | FTA Feature Band added after hero — "NZ India FTA Hub" heading, "Understand the FTA" button |

**Next step:** Awaiting Sunil's review before publish.

**Rows 3 and 5 are incomplete.** They record which section changed and the theme of the change, not
what the text said before and after. `CLAUDE.md` asks for the wording on both sides, because Site
History records *that* something changed while this log is the only record of *what it said*. That
matters concretely here: these seven changes are sitting unpublished in the live editor, and
`docs/discovery.md` OI-9 has them being rolled back. The duplicate `INZBC Staging` now exists and
OI-9 is closed, so the rollback is actionable rather than waiting on anything. Rolling back text
nobody wrote down loses it.

Paras to fill both rows from the editor before this merges. Not reconstructed here, because guessing
at the previous copy would defeat the point of the log.
