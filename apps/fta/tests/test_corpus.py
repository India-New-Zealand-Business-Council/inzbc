from __future__ import annotations

import re
from datetime import date

from apps.fta.corpus import (
    CORPUS,
    TIER_1_SOURCES,
    TIER_2_SOURCES,
    TariffOutcome,
    TradeDirection,
    stale_entries,
)


def test_corpus_entries_all_have_a_citation() -> None:
    assert CORPUS
    assert all(entry.citation for entry in CORPUS)


def test_unconfirmed_tariff_line_figure_is_marked_unconfirmed() -> None:
    entry = next(e for e in CORPUS if "tariff-line count" in e.topic)
    assert entry.confirmed is False


def test_dairy_exclusion_is_not_collapsed_into_a_blanket_exclusion() -> None:
    # docs/fta-source-corpus.md is explicit that milk/cheese/butter are excluded but bulk
    # infant formula, peptones and albumins get separate, non-zero treatment - these must stay
    # as distinct entries, not folded into one "dairy excluded" line.
    dairy_topics = {entry.topic for entry in CORPUS if entry.sector == "Dairy"}
    assert "Dairy - milk, cheese, butter" in dairy_topics
    assert "Dairy - bulk infant formula and other dairy-based food preparations" in dairy_topics
    assert "Dairy - peptones" in dairy_topics
    assert "Dairy - albumins" in dairy_topics


def test_tier_1_sources_include_the_two_blocked_india_documents() -> None:
    blocked = [s for s in TIER_1_SOURCES if s.automated_fetch_blocked]
    assert {s.name for s in blocked} == {
        "Ministry of Commerce & Industry / PIB press note",
        "Department of Commerce factsheet",
    }


def test_tier_2_sources_are_marked_context_only() -> None:
    assert TIER_2_SOURCES
    assert all(s.tier == 2 for s in TIER_2_SOURCES)


def test_stale_entries_flags_only_entries_past_the_window() -> None:
    fresh = TariffOutcome(
        id="TEST-FRESH",
        topic="Fresh",
        sector="Cross-sector",
        treatment="t",
        confirmed=True,
        citation="c",
        verified_at=date(2026, 7, 1),
    )
    stale = TariffOutcome(
        id="TEST-STALE",
        topic="Stale",
        sector="Cross-sector",
        treatment="t",
        confirmed=True,
        citation="c",
        verified_at=date(2026, 1, 1),
    )

    result = stale_entries([fresh, stale], as_of=date(2026, 7, 22), review_after_days=90)

    assert [entry.topic for entry in result] == ["Stale"]


def test_stale_entries_empty_when_nothing_past_the_window() -> None:
    entries = [
        TariffOutcome(
            id="TEST-FRESH",
            topic="Fresh",
            sector="Cross-sector",
            treatment="t",
            confirmed=True,
            citation="c",
            verified_at=date(2026, 7, 20),
        )
    ]
    assert stale_entries(entries, as_of=date(2026, 7, 22), review_after_days=90) == []


def test_every_entry_has_a_unique_stable_id() -> None:
    ids = [entry.id for entry in CORPUS]
    assert len(ids) == len(set(ids)), "corpus ids must be unique — they key React lists and DOM ids"
    assert all(ids), "every entry needs an id"


def test_ids_are_safe_as_html_ids() -> None:
    # topic is prose and makes an invalid HTML id / ARIA IDREF; id must not repeat that mistake.
    for entry in CORPUS:
        assert re.fullmatch(r"[A-Za-z][A-Za-z0-9\-_]*", entry.id), (
            f"{entry.id!r} is not a valid HTML id — no spaces or punctuation"
        )


# ---------- structured tariff fields (#185) ----------


def test_wool_has_the_sourced_current_and_final_tariff() -> None:
    # Real figures from the NIA's Key Tariff Outcomes table (p.13), not placeholders - the
    # whole point of #185 is that these are queryable, not just prose.
    entry = next(e for e in CORPUS if e.topic == "Wool")
    assert entry.direction is TradeDirection.NZ_EXPORTS_TO_INDIA
    assert entry.current_tariff == "2.75%"
    assert entry.final_tariff == "0% (eliminated)"
    assert entry.implementation_period_years == 0


def test_kiwifruit_and_apples_are_split_with_different_structured_outcomes() -> None:
    # They used to be one combined entry; combining them under a single current/final tariff
    # pair would misrepresent one of the two (apples is never fully eliminated).
    kiwifruit = next(e for e in CORPUS if e.topic == "Kiwifruit")
    apples = next(e for e in CORPUS if e.topic == "Apples")
    assert kiwifruit.id != apples.id
    assert kiwifruit.current_tariff == "33%"
    assert apples.current_tariff == "50%"
    assert "never fully eliminated" in apples.final_tariff.lower()


def test_cherries_and_avocados_split_from_the_unconfirmed_pair() -> None:
    confirmed_pair = next(e for e in CORPUS if e.topic == "Cherries and avocados")
    unconfirmed_pair = next(e for e in CORPUS if e.topic == "Blueberries and persimmons")

    assert confirmed_pair.current_tariff == "33%"
    assert confirmed_pair.final_tariff == "0% (eliminated)"

    # No product-specific line exists for these two - structured fields must stay unset
    # rather than silently borrowing the cherries/avocados figures.
    assert unconfirmed_pair.current_tariff is None
    assert unconfirmed_pair.final_tariff is None
    assert unconfirmed_pair.confirmed is True  # the qualitative claim is still sourced


def test_peptones_does_not_borrow_bulk_infant_formulas_current_tariff() -> None:
    peptones = next(e for e in CORPUS if e.topic == "Dairy - peptones")
    bulk_infant_formula = next(
        e for e in CORPUS if "bulk infant formula" in e.topic.lower()
    )

    assert bulk_infant_formula.current_tariff == "33%"
    assert peptones.current_tariff is None
    # The qualitative "phases out over 7 years" claim stays, it just isn't tied to a
    # borrowed baseline.
    assert peptones.implementation_period_years == 7


def test_excluded_dairy_has_no_current_tariff_figure() -> None:
    excluded = next(e for e in CORPUS if e.topic == "Dairy - milk, cheese, butter")
    assert excluded.current_tariff is None
    assert excluded.final_tariff is None


def test_aggregate_entries_carry_no_product_level_tariff_figures() -> None:
    # "95% of exports" is not a single product's tariff line - current/final tariff fields
    # must stay unset for cross-sector aggregates, not populated with something misleading.
    for topic in (
        "India tariffs on NZ exports (overall)",
        "India tariff-line count (~70% of ~12,500 lines)",
        "Two-way trade value",
        "Independent GDP modelling",
    ):
        entry = next(e for e in CORPUS if e.topic == topic)
        assert entry.current_tariff is None
        assert entry.final_tariff is None


def test_iron_steel_and_industrial_products_are_not_added() -> None:
    # The source table gives these a current-tariff range too, but neither is one of the ten
    # sectors either client document names (docs/project-charter.md §6, still unsettled) -
    # deliberately out of scope for this pass.
    topics = {entry.topic.lower() for entry in CORPUS}
    assert not any("iron" in t or "steel" in t for t in topics)
    assert not any("industrial product" in t for t in topics)
