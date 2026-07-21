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
- MFAT **National Interest Analysis** and sector fact sheets (when available).
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

## Reported outcomes to verify against Tier 1 (do NOT publish until confirmed)
> Sourced from a news summary, flagged for verification against MFAT fact sheets/schedules.
- Zero-duty access for ~100% of Indian exports into NZ.
- India opening ~70% of tariff lines, covering ~95% of current NZ imports.
- NZ winners reported: wool, wood, coal, wine, premium fruit (avocados, blueberries), agri-inputs.
- **Dairy exclusion** — milk, cheese, butter reportedly left out. Material caveat for an NZ
  trade body; must be stated accurately, not glossed.
- Two-way trade ~NZ$3.95bn annually.

## Member-facing mapping (how a query becomes a sourced answer)
Member selects sector/product → tool matches to the relevant tariff outcome in the schedule →
returns: the agreed treatment, its in-force status, the citation, and a "next steps / talk to
INZBC" prompt. Sectors most relevant to INZBC members (agriculture, dairy, education, finance,
infrastructure per the About page) get first-pass coverage; dairy's exclusion is handled
explicitly rather than omitted.

## Open items
- Pull the official agreement text + tariff schedules from MFAT once published (Tier 1 gap today).
- Confirm the reported figures above against MFAT fact sheets before any go-live.
- INZBC to confirm which member sectors to prioritise in the first release.
