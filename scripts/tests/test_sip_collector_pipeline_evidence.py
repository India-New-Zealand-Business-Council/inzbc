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
