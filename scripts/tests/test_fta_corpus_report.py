"""Tests for `scripts/fta_corpus_report.py` (#337).

No `DATABASE_URL` needed — `build_report()` reads `apps/fta/corpus.py`'s in-memory `CORPUS`
directly, so these run everywhere `apps/fta/tests/` does.
"""

from __future__ import annotations

from datetime import date

from apps.fta.corpus import CORPUS
from scripts.fta_corpus_report import build_report


def test_total_facts_count_matches_corpus() -> None:
    report = build_report(date(2026, 8, 25))
    assert f"Total facts in `CORPUS`: **{len(CORPUS)}**" in report


def test_confirmed_and_tier1_counts_match_corpus() -> None:
    confirmed = [e for e in CORPUS if e.confirmed]
    tier1_confirmed = [e for e in confirmed if e.source_tier == 1]

    report = build_report(date(2026, 8, 25))
    assert (
        f"Confirmed (`confirmed=True`): **{len(confirmed)}** "
        f"({len(CORPUS) - len(confirmed)} not confirmed)"
    ) in report
    assert f"Confirmed and Tier 1 sourced: **{len(tier1_confirmed)}**" in report


def test_sector_table_matches_corpus_per_sector() -> None:
    from apps.fta.corpus import SECTORS_IN_SCOPE

    report = build_report(date(2026, 8, 25))
    for sector in SECTORS_IN_SCOPE:
        sector_entries = [e for e in CORPUS if e.sector == sector]
        sector_confirmed = [e for e in sector_entries if e.confirmed]
        sector_tier1 = [e for e in sector_confirmed if e.source_tier == 1]
        assert (
            f"| {sector} | {len(sector_entries)} | {len(sector_confirmed)} | "
            f"{len(sector_tier1)} |"
        ) in report


def test_every_blocked_tier1_source_is_listed() -> None:
    from apps.fta.corpus import TIER_1_SOURCES

    blocked = [s for s in TIER_1_SOURCES if s.automated_fetch_blocked]
    assert blocked, "fixture assumption: at least one Tier 1 source is currently blocked"

    report = build_report(date(2026, 8, 25))
    for source in blocked:
        assert f"**{source.name}** — {source.url}" in report
    not_blocked = [s for s in TIER_1_SOURCES if not s.automated_fetch_blocked]
    for source in not_blocked:
        assert f"**{source.name}** — {source.url}" not in report


def test_freshness_table_matches_stale_entries_at_each_window() -> None:
    from scripts.fta_corpus_report import _ILLUSTRATIVE_WINDOWS_DAYS
    from apps.fta.corpus import stale_entries

    as_of = date(2026, 8, 25)
    report = build_report(as_of)
    for window in _ILLUSTRATIVE_WINDOWS_DAYS:
        stale = stale_entries(CORPUS, as_of, window)
        ids = ", ".join(f"`{e.id}`" for e in stale) if stale else "none"
        assert f"| {window} | {len(stale)} | {ids} |" in report
