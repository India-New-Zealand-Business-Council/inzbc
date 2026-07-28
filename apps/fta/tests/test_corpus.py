from __future__ import annotations

import re
from datetime import date

from apps.fta.corpus import (
    CORPUS,
    TIER_1_SOURCES,
    TIER_2_SOURCES,
    TariffOutcome,
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
