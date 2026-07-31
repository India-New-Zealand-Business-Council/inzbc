# Website redirect map — live URLs before migration

Prerequisite for the Wix rebuild. `INZBC_Website_Stocktake_Migration_and_Wix_Guide.docx` §5 is
explicit: do not delete or rename a page without a redirect, and publish new pages only once
redirects are ready. This file is the inventory that has to exist before any of that.

**Source of truth for the "current" column:** `https://www.inzbc.org` sitemaps, read 31 July 2026.
Not the guide's tables, which were written in June and no longer match the site.

| Sitemap | Count |
|---|---|
| `pages-sitemap.xml` | 20 |
| `blog-posts-sitemap.xml` | 154 |
| `blog-categories-sitemap.xml` | 6 |

The guide says 157 blog posts; the live sitemap says 154. Three have been removed or unpublished
since June. Neither figure should be quoted until someone reconciles them in the Wix dashboard.

## Two problems with the guide's redirect table

**`/trade-shows` does not exist.** The guide maps `/trade-shows -> /trade-missions`, but that URL
returns **404** on the live site. It is a navigation label, not a page. Nothing to redirect; the
row should be removed so it does not imply a page was handled.

**Eleven live pages have no redirect decision.** The guide's table covers 10 URLs. Nine of those
exist. The pages below are live, in the sitemap, and absent from the plan. Every one needs a
decision before launch, because an unmapped page either 404s or silently keeps ranking against the
new structure.

## Decided redirects

From the guide §5, with the current URL verified against the sitemap.

| Old URL | New URL | Type | Verified live |
|---|---|---|---|
| `/about-us` | `/about-inzbc` | 301 | yes |
| `/our-sponsors` | `/partners` | 301 | yes |
| `/upcoming-events` | `/events` | 301 | yes |
| `/trade-bazaar` | `/india-market-opportunities` | 301 | yes |
| `/join-inzbc` | `/membership` | 301 | yes |
| `/membership-form` | `/membership/join` | 301 | yes |
| `/publications` | `/insights/publications` | 301 | yes |
| `/newsletters` | `/insights/newsletters` | 301 | yes |
| `/news/categories/news` | `/media/news` | 301 | yes |
| ~~`/trade-shows`~~ | ~~`/trade-missions`~~ | — | **404, drop this row** |

## Undecided — live pages with no plan

Each needs a target or an explicit "keep as-is". `[[decision]]` marks what INZBC owes.

| Live URL | Note | Proposed target |
|---|---|---|
| `/connect` | Contact / enquiry entry point. | `[[decision]]` — keep, or fold into `/about-inzbc` |
| `/executive-council` | Board and executive bios; cited by `client-answers.md` D1. | Keep. Sits under About in the new tree. |
| `/our-patron` | Patron page; `client-answers.md` C8 says Patron belongs in About, linked from Partners. | `/about-inzbc/patron` `[[decision]]` |
| `/members` | Overlaps `/join-inzbc` and `/membership-form`. | `/membership` `[[decision]]` |
| `/member-directory` | C5 says link out to Member Jungle, do not copy the directory. | `/membership/directory` `[[decision]]` |
| `/member-profile` | Members Area dynamic page, not a content page. | Keep. Do not redirect a Members Area route. |
| `/past-events` | Guide wants one event hub with a clean archive. | `/events/past` `[[decision]]` |
| `/trade-news` | Trade content that predates the Insights split. | `/insights` or `/media/news` `[[decision]]` |
| `/india-x-nz` | Campaign or event page; purpose unclear from the URL. | `[[decision]]` — INZBC to confirm what this is |
| `/copy-of-boardroom-to-border` | **Leftover Wix duplicate.** The `copy-of-` prefix is an editor artefact, and it is indexed. | `/events/past` `[[decision]]`, or unpublish |
| `/news` | Blog root. Guide moves news under Media Centre. | `/media/news` `[[decision]]` |

## Blog categories

Five category URLs are live and indexed. The guide replaces the whole taxonomy with FTA Insights,
India Market Updates, INZBC News, Events, Reports and Commentary, so **all five change**, not just
the one row in §5.

| Live category | Proposed |
|---|---|
| `/news/categories/news` | `/media/news` (in guide) |
| `/news/categories/announcement` | `[[decision]]` |
| `/news/categories/past-events` | `[[decision]]` |
| `/news/categories/upcoming-events` | `[[decision]]` |
| `/news/categories/trade-events` | `[[decision]]` |

## Blog posts

154 posts at `/post/<slug>`. **Do not change these slugs.** They carry the site's search history
and the guide's own analytics note says AI referrals are already arriving. Recategorising a post
does not change its URL in Wix; only renaming the post does. If any post is renamed or pruned, it
needs its own 301 and belongs in this table.

## Order of work

Straight from the guide's SEO checklist, and not to be reordered:

1. Export the full URL list. Done above; refresh it immediately before launch.
2. Record current titles and meta descriptions. **Not done.** Needed for the pages being renamed.
3. Build new pages as **hidden** pages on the duplicate.
4. Add content, SEO title, meta description and internal links before publishing.
5. Publish only when the redirects are ready.
6. Add the 301s immediately after each URL change.
7. Submit the sitemap to Google Search Console.
8. Check 404s weekly for eight weeks.

## Constraints

- Build on the duplicate, `INZBC Staging` (`5ba17306-89ea-4d17-a67d-47dcb21ba20c`). Do not edit or
  publish `inzbc.org` (`40ea1d0a-807a-48d2-ab93-3ccce6ed6443`).
- Wix MCP writes hit live data instantly with no draft step. Confirm the target site id before any
  write call.
- Log every editor session in `docs/wix-changes-log.md` with before and after text.
- Redirects are configured in Wix SEO tools and only apply on the **live** site. They cannot be
  tested on the duplicate, so the redirect list has to be right before cutover rather than
  discovered afterwards.
