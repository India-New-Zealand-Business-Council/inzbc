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
