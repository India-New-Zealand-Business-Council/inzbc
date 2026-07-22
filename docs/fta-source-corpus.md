# FTA Opportunity Explainer — Source Corpus Plan

Defines the sourced material the FTA Explainer (page 7) draws on, and the rules for what
counts as citable fact vs context. The Explainer must never invent tariff lines or FTA terms;
every substantive claim traces to an official document below.

## Status of the agreement (as at July 2026)
- NZ–India FTA **signed 27 April 2026**; negotiations concluded 22 Dec 2025.
- **Not yet in force** — awaiting domestic ratification in both countries.
- Implication for the tool: it must state this status plainly. Benefits are described as
  "agreed, applying once the FTA enters into force", not as current access. A single status
  line should appear on every answer.

## Source tiers

**Tier 1 — official, citable for tariff/market-access facts**
- MFAT NZ–India FTA hub: https://www.mfat.govt.nz/en/trade/free-trade-agreements/free-trade-agreements-concluded-but-not-in-force/new-zealand-india-free-trade-agreement
- MFAT negotiations timeline (same path `/timeline-of-negotiations`).
- The **agreement text and full tariff schedules are now published** — confirmed at
  https://www.mfat.govt.nz/en/trade/free-trade-agreements/free-trade-agreements-concluded-but-not-in-force/new-zealand-india-free-trade-agreement/text-of-the-agreement
  (consolidated text + 20 chapters individually; Annex 2A-1 is India's tariff schedule,
  Annex 2A-2 is New Zealand's; Annex 2B covers economic cooperation/TRQs; 6 side letters
  including one on dairy). This closes the "no line-by-line schedule" gap — the Explainer
  should cite Annex 2A directly for product-level tariff lines, not just the NIA summary.
- MFAT **National Interest Analysis (NIA)** — now available:
  https://www.mfat.govt.nz/assets/Trade-agreements/NZ-India-FTA/NZ-India-FTA-National-Interest-Analysis-NIA.pdf
  (published ~2026; covers tariff outcomes, economic modelling, and treaty obligations chapter
  by chapter). Sector fact sheets still to check for separately.
- Indian government primary sources: Ministry of Commerce & Industry / PIB release
  (PIB doc dated 27 Apr 2026, https://www.pib.gov.in/PressNoteDetails.aspx?NoteId=158370) and
  the Dept of Commerce factsheet (https://www.commerce.gov.in/files/2026-04/final_1.pdf).
  **Both blocked automated fetch (403/bot protection) as of 22 Jul 2026** — read manually in a
  browser before citing India-side-only figures (e.g. tariff-line counts) from these.

**Tier 2 — context/narrative only, never the source of a number**
- Asia Media Centre explainer, USDA GAIN report, law-firm summaries (Lexology, Mondaq).
- Useful for plain-language framing and sector commentary; every figure they cite is
  re-checked against Tier 1 before the Explainer repeats it.

## Rules the Explainer follows
1. Tariff lines, percentages, in-force dates, and exclusions come from **Tier 1 only**.
2. Every answer shows its citation (document + link) and the "not yet in force" status.
3. If the corpus doesn't cover a member's question, the tool says so and routes them to
   INZBC — it does not guess.
4. Sector claims are scoped to what the official schedules actually say for that product.

## Verified against Tier 1 (MFAT NIA, checked 22 Jul 2026)
- **NZ side:** New Zealand removes all tariffs on Indian imports from day one — confirmed,
  100% (NIA §Executive Summary, in line with NZ's recent FTA practice).
- **India side, for NZ exporters:** 95% of NZ's current exports to India get tariff elimination
  or reduction over time — 57% duty-free from day one, rising to 82% once fully implemented,
  the remaining 13% subject to sharp cuts (NIA §1.3, Tier 1, confirmed). This is the figure to
  cite for NZ audiences.
- **"~70% of tariff lines" figure — still not Tier-1-confirmed.** Secondary reporting says
  India opened ~70.03% of its ~12,500 tariff lines and excluded ~29.97%, with the excluded
  lines said to represent only ~5% of bilateral import value (which would reconcile with the
  95% export-coverage figure above). But this figure traces back to news summaries and a
  trading-blog aggregation, not a document I've read directly — the two Indian government
  primary sources that would confirm it (PIB press note, Dept of Commerce factsheet) blocked
  automated fetch. **Do not cite the tariff-line-count figure in the Explainer until someone
  opens those two links in a browser and confirms the number directly.**
- NZ winners **confirmed** in the NIA's key tariff outcomes table: forestry (tariff eliminated
  on ~95%+ of exports at entry into force), wool (day 1), sheepmeat (day 1), coal (day 1), fish
  & seafood (phased over 7 years), kiwifruit and apples (new quota access, NZ first mover),
  wine (reduced at entry into force, cut further over 10 years), mānuka honey (75% cut over 5
  years, NZ first mover), cherries/avocados/blueberries/persimmons (phased elimination).
  "Agri-inputs" as a category is not named in the NIA outcomes table — treat as unconfirmed
  until a specific product/tariff line is found.
- **Dairy exclusion confirmed** — milk, cheese and butter are excluded; this is NZ's first FTA
  to exclude major dairy products (NIA + corroborating reporting). Not a blanket dairy
  exclusion though: bulk infant formula and other dairy-based food preparations phase out over
  7 years, peptones phase out over 7 years, and albumins get a 50% cut within a quota. The
  Explainer must distinguish "core dairy (milk/cheese/butter) excluded" from "some dairy-based
  preparations get phased access" — do not collapse these into one line.
- Two-way trade ~NZ$3.95bn annually — confirmed on the MFAT FTA hub page.
- **New, not previously in this doc:** independent modelling (Motu, cited in the NIA) projects
  NZ GDP 0.07% ($401m, 2024 dollars) above non-FTA baseline by 2037, growing to 0.1% ($657.7m)
  by 2050. Useful context for an Explainer answer, not a tariff fact — keep separate from
  product-level citations.

## Member-facing mapping (how a query becomes a sourced answer)
Member selects sector/product → tool matches to the relevant tariff outcome in the schedule →
returns: the agreed treatment, its in-force status, the citation, and a "next steps / talk to
INZBC" prompt. Sectors most relevant to INZBC members (agriculture, dairy, education, finance,
infrastructure per the About page) get first-pass coverage; dairy's exclusion is handled
explicitly rather than omitted.

## Open items
- Manually open the PIB press note and Dept of Commerce factsheet (links above) to confirm the
  ~70% tariff-line figure before it's cited anywhere — automated fetch is blocked on both.
- Read Annex 2A-1/2A-2 (now published) for any product-level tariff lines the Explainer needs
  beyond what the NIA's summary table already covers.
- INZBC to confirm which member sectors to prioritise in the first release.
