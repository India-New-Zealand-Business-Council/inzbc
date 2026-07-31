# Accessibility audit — current live site (baseline)

## What this is

An accessibility audit of the **live production site at inzbc.org as it exists today**,
fetched and reviewed 29 Jul 2026. This is a **baseline**, not the audit `REQ-U-03`
(`docs/requirements.md`) actually requires — that requirement is "an end-to-end WCAG 2.2 AA
audit passes on every public page" of the **new** site once it's built, and the new site
isn't rendered anywhere yet except an unpublished homepage draft sitting in the live Wix
editor, which this audit does not touch (see `docs/discovery.md` OI-9 — live-site editing is
currently paused pending Sunil duplicating the site). Auditing the old, live pages instead
tells the team what's carrying over and what to deliberately fix in the rebuild, the same
way `docs/discovery.md`'s content audit did for copy.

## Method

Static fetch of each live page's server-rendered HTML (`curl`), then manual review of the
markup against a fixed set of WCAG 2.2 AA success criteria. **This is not full browser or
assistive-technology testing.** Criteria that require a rendered viewport, computed styles,
or real keyboard/screen-reader interaction (contrast, reflow, non-text contrast, keyboard
operation, focus visibility, target size) are marked **Not verified** below rather than
guessed — a static fetch cannot responsibly answer them, and this repo's rule is to flag
what's unconfirmed rather than assume (`CLAUDE.md`).

## Page mapping

The new site's IA doesn't match the live site 1:1. Home, About and Connect map directly.
Events, Trade, Members and Partners on the new site are **rewrites or merges of multiple
current pages**, so those sections below audit every live page feeding into the new one:

| New page | Live page(s) audited | Note |
|---|---|---|
| Home | `/` | Direct match |
| About | `/about-us` | Direct match |
| Events | `/upcoming-events`, `/past-events` | Direct match (two current pages) |
| Trade | `/trade-news` ("Trade Shows"), `/trade-bazaar` | New page merges these two. **Correction:** the live nav's "Trade Shows" link actually points to `/trade-news`, not `/trade-shows` (that slug 404s) — worth fixing in any future URL inventory. |
| Members | `/join-inzbc`, `/member-directory` | New page merges these two |
| Partners | `/our-sponsors` | New page, closest live equivalent |
| Connect | `/connect` | Direct match |

## Findings by page

Verdict key: **Pass** (observed and correct) · **Fail** (observed and wrong) · **Not
verified** (cannot be determined from static HTML).

Heading structure is recorded as **Not verified**, not Fail. A missing `<h1>` and skipped ranks
are real observations and almost certainly problems, but neither is a WCAG 2.2 AA failure on its
own: no success criterion requires an `h1`, and proper nesting is an advisory technique for
SC 1.3.1 (G141), not a requirement. SC 1.3.1 asks whether structure conveyed visually is also
available programmatically, which needs a rendered comparison this method cannot make. The counts
below stand as evidence for the rendered pass to confirm.

Filename-as-alt-text is different, and is recorded as **Fail**: W3C documents using a filename as
the text alternative as a failure of SC 1.1.1, and that is visible in the served markup.

### Home (`/`)
| Criterion | Verdict | Evidence |
|---|---|---|
| 3.1.1 Language of Page | Pass | `<html lang="en">` |
| 2.4.2 Page Titled | Pass | `<title>India New Zealand Business Council \| Home</title>` |
| 1.3.1 Info and Relationships (headings) | Not verified | No `<h1>` anywhere on the page. Headings present are 5×`<h2>`, 1×`<h5>`, 4×`<h6>` — jumps straight from h2 to h5/h6, skipping h3/h4. Levels read as font-size choices, not document structure. |
| 1.1.1 Non-text Content | Fail (mixed) | 36 `<img>` tags, all carry an `alt` attribute (none missing outright), but 26 use raw, auto-generated filenames as the alt text, e.g. `alt="Screen Shot 2022-04-13 at 1.01.19 PM.png"`, `alt="WhatsApp Image 2025-05-12 at 2.06.54 PM.jpg"`. 10 use `alt=""`. Genuine pass: the four social-media icons carry clean alt text (`"Twitter"`, `"LinkedIn"`, `"Facebook"`, `"YouTube"`). |
| 2.4.4 Link Purpose (nav) | Pass | Primary nav links are descriptive (`About INZBC`, `Executive Council`, `Our Sponsors`, `Trade Shows`, `Join INZBC`, etc.) — no bare "click here"/"read more" in the nav. Body-copy links not exhaustively checked. |
| 4.1.2 Name, Role, Value | Pass | Custom "More…" carousel buttons carry explicit `aria-label`, e.g. `aria-label="More ABOUT US pages"`. `role="button"` (×7) and `role="region"` (×4) present; real keyboard operability of these custom roles is Not verified. |
| Landmarks | Pass | One each of `<header>`, `<main>`, `<footer>`; two `<nav>`. |
| 1.4.3 Contrast (Minimum) | Not verified | Needs rendered/computed-style check. |
| 1.4.10 Reflow | Not verified | Needs a real narrow viewport. |
| 1.4.11 Non-text Contrast | Not verified | Needs rendered/computed-style check. |
| 2.1.1 Keyboard | Not verified | Needs interactive testing. |
| 2.4.7 Focus Visible | Not verified | Needs interactive testing. |
| 2.5.8 Target Size (Minimum) | Not verified | Needs rendered measurement. |

