"""FTA Opportunity Explainer's source corpus - structured form of docs/fta-source-corpus.md.

Every fact here traces to that doc, which traces to the citations recorded on each entry. Do not
add a fact here that isn't already sourced in docs/fta-source-corpus.md; update that doc first,
then mirror it here, the same relationship apps/sip/collector/source_register.py has to
SIP-185. Last mirrored against the doc as checked there on 22 Jul 2026.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from enum import Enum

FTA_STATUS_LINE = (
    "NZ-India FTA signed 27 April 2026 (negotiations concluded 22 Dec 2025). Not yet in force - "
    "awaiting domestic ratification in both countries. Benefits are agreed, applying once the "
    "FTA enters into force, not current access."
)

# Settled 9 Aug 2026 (#219, docs/client-answers-relayed-2026-08-09.md "FTA sectors: goods first,
# services second"): the three previously-conflicting sector lists are resolved by scope, not by
# picking one - Sunil's ten broad sectors and this corpus's tariff-outcome categories are
# different kinds of thing. Build now on the goods sectors already sourced (these four category
# values, used by CORPUS entries below). Add next, once sourced from the agreement text before
# publication: tourism, education, investment. Defence and security, immigration and sports are
# not dropped, but are not sourced and do not gate the build (BR2: nothing is written about a
# sector until it has a source). No longer provisional/pending INZBC - this list will grow as
# "add next" items get sourced, not on further confirmation.
SECTORS_IN_SCOPE: tuple[str, ...] = (
    "Agriculture",
    "Cross-sector",
    "Dairy",
    "Infrastructure",
)


@dataclass(frozen=True)
class SourceDocument:
    name: str
    url: str
    tier: int  # 1 = official, citable for tariff/market-access facts; 2 = context only
    automated_fetch_blocked: bool = False
    note: str | None = None


TIER_1_SOURCES: tuple[SourceDocument, ...] = (
    SourceDocument(
        "MFAT NZ-India FTA hub",
        "https://www.mfat.govt.nz/en/trade/free-trade-agreements/free-trade-agreements-concluded-but-not-in-force/new-zealand-india-free-trade-agreement",
        tier=1,
    ),
    SourceDocument(
        "MFAT negotiations timeline",
        "https://www.mfat.govt.nz/en/trade/free-trade-agreements/free-trade-agreements-concluded-but-not-in-force/new-zealand-india-free-trade-agreement/timeline-of-negotiations",
        tier=1,
    ),
    SourceDocument(
        "MFAT agreement text and tariff schedules",
        "https://www.mfat.govt.nz/en/trade/free-trade-agreements/free-trade-agreements-concluded-but-not-in-force/new-zealand-india-free-trade-agreement/text-of-the-agreement",
        tier=1,
        note=(
            "Consolidated text + 20 chapters. Appendix 2A-1 to Annex 2A is India's schedule of "
            "tariff commitments, Appendix 2A-2 is New Zealand's; Annex 2B covers economic "
            "cooperation/TRQs; 6 side letters, one of them 'Dairy Consultations'."
        ),
    ),
    SourceDocument(
        "MFAT National Interest Analysis (NIA)",
        "https://www.mfat.govt.nz/assets/Trade-agreements/NZ-India-FTA/NZ-India-FTA-National-Interest-Analysis-NIA.pdf",
        tier=1,
        note="Covers tariff outcomes, economic modelling, and treaty obligations chapter by chapter.",
    ),
    SourceDocument(
        "Ministry of Commerce & Industry / PIB press note",
        "https://www.pib.gov.in/PressNoteDetails.aspx?NoteId=158370",
        tier=1,
        automated_fetch_blocked=True,
        note="403/bot protection as of 22 Jul 2026 - read manually before citing India-side-only figures from this.",
    ),
    SourceDocument(
        "Department of Commerce factsheet",
        "https://www.commerce.gov.in/files/2026-04/final_1.pdf",
        tier=1,
        automated_fetch_blocked=True,
        note="403/bot protection as of 22 Jul 2026 - read manually before citing India-side-only figures from this.",
    ),
)

TIER_2_SOURCES: tuple[SourceDocument, ...] = (
    SourceDocument("Asia Media Centre explainer", "", tier=2, note="Context/narrative only, never the source of a number."),
    SourceDocument("USDA GAIN report", "", tier=2, note="Context/narrative only, never the source of a number."),
    SourceDocument("Lexology / Mondaq law-firm summaries", "", tier=2, note="Context/narrative only, never the source of a number."),
)


class TradeDirection(str, Enum):
    """Which way the goods move. A tariff outcome only makes sense read against one direction -
    "NZ removes all tariffs on Indian imports" and "India phases out its tariff on NZ wool" are
    both true and both in the corpus, but they are not the same fact from the same country's
    tariff schedule.
    """

    NZ_EXPORTS_TO_INDIA = "NZ exports to India"  # India's tariff schedule applies
    INDIA_EXPORTS_TO_NZ = "India exports to NZ"  # NZ's tariff schedule applies


@dataclass(frozen=True)
class TariffOutcome:
    """One sourced fact from the FTA. `confirmed=False` entries exist so the Explainer can
    represent "known but not citable yet" rather than omitting the topic entirely - it must
    never present one as a confirmed figure (see explainer.py).

    The structured tariff fields (#185) exist because `treatment` alone is prose the Explainer
    cannot answer a tariff question *from* - a member asking "what's the current tariff on wool"
    needs a queryable value, not a sentence to re-parse. They are free text (`str | None`), not
    a parsed percentage, because the source itself states some as ranges ("5.5%-11%") and others
    as within-quota figures that aren't reducible to one number without losing meaning - storing
    exactly what the Tier 1 source says is more honest than forcing a false precision. All four
    are `None` for cross-sector/aggregate entries (there is no single product tariff line for
    "95% of exports") and for entries where the source doesn't give a product-specific figure
    (see docs/fta-source-corpus.md's "Not in this table" list) - `None` there means "not yet
    sourced", not "zero" or "unchanged".
    """

    # Stable identifier, assigned once and never reused. Callers key React lists and DOM ids
    # off this rather than `topic`: topic is prose (spaces, punctuation, parentheses), so it
    # makes an invalid HTML id and an unstable key if the wording is ever revised. Follows the
    # SIP-185 source-id convention (NZ-OFF-001), not a slug, so an editorial change to `topic`
    # cannot silently change an entry's identity.
    id: str
    topic: str
    sector: str
    treatment: str
    confirmed: bool
    citation: str
    verified_at: date
    notes: str | None = None
    # 1 = the citation is a Tier 1 official/treaty source; 2 = industry/secondary reporting.
    # Drives the Information Confidence Standard rating (docs/information-standard.md).
    source_tier: int = 1
    direction: TradeDirection | None = None
    current_tariff: str | None = None  # pre-FTA baseline, as stated by the source
    fta_commencement_tariff: str | None = None  # rate at entry into force ("day 1")
    staged_reductions: str | None = None  # the phase-in path between commencement and final
    final_tariff: str | None = None
    implementation_period_years: int | None = None  # 0 = immediate/day-one


CORPUS: tuple[TariffOutcome, ...] = (
    TariffOutcome(
        id="FTA-001",
        topic="NZ tariffs on Indian imports",
        sector="Cross-sector",
        treatment="New Zealand removes all tariffs on Indian imports from day one (100%).",
        confirmed=True,
        citation="MFAT National Interest Analysis, Executive Summary",
        verified_at=date(2026, 7, 22),
        direction=TradeDirection.INDIA_EXPORTS_TO_NZ,
    ),
    TariffOutcome(
        id="FTA-002",
        topic="India tariffs on NZ exports (overall)",
        sector="Cross-sector",
        treatment=(
            "95% of NZ's current exports to India get tariff elimination or reduction over "
            "time: 57% duty-free from day one, rising to 82% once fully implemented, the "
            "remaining 13% subject to sharp cuts."
        ),
        confirmed=True,
        citation="MFAT National Interest Analysis, section 1.3",
        notes="This is the figure to cite for NZ audiences.",
        verified_at=date(2026, 7, 22),
        direction=TradeDirection.NZ_EXPORTS_TO_INDIA,
    ),
    TariffOutcome(
        id="FTA-003",
        topic="India tariff-line count (~70% of ~12,500 lines)",
        sector="Cross-sector",
        treatment=(
            "Secondary reporting says India opened ~70.03% of its ~12,500 tariff lines and "
            "excluded ~29.97%, with the excluded lines said to represent only ~5% of bilateral "
            "import value."
        ),
        confirmed=False,
        citation="Secondary reporting only - not yet confirmed against a Tier 1 document",
        source_tier=2,
        notes=(
            "The two Indian government primary sources that would confirm this (PIB press "
            "note, Dept of Commerce factsheet) block automated fetch. Do not cite this figure "
            "until someone opens those links in a browser and confirms it directly."
        ),
        verified_at=date(2026, 7, 22),
        direction=TradeDirection.NZ_EXPORTS_TO_INDIA,
    ),
    TariffOutcome(
        id="FTA-004",
        topic="Forestry",
        sector="Agriculture",
        treatment="Tariff eliminated on ~95%+ of exports at entry into force.",
        confirmed=True,
        citation="MFAT National Interest Analysis, Key Tariff Outcomes table, p.13",
        verified_at=date(2026, 8, 10),
        direction=TradeDirection.NZ_EXPORTS_TO_INDIA,
        current_tariff="5.5%-11%",
        fta_commencement_tariff="Eliminated on almost all goods",
        staged_reductions="Remainder of forestry trade interests phased out over 5-7 years",
        final_tariff="0% (eliminated)",
        implementation_period_years=7,
    ),
    TariffOutcome(
        id="FTA-005",
        topic="Wool",
        sector="Agriculture",
        treatment="Tariff eliminated day one.",
        confirmed=True,
        citation="MFAT National Interest Analysis, Key Tariff Outcomes table, p.13",
        verified_at=date(2026, 8, 10),
        direction=TradeDirection.NZ_EXPORTS_TO_INDIA,
        current_tariff="2.75%",
        fta_commencement_tariff="0% (eliminated day 1)",
        final_tariff="0% (eliminated)",
        implementation_period_years=0,
    ),
    TariffOutcome(
        id="FTA-006",
        topic="Sheepmeat",
        sector="Agriculture",
        treatment="Tariff eliminated day one.",
        confirmed=True,
        citation="MFAT National Interest Analysis, Key Tariff Outcomes table, p.13",
        verified_at=date(2026, 8, 10),
        direction=TradeDirection.NZ_EXPORTS_TO_INDIA,
        current_tariff="33%",
        fta_commencement_tariff="0% (eliminated day 1)",
        final_tariff="0% (eliminated)",
        implementation_period_years=0,
    ),
    TariffOutcome(
        id="FTA-007",
        topic="Coal",
        sector="Infrastructure",
        treatment="Tariff eliminated day one.",
        confirmed=True,
        citation="MFAT National Interest Analysis, Key Tariff Outcomes table, p.13",
        verified_at=date(2026, 8, 10),
        direction=TradeDirection.NZ_EXPORTS_TO_INDIA,
        current_tariff="2.75%",
        fta_commencement_tariff="0% (eliminated day 1)",
        final_tariff="0% (eliminated)",
        implementation_period_years=0,
    ),
    TariffOutcome(
        id="FTA-008",
        topic="Fish and seafood",
        sector="Agriculture",
        treatment="Tariff phased out over 7 years.",
        confirmed=True,
        citation="MFAT National Interest Analysis, Key Tariff Outcomes table, p.13",
        verified_at=date(2026, 8, 10),
        direction=TradeDirection.NZ_EXPORTS_TO_INDIA,
        current_tariff="33%",
        staged_reductions="Phased out over 7 years",
        final_tariff="0% (eliminated on most goods)",
        notes="Table says 'most goods' over 7 years, not all - do not present as a blanket elimination.",
        implementation_period_years=7,
    ),
    TariffOutcome(
        id="FTA-009",
        topic="Kiwifruit",
        sector="Agriculture",
        treatment=(
            "New quota access; NZ is first mover. Tariff-free within quota (6,250 tonnes from "
            "day 1, growing to 15,900 tonnes over 6 years); 50% tariff reduction (to 16.5%) "
            "outside quota, from day 1."
        ),
        confirmed=True,
        citation="MFAT National Interest Analysis, Key Tariff Outcomes table, p.13",
        verified_at=date(2026, 8, 10),
        direction=TradeDirection.NZ_EXPORTS_TO_INDIA,
        current_tariff="33%",
        fta_commencement_tariff="0% within quota (6,250t); 16.5% outside quota",
        staged_reductions="In-quota volume grows from 6,250t to 15,900t over 6 years",
        final_tariff="0% within quota (up to 15,900t); 16.5% outside quota",
        implementation_period_years=6,
        notes=(
            "Split from a combined 'Kiwifruit and apples' entry - apples has a different "
            "structured outcome (never fully eliminated, see FTA-019) and combining the two "
            "under one current/final tariff pair would misrepresent one of them."
        ),
    ),
    TariffOutcome(
        id="FTA-010",
        topic="Wine",
        sector="Agriculture",
        treatment="Tariff reduced at entry into force, cut further over 10 years.",
        confirmed=True,
        citation="MFAT National Interest Analysis, Key Tariff Outcomes table, p.13",
        verified_at=date(2026, 8, 10),
        direction=TradeDirection.NZ_EXPORTS_TO_INDIA,
        current_tariff="150%",
        staged_reductions="66-83% reduction over 10 years from entry into force",
        final_tariff="25% or 50% (depending on price tier)",
        notes=(
            "Also carries a most-favoured-nation-style clause: any better tariff outcome India "
            "offers a later FTA partner is automatically extended to New Zealand."
        ),
        implementation_period_years=10,
    ),
    TariffOutcome(
        id="FTA-011",
        topic="Manuka honey",
        sector="Agriculture",
        treatment="Tariff cut 75% over 5 years; NZ is first mover.",
        confirmed=True,
        citation="MFAT National Interest Analysis, Key Tariff Outcomes table, p.13",
        verified_at=date(2026, 8, 10),
        direction=TradeDirection.NZ_EXPORTS_TO_INDIA,
        current_tariff="66%",
        staged_reductions="75% reduction over 5 years, within a 200 tonne quota",
        final_tariff="16.5%",
        implementation_period_years=5,
    ),
    TariffOutcome(
        id="FTA-012",
        topic="Cherries and avocados",
        sector="Agriculture",
        treatment="Tariff eliminated over 10 years.",
        confirmed=True,
        citation="MFAT National Interest Analysis, Key Tariff Outcomes table, p.13",
        verified_at=date(2026, 8, 10),
        direction=TradeDirection.NZ_EXPORTS_TO_INDIA,
        current_tariff="33%",
        staged_reductions="Phased elimination over 10 years",
        final_tariff="0% (eliminated)",
        implementation_period_years=10,
        notes=(
            "Split from a combined 'Cherries, avocados, blueberries, persimmons' entry - "
            "blueberries and persimmons don't have their own line in the Key Tariff Outcomes "
            "table (see FTA-020) and don't share this confirmed 33%/10-year figure by default."
        ),
    ),
    TariffOutcome(
        id="FTA-013",
        topic="Dairy - milk, cheese, butter",
        sector="Dairy",
        treatment=(
            "Excluded from India's tariff concessions - milk, cheese and butter get no tariff "
            "elimination or reduction. This is not a blanket dairy exclusion: see the separate "
            "bulk infant formula, peptones and albumins entries."
        ),
        confirmed=True,
        citation="MFAT National Interest Analysis",
        notes=(
            "Reporting also calls this NZ's first FTA to exclude major dairy products. That "
            "comparison is Tier 2, is not a tariff fact, and no Tier 1 source establishes it, "
            "so it is deliberately not asserted here. The agreement carries a 'Dairy "
            "Consultations' side letter, so the exclusion is not necessarily permanent. Excluded "
            "products don't get a current-tariff callout in the Key Tariff Outcomes table - "
            "current_tariff stays unset rather than guessed."
        ),
        verified_at=date(2026, 7, 22),
        direction=TradeDirection.NZ_EXPORTS_TO_INDIA,
    ),
    TariffOutcome(
        id="FTA-014",
        topic="Dairy - bulk infant formula and other dairy-based food preparations",
        sector="Dairy",
        treatment="Tariff phases out over 7 years.",
        confirmed=True,
        citation="MFAT National Interest Analysis, Key Tariff Outcomes table, p.13",
        verified_at=date(2026, 8, 10),
        direction=TradeDirection.NZ_EXPORTS_TO_INDIA,
        current_tariff="33%",
        staged_reductions="Phased out over 7 years",
        final_tariff="0% (eliminated)",
        implementation_period_years=7,
    ),
    TariffOutcome(
        id="FTA-015",
        topic="Dairy - peptones",
        sector="Dairy",
        treatment="Tariff phases out over 7 years.",
        confirmed=True,
        citation="MFAT National Interest Analysis",
        notes=(
            "Peptones has no own row in the Key Tariff Outcomes table - only bulk infant "
            "formula does (FTA-014, 33% current). Do not assume peptones shares that baseline; "
            "current_tariff stays unset until a peptones-specific figure is found."
        ),
        verified_at=date(2026, 7, 22),
        direction=TradeDirection.NZ_EXPORTS_TO_INDIA,
        staged_reductions="Phased out over 7 years",
        final_tariff="0% (eliminated)",
        implementation_period_years=7,
    ),
    TariffOutcome(
        id="FTA-016",
        topic="Dairy - albumins",
        sector="Dairy",
        treatment="50% tariff cut within a quota.",
        confirmed=True,
        citation="MFAT National Interest Analysis, Key Tariff Outcomes table, p.13",
        verified_at=date(2026, 8, 10),
        direction=TradeDirection.NZ_EXPORTS_TO_INDIA,
        current_tariff="22%",
        fta_commencement_tariff="11% for 1,000 tonnes",
        staged_reductions="In-quota volume grows from 1,000t to 3,000t over 5 years",
        final_tariff="11% (within quota, up to 3,000t)",
        implementation_period_years=5,
    ),
    TariffOutcome(
        id="FTA-019",
        topic="Apples",
        sector="Agriculture",
        treatment=(
            "New quota access; NZ is first mover. 50% tariff reduction (to 25%) for 32,500 "
            "tonnes from day 1, growing to 45,000 tonnes over 6 years. Not fully eliminated."
        ),
        confirmed=True,
        citation="MFAT National Interest Analysis, Key Tariff Outcomes table, p.13",
        verified_at=date(2026, 8, 10),
        direction=TradeDirection.NZ_EXPORTS_TO_INDIA,
        current_tariff="50%",
        fta_commencement_tariff="25% for 32,500 tonnes",
        staged_reductions="In-quota volume grows from 32,500t to 45,000t over 6 years",
        final_tariff="25% (within quota, up to 45,000t) - never fully eliminated",
        implementation_period_years=6,
        notes="Split from a combined 'Kiwifruit and apples' entry - see FTA-009's note.",
    ),
    TariffOutcome(
        id="FTA-020",
        topic="Blueberries and persimmons",
        sector="Agriculture",
        treatment="Phased tariff elimination.",
        confirmed=True,
        citation="MFAT National Interest Analysis, section 1.3",
        notes=(
            "Split from a combined entry with cherries/avocados. The NIA prose bundles "
            "blueberries and persimmons with cherries/avocados as 'phased tariff elimination,' "
            "but the Key Tariff Outcomes table only breaks out Cherries and Avocados by name "
            "(see FTA-012) - no product-specific current/final tariff figure exists for "
            "blueberries or persimmons yet. The qualitative claim stays confirmed; the "
            "structured fields stay unset rather than borrowing FTA-012's numbers."
        ),
        verified_at=date(2026, 7, 22),
        direction=TradeDirection.NZ_EXPORTS_TO_INDIA,
    ),
    TariffOutcome(
        id="FTA-017",
        topic="Two-way trade value",
        sector="Cross-sector",
        treatment=(
            "Two-way goods and services trade totalled approximately NZ$3.95bn in the year "
            "ended December 2025."
        ),
        confirmed=True,
        citation="MFAT key facts on NZ-India trade",
        notes="Publish the period with the figure; an undated 'annually' goes stale silently.",
        verified_at=date(2026, 7, 28),
    ),
    TariffOutcome(
        id="FTA-018",
        topic="Independent GDP modelling",
        sector="Cross-sector",
        treatment=(
            "Motu modelling (cited in the NIA) projects NZ GDP 0.07% ($401m, 2024 dollars) "
            "above a non-FTA baseline by 2037, growing to 0.1% ($657.7m) by 2050."
        ),
        confirmed=True,
        citation="MFAT National Interest Analysis (Motu modelling)",
        notes="Context for an answer, not a tariff fact - keep separate from product-level citations.",
        verified_at=date(2026, 7, 22),
    ),
)


def stale_entries(
    entries: Iterable[TariffOutcome], as_of: date, review_after_days: int
) -> list[TariffOutcome]:
    """Entries last verified more than `review_after_days` before `as_of`.

    `review_after_days` has no default on purpose - the review cadence is a business decision
    INZBC hasn't set (see docs/modules/fta-centre.md's dependencies); this only provides the
    mechanism once that number exists.
    """
    return [entry for entry in entries if (as_of - entry.verified_at).days > review_after_days]
