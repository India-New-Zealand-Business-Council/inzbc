# Design decisions — Homepage & About page

Documents the design decisions behind the homepage and About page rebuild: what was
specified by INZBC, what the team decided where sources conflicted, and what's still open.
Not a style guide — the design direction lives in `docs/design-direction.md`, and the reusable
design-token implementation built from it does not exist yet (see `docs/workstreams/paras.md`
"Design system" item). This doc is the sourced input that system should be built from.

## Sources
- `INZBC_Website_Migration_Checklist.xlsx` — Sunil Kaushal, Drive, uploaded 20 Jul 2026.
  Page inventory, migration map, homepage wireframe, SEO map.
- `INZBC_Website_Stocktake_Migration_and_Wix_Guide.docx` v1.0 — Sunil Kaushal, Drive,
  7 Jun 2026. Site architecture, page templates (section 8), Wix build steps.
- `INZBC Brand Guidelines 2026.pdf` v1.0 2025 — Drive, `Brand/Brand Guidelines` folder.
  Logo, colour, typography, photography direction.
- `INZBC Brand colors Typography logos use.pdf` — Drive, `Brand` folder. Social post
  template showing the fonts/colours applied to real copy.
- `apps/fta/corpus.py` (MFAT National Interest Analysis / MFAT FTA hub) — verified against
  MFAT Tier 1 sources 28 Jul 2026 (PR #146), used for trade statistics instead of the
  migration guide's figures (see Open items below).

## Brand tokens (from Brand Guidelines v1.0 2025)

**Colour palette** — base is navy blue and purple/blue tones (~80% of use combined); crimson,
tangerine, forest and lime/lavender are accents. The guide's ratio reads 50% Navy Blue, 30%
Purple/Blue, then 5% each for Crimson, Tangerine, Forest and Lime/Lavender, where Lime and Lavender
share one 5% allocation rather than taking 5% each. Listing them separately at 5% apiece totals
105%, so the per-colour figures below are indicative until the PDF wording is confirmed.

| Name | Hex | RGB | Role |
|------|-----|-----|------|
| Navy Blue | `#160933` | 22, 9, 51 | Primary — base/background, ~50% of colour use |
| Blue | `#261866` | 38, 24, 102 | Secondary base, ~30% with Purple |
| Purple | `#61145f` | 97, 20, 95 | Secondary base |
| Crimson | `#7e0030` | 126, 0, 48 | Accent, ~5% |
| Tangerine | `#f05b29` | 240, 91, 41 | Accent, CTA/action colour, ~5%. **Never behind white body-size text**: 3.37:1, below the 4.5:1 AA minimum. Navy `#160933` on tangerine is 5.56:1 and passes. |
| Forest | `#1b4640` | 27, 70, 64 | Accent, ~5% |
| Lavender | `#c1acfb` | 193, 172, 251 | Accent, shares ~5% with Lime |
| Lime | `#b8f07c` | 184, 240, 124 | Accent, shares ~5% with Lavender |

Preferred gradient: Lavender → Blue → Navy Blue (guide calls this combination out as
particularly successful). Red/orange/green gradients should stay sparing, matching the
solid-colour usage ratio.

**A provisional third palette exists — NOT FINAL, not the table above.** Added 6 August
2026 in the `inzbc-studio-site` repo (`docs/live-site-extract.md`), pending Sunil/INZBC
confirmation: Deep Navy `#12203D` / Marigold `#E86A17` / Teal `#0E7C86`, a 60/30/10
trust-plus-accent allocation tied to INZBC's bicultural India–NZ identity. It does not
replace the Brand Guidelines table above and nothing in either repo is built against it yet.

**Typography** — two fonts:
- **Big Shoulders** (Medium–Bold): headings and short, high-impact statements only, set in
  UPPERCASE, Bold weight as default (Medium/Extrabold for varied emphasis). Not for body
  text — the guide is explicit it stays legible only at large sizes / short lines.
- **Merriweather** (Light–Medium): all body copy. Light weight for regular paragraphs,
  Regular/Medium weight for emphasis.

**Logo** — lotus-flower mark with a star in the negative space (India + NZ symbolism
combined). Three variants: primary (full lockup), secondary (for compositions too narrow
for the primary), acronym ("INZBC", for small scales). Minimum sizes: primary 20mm/60px,
secondary 15mm/45px, acronym 8mm/25px wide. Clearspace: at least the height of the logo's
flower element on every side. Do not distort, recolour, rotate, shadow, or place on a busy
background. File formats supplied: jpg/png (screen), svg (print) — **no logo asset files
found in this repo**; INZBC needs to supply the library (see Open items).

**Photography** — vibrant, light, positive; should reflect "flourishing cultures, economies
and relationships between the two countries" and complement the brand palette. No actual
photography assets sourced yet.

## Homepage decisions

- **Section order** — hero → FTA feature band → trade-opportunity stats → pathway cards →
  upcoming events → latest insights → membership value → member spotlight → partners →
  final CTA. Taken from the migration guide's homepage wireframe (section 6). **Not identical to
  `apps/site/content/home.md`**, which also carries a credibility strip between the statistics and
  the pathway cards, and a Trade Resources entry between the Digest and membership sections. Those
  two are unresolved, not omitted deliberately. The Wix editor build is recorded in
  `docs/wix-changes-log.md` (#143), which is the source for what the editor actually holds.
- **Hero headline — reconciled.** The migration guide's wireframe specifies the headline
  verbatim: "New Zealand's Gateway to India." The Wix editor build now uses that exact
  wording (`docs/wix-changes-log.md`, 28 Jul 2026 entry). `apps/site/content/home.md`
  currently has a longer variant, "New Zealand's gateway to the India opportunity" —
  **not yet reconciled with the wireframe/Wix wording; flagged in Open items below rather
  than silently changed.**
- **CTA colour** — Tangerine (`#f05b29`) for primary action buttons (Explore the FTA, Join
  INZBC, Understand the FTA, View All Insights). Rationale: the brand guide reserves
  Tangerine as an accent against the Navy/Blue/Purple base, and an accent colour reserved
  for CTAs is the conventional way to spend that 5% — not stated explicitly in either
  source document, so treat as a design decision to confirm with Sunil, not a brand-guide
  requirement.
- **FTA feature band background** — the Lavender → Blue → Navy Blue gradient the brand
  guide calls out as its strongest combination. Same reasoning as above: a reasonable
  application of the palette, not a documented requirement — confirm before build.
- **Trade-opportunity statistics — source conflict, not yet resolved.** The migration
  guide's wireframe gives: "$3.68b two-way trade | 95% of current NZ exports receiving
  tariff removal or reductions | 300,000 strong Indian diaspora | India middle class growth
  story." `apps/site/content/home.md` and `trade.md` instead use **NZ$3.95bn** two-way
  trade and a phased **95%** tariff figure (57% duty-free from day one, rising to 82% once
  fully implemented, remaining 13% under sharp cuts) — corrected against MFAT Tier 1
  sources (key outcomes, key facts, agreement text) on 28 Jul 2026, per `apps/fta/corpus.py`
  and PR #146. That's a primary source with a recent, deliberate accuracy pass, not Sunil's
  own document. The 300,000 diaspora figure is deliberately **not** used anywhere in the
  content, because it isn't in the FTA source corpus and the team's rule is not to
  estimate. **This is a real conflict between two INZBC-supplied figures ($3.68b vs.
  $3.95bn) that needs Sunil/INZBC confirmation before publish — see Open items.** Given the
  FTA-corpus figure's stronger, recently-verified provenance, the working assumption should
  be that it's correct and the migration guide's $3.68b is the stale one — but that's a
  judgement call, not a substitute for Sunil's confirmation.
- **The $3.95bn wording still needs correcting wherever it appears.** `apps/fta/corpus.py:292`
  states it as "approximately NZ$3.95bn in the year ended December 2025" and its own note says to
  publish the period with the figure, because an undated "annually" goes stale silently. Both
  `apps/site/content/home.md` and `trade.md` currently say "NZ$3.95bn annually" without the period.
  That is a separate fix from the $3.68b conflict above and does not wait on Sunil.
- **Credibility strip member count** — "more than 200 members" in `home.md` is marked
  `[[proposed — pending INZBC confirmation]]`; the live About page audit in
  `docs/discovery.md` says "160+ members." Two different unconfirmed counts exist in the
  source material; neither is used as fact without INZBC sign-off.

## About page decisions

- **Section order** — hero → history → mission → what we do → Executive Council →
  governance → CTA, per the Wix guide's About page template (section 8: hero, history,
  mission, role, council structure, CTA). No deviation.
- **"Since 1988," not "over 25 years."** The migration checklist flags the live site's
  "over 25 years" framing as outdated positioning and directs a rewrite to "since 1988."
  `about.md` follows this exactly — this is a checklist requirement, not a stylistic
  choice.
- **History/mission copy grounded in the Brand Guidelines "Who we are" text** (guide page
  4), lightly edited for accuracy: the guide's own draft still says the Kerala ICT
  delegation is "the most recent," which is unverifiable and stale by definition in a
  living brand doc — `about.md` correctly declines to restate that as current and flags it
  `[[confirm current example with INZBC]]` instead of copying it forward.
- **Executive Council names/bios** — sourced from the live site (27 Jul 2026 read), per the
  discovery-phase guardrail (OI-6: never invent board names, verify at build time). Already
  flagged `[[proposed — pending INZBC confirmation]]` in `about.md`; no change needed here,
  noting it only so this doc's coverage of the About page is complete.
- **Typography/colour application** — Big Shoulders uppercase for the About hero headline
  and section headings, Merriweather for body (history, mission, "what we do" copy),
  consistent with the homepage. Navy Blue base; no strong rationale yet for accent colour
  use on this page specifically (About is credibility-led, not conversion-led, so heavier
  accent/CTA colour may be wrong here — flagged as an open call, not decided).

## Open items — need Sunil/INZBC before build

1. Reconcile the homepage hero headline: `home.md`'s "New Zealand's gateway to the India
   opportunity" vs. the wireframe/Wix's "New Zealand's Gateway to India."
2. Reconcile the two-way trade figure: $3.68b (migration guide) vs. NZ$3.95bn (FTA corpus,
   verified against MFAT Tier 1 sources 28 Jul 2026). Confirm which is current; do not
   average or silently pick one.
3. Confirm whether the 300,000 Indian diaspora figure is safe to publish, and its source —
   currently withheld because it isn't in the verified FTA corpus.
4. Reconcile the member count: "160+" (`docs/discovery.md` site audit) vs. "200+"
   (`home.md` proposed draft).
5. Supply the logo asset library (svg/png/jpg, all three variants) — none exist in this
   repo yet.
6. Supply or commission photography matching the brand direction (vibrant, light,
   positive) — none sourced yet.
7. Confirm CTA-colour (Tangerine) and FTA-band gradient (Lavender→Blue→Navy) choices above
   — reasonable applications of the palette, not documented requirements.
8. Decide the palette, three-way: this table (Brand Guidelines), the live `inzbc.org`
   colours, or the provisional bicultural palette above — see `inzbc-studio-site`'s
   `docs/live-site-extract.md` for the full comparison.