### About (`/about-us`)
| Criterion | Verdict | Evidence |
|---|---|---|
| 3.1.1 / 2.4.2 | Pass | `lang="en"`; `<title>About INZBC \| India New Zealand Business Council</title>` |
| 1.3.1 (headings) | Not verified | Only 2×`<h2>` on the whole page. No `<h1>`, no h3–h6. |
| 1.1.1 Non-text Content | Fail (mixed) | 15 images; 4 `alt=""`, rest filename-derived (`alt="Screen Shot 2021-08-30 at 11.42.18 AM.png"`, `alt="Screen Shot 2020-05-12 at 4.38.52 PM.png"`) except the same four social icons, which pass. |
| Landmarks | Pass | One each of header/main/footer/nav. |
| Contrast / reflow / non-text contrast / keyboard / focus / target size | Not verified | Same static-fetch limitation as Home. |

### Events (`/upcoming-events`, `/past-events`)
| Criterion | Verdict | Evidence |
|---|---|---|
| 3.1.1 / 2.4.2 | Pass | Both pages: `lang="en"`; titled `Event Calendar \| …` and `Past Events \| …` |
| 1.3.1 (headings) | Not verified | `/upcoming-events`: 1×h2 then 7×h4 — skips h3, no h1. `/past-events`: 5×h2 only, no h1. |
| 1.1.1 Non-text Content | Fail (mixed) | `/upcoming-events`: 17 images, mostly event-flyer filenames as alt text (`alt="Invite-Chch-Diwali-V2.jpg"`, `alt="Covid-series_invite-part3-low.jpg"`) — same social-icon pass pattern. `/past-events`: 18 images, same pattern. |
| Note | — | `/upcoming-events` returned HTTP 200 on this fetch (29 Jul 2026). `docs/discovery.md`'s earlier audit recorded this slug as 404 — that appears resolved or was transient; not re-verified against the earlier crawl conditions. |
| Contrast / reflow / non-text contrast / keyboard / focus / target size | Not verified | — |

### Trade (`/trade-news` "Trade Shows", `/trade-bazaar`)
| Criterion | Verdict | Evidence |
|---|---|---|
| 3.1.1 / 2.4.2 | Pass | Both: `lang="en"`; titled `Trade Shows \| …` and `Trade Bazaar \| …` |
| 1.3.1 (headings) | Not verified | `/trade-news`: 10×h2, no h1, nothing else. `/trade-bazaar`: 1×h2 only, no h1. |
| 1.1.1 Non-text Content | **Pass** on `/trade-news`, **Fail** on `/trade-bazaar` | `/trade-news`'s 28 event images use genuinely descriptive alt text matching the real event title, e.g. `alt="11th CII HR Conclave - "Powering Growth with Head, Heart and Courage" on 25-26 Nov 2021"`, `alt="Hon Phil Twyford's Address to the 7th International INZBC Summit 2021"`. This is the pattern every other page should match. `/trade-bazaar` reverts to the filename/empty-alt pattern seen elsewhere (10 images, 4 empty, rest generic). |
| Contrast / reflow / non-text contrast / keyboard / focus / target size | Not verified | — |

### Members (`/join-inzbc`, `/member-directory`)
| Criterion | Verdict | Evidence |
|---|---|---|
| 3.1.1 / 2.4.2 | Pass | Both: `lang="en"`; titled `Join INZBC \| …` and `Member Directory \| …` |
| 1.3.1 (headings) | Partial pass | `/join-inzbc` is the **only page in this audit with an `<h1>`** (one h1, one h2) — real structural improvement over the rest of the site, though the h1 is styled at `font-size:20px`, visually smaller than a main heading would typically read. `/member-directory` has no h1, only 1×h2. |
| 1.1.1 Non-text Content | Fail (mixed) | Both pages: only 2 real content images each (the rest are the shared header/footer/social icons), and both use the generic `alt="Untitled-1.jpg"` for the non-icon image, appearing twice on each page. |
| Contrast / reflow / non-text contrast / keyboard / focus / target size | Not verified | — |

