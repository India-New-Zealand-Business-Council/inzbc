"""Tests for `scripts/sip_collector_pipeline_evidence.py` (#337).

No `DATABASE_URL` needed — the script itself runs entirely offline against synthetic fixture
data (dedupe.py, ingest.py and source_register.py's pure logic, no live client, no database).
"""

from __future__ import annotations

from apps.sip.collector.dedupe import find_duplicate_of
from apps.sip.collector.ingest import ingest_articles
from scripts.sip_collector_pipeline_evidence import (
    _ALREADY_CAPTURED,
    _INCOMING_BATCH,
    _RUN_ID,
    _FakeClient,
    build_report,
)


def test_dedupe_count_matches_a_direct_find_duplicate_of_run() -> None:
    """Recomputes the duplicate count directly against `dedupe.find_duplicate_of` — the same
    check the evidence report's own claim rests on — rather than trusting the script's internal
    counter.
    """
    matched = 0
    for article in _INCOMING_BATCH:
        if not isinstance(article, dict) or "title" not in article:
            continue
        if find_duplicate_of(article, _ALREADY_CAPTURED):
            matched += 1
    assert matched == 2


def test_malformed_item_fails_in_isolation_without_stopping_the_batch() -> None:
    """The one item with no `title` fails on its own; every well-formed item around it still
    gets created — `ingest_articles`'s per-item isolation claim, exercised directly rather than
    read off the report the script generates from this same call.
    """
    client = _FakeClient()
    result = ingest_articles(client, _RUN_ID, _INCOMING_BATCH)

    well_formed = sum(
        1 for a in _INCOMING_BATCH if isinstance(a, dict) and "title" in a
    )
    assert len(result.created) == well_formed
    assert len(result.failed) == 1
    assert "title" in result.failed[0].error


def test_mandatory_source_gate_reports_the_uncovered_set_not_a_fixed_total() -> None:
    """`missing_mandatory_outcomes` with zero outcomes recorded returns every mandatory source;
    with the first three covered, it returns exactly three fewer — proof it reports the
    *uncovered* set rather than a count that happens to look right at zero.
    """
    from apps.sip.collector.source_register import (
        MANDATORY_SOURCES,
        missing_mandatory_outcomes,
    )

    assert len(missing_mandatory_outcomes(set())) == len(MANDATORY_SOURCES)

    covered = {s.source_id for s in MANDATORY_SOURCES[:3]}
    still_missing = missing_mandatory_outcomes(covered)
    assert len(still_missing) == len(MANDATORY_SOURCES) - 3
    assert not covered & set(still_missing)


def test_build_report_contains_all_three_sections() -> None:
    """`build_report()` combines all three sections without error and in order — a smoke test
    that would catch one section's function raising or the assembly order changing.
    """
    report = build_report()
    dedupe_idx = report.index("## 1. Cross-run duplicate detection")
    ingest_idx = report.index("## 2. Per-item isolation on a malformed article")
    gate_idx = report.index("## 3. Mandatory-source coverage gate")
    assert dedupe_idx < ingest_idx < gate_idx

