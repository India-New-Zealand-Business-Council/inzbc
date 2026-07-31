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

The guide says 157 blog posts; the live sitemap says 154. That is a net difference of three, which
is not the same as three removals: additions, unpublishing and an inaccurate June count all produce
it. Neither figure should be quoted until someone reconciles them in the Wix dashboard.

Every URL is listed in [`website-url-inventory-2026-07-31.txt`](website-url-inventory-2026-07-31.txt),
including all 154 post slugs. Without the slugs there is no snapshot to diff against later, so a
renamed or pruned post could not be identified as needing a redirect.

## Two problems with the guide's redirect table

**`/trade-shows` does not exist, but Trade Shows does.** The guide maps
`/trade-shows -> /trade-missions`, and `/trade-shows` returns **404**. That is not the end of it:
the live navigation's "Trade Shows" link points at **`/trade-news`**, whose page title is literally
"Trade Shows | India New Zealand Business Council". So the content exists at a URL the guide never
mentions, and `/trade-news` is not a news page despite its slug.

Two consequences. `/trade-news` must go to the Trade destination, not to Insights or Media, because
`docs/discovery.md:41` and `docs/page-specs.md:42` both place Trade Shows in the Trade Resources
hub. And `/trade-shows` is still worth a 301 even though it 404s today: rescuing a historical URL
that external links may still point at is a normal reason to add one, not a no-op.

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
| `/trade-shows` | `/trade-missions` | 301 | **404 today; keep the 301 to rescue old links** |

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
| `/trade-news` | **This is the Trade Shows page**, despite the slug. Title: "Trade Shows \| India New Zealand Business Council". Linked from the live nav as "Trade Shows". | Trade Resources / `/trade-missions` `[[decision]]`. **Not** Insights or Media: `discovery.md:41` and `page-specs.md:42` both put Trade Shows under Trade. |
| `/india-x-nz` | **Boardroom to Border, Auckland.** Title: "Boardroom to Border \| INZBC". A real 2025 event page, not a campaign of unknown purpose. | `/events/past` `[[decision]]` |
| `/copy-of-boardroom-to-border` | **Boardroom to Border, Christchurch.** Title: "Boardroom to Border - Christchurch \| INZBC". The `copy-of-` prefix is an editor artefact, but the page is a distinct event and is linked from current navigation. | `/events/past` `[[decision]]`. **Do not unpublish**: it is indexed and substantive, and unpublishing without a redirect breaks this document's own prerequisite. |
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

154 posts at `/post/<slug>`, all listed in the inventory file. **Do not change these slugs.** They
carry the site's search history, and the guide's own analytics note says AI referrals are already
arriving.

Recategorising a post does not change its URL. Changing the URL does, and in Wix the slug is a
separately editable SEO field, so renaming the title is not the only way to alter it. Any slug
change or pruned post needs its own 301 and belongs in this table.

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

- Build on the duplicate, `INZBC Staging` (`5ba17306-89ea-4d17-a67d-47dcb21ba20c`, draft, free
  plan, no custom domain). Do not edit or publish `inzbc.org`
  (`40ea1d0a-807a-48d2-ab93-3ccce6ed6443`, published, premium, custom domain).

  **This partly contradicts `docs/discovery.md` OI-9**, which still lists duplication, collaborator
  access and written confirmation as outstanding on Sunil. The staging site exists and Bhanu
  confirmed on 31 July 2026 that it is the duplicate to build on. The rest of OI-9 is unverified
  here: whether the team have collaborator access, whether the live site's publish rights were
  removed, and whether written confirmation was given. Do not read this line as OI-9 being closed;
  it needs updating in its own change once those are checked.
- Wix MCP writes hit live data instantly with no draft step. Confirm the target site id before any
  write call.
- Log every editor session in `docs/wix-changes-log.md` with before and after text.
- Redirects are configured in Wix SEO tools and only apply on the **live** site. They cannot be
  tested on the duplicate, so the redirect list has to be right before cutover rather than
  discovered afterwards.
