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


@dataclass(frozen=True)
class TariffOutcome:
    """One sourced fact from the FTA. `confirmed=False` entries exist so the Explainer can
    represent "known but not citable yet" rather than omitting the topic entirely - it must
    never present one as a confirmed figure (see explainer.py).
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


CORPUS: tuple[TariffOutcome, ...] = (
    TariffOutcome(
        id="FTA-001",
        topic="NZ tariffs on Indian imports",
        sector="Cross-sector",
        treatment="New Zealand removes all tariffs on Indian imports from day one (100%).",
        confirmed=True,
        citation="MFAT National Interest Analysis, Executive Summary",
        verified_at=date(2026, 7, 22),
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
    ),
    TariffOutcome(
        id="FTA-004",
        topic="Forestry",
        sector="Agriculture",
        treatment="Tariff eliminated on ~95%+ of exports at entry into force.",
        confirmed=True,
        citation="MFAT National Interest Analysis, key tariff outcomes table",
        verified_at=date(2026, 7, 22),
    ),
    TariffOutcome(
        id="FTA-005",
        topic="Wool",
        sector="Agriculture",
        treatment="Tariff eliminated day one.",
        confirmed=True,
        citation="MFAT National Interest Analysis, key tariff outcomes table",
        verified_at=date(2026, 7, 22),
    ),
    TariffOutcome(
        id="FTA-006",
        topic="Sheepmeat",
        sector="Agriculture",
        treatment="Tariff eliminated day one.",
        confirmed=True,
        citation="MFAT National Interest Analysis, key tariff outcomes table",
        verified_at=date(2026, 7, 22),
    ),
    TariffOutcome(
        id="FTA-007",
        topic="Coal",
        sector="Infrastructure",
        treatment="Tariff eliminated day one.",
        confirmed=True,
        citation="MFAT National Interest Analysis, key tariff outcomes table",
        verified_at=date(2026, 7, 22),
    ),
    TariffOutcome(
        id="FTA-008",
        topic="Fish and seafood",
        sector="Agriculture",
        treatment="Tariff phased out over 7 years.",
        confirmed=True,
        citation="MFAT National Interest Analysis, key tariff outcomes table",
        verified_at=date(2026, 7, 22),
    ),
    TariffOutcome(
        id="FTA-009",
        topic="Kiwifruit and apples",
        sector="Agriculture",
        treatment="New quota access; NZ is first mover.",
        confirmed=True,
        citation="MFAT National Interest Analysis, key tariff outcomes table",
        verified_at=date(2026, 7, 22),
    ),
    TariffOutcome(
        id="FTA-010",
        topic="Wine",
        sector="Agriculture",
        treatment="Tariff reduced at entry into force, cut further over 10 years.",
        confirmed=True,
        citation="MFAT National Interest Analysis, key tariff outcomes table",
        verified_at=date(2026, 7, 22),
    ),
    TariffOutcome(
        id="FTA-011",
        topic="Manuka honey",
        sector="Agriculture",
        treatment="Tariff cut 75% over 5 years; NZ is first mover.",
        confirmed=True,
        citation="MFAT National Interest Analysis, key tariff outcomes table",
        verified_at=date(2026, 7, 22),
    ),
    TariffOutcome(
        id="FTA-012",
        topic="Cherries, avocados, blueberries, persimmons",
        sector="Agriculture",
        treatment="Phased tariff elimination.",
        confirmed=True,
        citation="MFAT National Interest Analysis, key tariff outcomes table",
        verified_at=date(2026, 7, 22),
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
            "Consultations' side letter, so the exclusion is not necessarily permanent."
        ),
        verified_at=date(2026, 7, 22),
    ),
    TariffOutcome(
        id="FTA-014",
        topic="Dairy - bulk infant formula and other dairy-based food preparations",
        sector="Dairy",
        treatment="Tariff phases out over 7 years.",
        confirmed=True,
        citation="MFAT National Interest Analysis",
        verified_at=date(2026, 7, 22),
    ),
    TariffOutcome(
        id="FTA-015",
        topic="Dairy - peptones",
        sector="Dairy",
        treatment="Tariff phases out over 7 years.",
        confirmed=True,
        citation="MFAT National Interest Analysis",
        verified_at=date(2026, 7, 22),
    ),
    TariffOutcome(
        id="FTA-016",
        topic="Dairy - albumins",
        sector="Dairy",
        treatment="50% tariff cut within a quota.",
        confirmed=True,
        citation="MFAT National Interest Analysis",
        verified_at=date(2026, 7, 22),
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
