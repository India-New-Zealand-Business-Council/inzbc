"""Replay and tamper detection through Postgres (`apps/sip/core/eval/persisted_replay.py`).

A short run of the same measurement the research reports at 200 runs, so CI fails if a trail
stops round-tripping exactly or a database-level rewrite stops being caught on read.
"""

from __future__ import annotations

import os

import pytest

from apps.sip.core.eval.persisted_replay import run_measurement

DATABASE_URL = os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - needs a real Postgres with schema.sql",
)


def test_trails_round_trip_and_database_tampering_is_caught_with_the_key() -> None:
    report = run_measurement(DATABASE_URL, runs=5)
    assert report["round_trip_exact"] == 5
    assert report["replay_exact_after_read"] == 5
    assert report["application_update_refused"] == 5
    assert report["db_tamper_safety_detected"] == report["db_tamper_safety_applied"] > 0
    assert report["db_tamper_metadata_detected"] == report["db_tamper_metadata_applied"] > 0
    # The key is what catches a forged approver: without it the forgery replays as valid.
    forged = report["db_tamper_by_mutation"]["forge-human-approver"]
    assert forged["detected"] == forged["applied"] and forged["detected_without_key"] == 0