### Partners (`/our-sponsors`)
| Criterion | Verdict | Evidence |
|---|---|---|
| 3.1.1 / 2.4.2 | Pass | `lang="en"`; `<title>Our Sponsors \| India New Zealand Business Council</title>` |
| 1.3.1 (headings) | Not verified | 1×h2, then 6×h4 — skips h3, no h1. |
| 1.1.1 Non-text Content | Fail (mixed) | 19 images. Partner/sponsor logos are partially identifying but still mostly filename-derived: `alt="HCI"` is a genuine pass (short, meaningful), but `alt="bnz-logo-1.png"`, `alt="UoA logo.png"`, `alt="Duco Consultancy New Logo.png"` just repeat the filename rather than naming the partner clearly. Three images share the identical generic `alt="Sponsors-Card_Logo_Plate_1200x785.jpg"`, which is actively unhelpful for distinguishing them by screen reader. |
| Contrast / reflow / non-text contrast / keyboard / focus / target size | Not verified | — |

### Connect (`/connect`)
| Criterion | Verdict | Evidence |
|---|---|---|
| 3.1.1 / 2.4.2 | Pass | `lang="en"`; `<title>Connect \| India New Zealand Business Council</title>` |
| 1.3.1 (headings) | Not verified | 4×h3, 1×h5, 7×h6 — no h1, no h2. Structure jumps straight to h3 then down to h5/h6. |
| **Landmarks** | **Fail** | Page has **two `<main>` elements**. Only one `<main>` is valid per page — a second one breaks the "jump to main content" landmark for screen-reader users, who get no reliable way to know which is the real content region. |
| 1.1.1 Non-text Content | Fail (mixed), with a pass on video links | 26 images. Same generic-filename pattern as other pages (`alt="Untitled-1.jpg"`, `alt="inzbc-website-foot-23.jpg"` ×2, `alt="newsletter-mop.png"`). Genuine pass: embedded video links carry descriptive alt text (`alt="Summit 2019 Highlights"`, `alt="INZBC SUMMIT 2018 - Highlights"`). Social icons pass as elsewhere. |
| 3.3.2 Labels or Instructions (contact form) | **Pass** | The enquiry form (first name, last name, email, phone, message) uses real `<label for="input_comp-…">` elements each correctly bound by `id` to its field — genuine, correct programmatic labelling. The email field additionally has `type="email"`, `required`, and a validation `pattern`. |
| Contrast / reflow / non-text contrast / keyboard / focus / target size | Not verified | — |

## Cross-page patterns

Observed consistently across all seven page-groups, not isolated incidents:

1. **No `<h1>` on 6 of 7 page-groups.** Only `/join-inzbc` has one. Heading levels
   elsewhere appear chosen for visual size (h2/h4/h5/h6 used inconsistently) rather than
   document structure, and levels are skipped (h2→h4, h2→h5/h6) on every page checked.
   This is the single most consistent, fixable problem found.
2. **Alt text is present but usually not meaningful.** No page had an image missing the
   `alt` attribute outright — but the large majority of non-icon images across every page
   use the original filename as alt text (`Screen Shot …`, `WhatsApp Image …`,
   `Untitled-1.jpg`). The one clear exception is `/trade-news`, where every event image has
   a real descriptive alt matching the event title — proof the rest of the site can do this
   without new tooling, just consistent editorial habit when images are uploaded.
3. **Social icons and nav links are reliably good.** The shared header/footer component's
   social icons (`"Twitter"`, `"LinkedIn"`, `"Facebook"`, `"YouTube"`) and primary nav link
   text are consistently correct across every page — this part of the shared template
   doesn't need fixing.
4. **`lang="en"` and a descriptive `<title>` are correct on every single page audited** —
   no findings needed here at all.

## What needs fixing (priority order, for whoever builds the new site)

1. **Give every page one real `<h1>`, then a non-skipping heading hierarchy underneath
   it.** Highest-impact, lowest-effort fix; affects every page. Bake this into the design
   system / component library work already planned (`docs/workstreams/paras.md`, "Design
   system" item) rather than auditing it in after the fact.
2. **Write real alt text at upload time, not filename defaults.** `/trade-news` already
   proves the team can do this — make it the standard for every image, not just event
   flyers. Distinguish genuinely decorative images (`alt=""`) from content images that need
   real description; don't default to either.
3. **Never render two `<main>` landmarks on one page** — found on the live Connect page;
   worth a specific check in the new build's component review.
4. **Keep the working patterns**: the shared nav/footer's link text, social-icon alt text,
   and the Connect page's form-label association are all genuinely correct today and are a
   reasonable baseline to carry forward into the rebuild.
5. **Contrast, keyboard operability, focus visibility, reflow, and target size are
   completely unverified by this audit** and need real testing (rendered browser + keyboard
   + a contrast checker, ideally an automated tool like axe plus manual passes) once the new
   site has actual rendered pages to test — this is what `REQ-U-03`'s "end-to-end WCAG 2.2
   AA audit" will need to cover that this baseline could not.
