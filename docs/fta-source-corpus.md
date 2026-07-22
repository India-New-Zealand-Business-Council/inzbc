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
- The **agreement text** and annexes (tariff schedules) once MFAT publishes them.
- MFAT **National Interest Analysis (NIA)** — now available:
  https://www.mfat.govt.nz/assets/Trade-agreements/NZ-India-FTA/NZ-India-FTA-National-Interest-Analysis-NIA.pdf
  (published ~2026; covers tariff outcomes, economic modelling, and treaty obligations chapter
  by chapter). Sector fact sheets still to check for separately.
- Indian government primary sources: Ministry of Commerce & Industry / PIB release
  (PIB doc dated 27 Apr 2026) and India's published FTA summary.

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
  the remaining 13% subject to sharp cuts (NIA §1.3). The "~70% of tariff lines" figure quoted
  in early news summaries describes India's overall schedule structure (~70.03% of India's
  ~12,500 tariff lines opened) rather than the NZ-export-coverage figure above — cite the 95%
  export-coverage figure for NZ audiences; the tariff-line-count figure needs an Indian
  government primary source (PIB/Dept of Commerce) before citing, not yet checked.
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
- Pull the official agreement text + full tariff schedules from MFAT once published (NIA gives
  headline outcomes, not the line-by-line schedule — still a Tier 1 gap).
- Get an Indian government primary source (PIB / Dept of Commerce) for the ~70% tariff-line
  figure before citing it; do not carry the news-summary version forward.
- INZBC to confirm which member sectors to prioritise in the first release.
