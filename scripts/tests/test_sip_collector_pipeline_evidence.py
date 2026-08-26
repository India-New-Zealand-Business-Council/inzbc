"""Tests for `scripts/sip_collector_pipeline_evidence.py` (#337).

No `DATABASE_URL` needed — the script itself runs entirely offline against synthetic fixture
data (dedupe.py, ingest.py and source_register.py's pure logic, no live client, no database).
"""

from __future__ import annotations

from apps.sip.collector.dedupe import find_duplicate_of
from scripts.sip_collector_pipeline_evidence import _ALREADY_CAPTURED, _INCOMING_BATCH


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
