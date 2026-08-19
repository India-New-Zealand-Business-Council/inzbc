"""Tests for the #55 dry-run orchestration script (run_dry_run.py).

Uses a fake SipPipelineClient (same pattern as test_pipeline_integration.py's FakeSipApi) so
these run without a live backend - the real end-to-end path is exercised only via the
workflow_dispatch CI job (sip-dry-run.yml), which has a real Postgres and services/api.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from apps.sip.collector import run_dry_run
from apps.sip.pipeline.client import SipApiError

FIXTURE = Path(__file__).parents[1] / "data" / "dry_run_fixture_articles.json"

_SESSION_ARGS = ["--session-cookie", "cookie-value", "--csrf-token", "csrf-value"]


@dataclass
class _FakeClient:
    base_url: str
    session_cookie: str
    csrf_token: str
    source_library_status: int | None = None
    runs: list[dict] = field(default_factory=list)
    candidates: dict[str, dict] = field(default_factory=dict)
    _next_id: int = 0

    def _new_id(self, prefix: str) -> str:
        self._next_id += 1
        return f"{prefix}-{self._next_id}"

    def create_run(self, run) -> dict:
        payload = run.model_dump(mode="json", exclude_none=True)
        payload["id"] = self._new_id("run")
        self.runs.append(payload)
        return payload

    def get_source_library(self) -> list[dict]:
        if self.source_library_status is not None:
            raise SipApiError(self.source_library_status, "not found")
        return []

    def create_candidate(self, candidate) -> dict:
        payload = candidate.model_dump(mode="json", exclude_none=True)
        payload["id"] = self._new_id("cand")
        self.candidates[payload["id"]] = payload
        return payload


def test_locked_coverage_window_is_exact_24h_previous_day_0700_to_today_0700():
    now_utc = datetime(2026, 8, 8, 3, 0, tzinfo=UTC)  # 15:00 NZST, well after 07:00
    start, end = run_dry_run._locked_coverage_window(now_utc)

    start_nz = datetime.fromisoformat(start).astimezone(ZoneInfo("Pacific/Auckland"))
    end_nz = datetime.fromisoformat(end).astimezone(ZoneInfo("Pacific/Auckland"))

    assert start_nz.hour == 7 and start_nz.minute == 0
    assert end_nz.hour == 7 and end_nz.minute == 0
    assert (end_nz - start_nz).total_seconds() == 24 * 3600
    assert end_nz.date() == now_utc.astimezone(ZoneInfo("Pacific/Auckland")).date()


def test_locked_coverage_window_before_0700_nz_uses_previous_boundary():
    # 02:00 NZST is before the 07:00 boundary, so "today's" window hasn't opened yet.
    now_utc = datetime(2026, 8, 7, 13, 0, tzinfo=UTC)  # 01:00 NZST next day... use a clean case
    now_utc = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)  # 00:00 NZST 9 Aug -> before 07:00
    _start, end = run_dry_run._locked_coverage_window(now_utc)
    end_nz = datetime.fromisoformat(end).astimezone(ZoneInfo("Pacific/Auckland"))
    assert end_nz.date() < now_utc.astimezone(ZoneInfo("Pacific/Auckland")).date()


def test_main_creates_a_dryrun_stamped_run_not_a_run_number(monkeypatch, tmp_path):
    fake = _FakeClient(base_url="http://x", session_cookie="c", csrf_token="t")
    monkeypatch.setattr(run_dry_run, "SipPipelineClient", lambda *a, **k: fake)
    evidence_out = tmp_path / "evidence.json"

    exit_code = run_dry_run.main(
        [
            "--base-url",
            "http://x",
            "--articles-file",
            str(FIXTURE),
            *_SESSION_ARGS,
            "--evidence-out",
            str(evidence_out),
        ]
    )

    assert exit_code == 0
    assert fake.runs[0]["run_number"].startswith("DRYRUN-")
    assert fake.runs[0]["production_enabled"] is False
    assert len(fake.candidates) == 2

    evidence = json.loads(evidence_out.read_text())
    assert evidence["dry_run"] is True
    assert evidence["candidates_created"] == 2
    assert evidence["source_library_available"] is True
    # an empty source_library means every mandatory source is still missing an outcome
    assert len(evidence["mandatory_source_outcomes_missing"]) == 112


def test_main_is_fatal_when_source_library_is_unavailable(monkeypatch, tmp_path):
    # A broken or unseeded source_library must not look like a pass: previously this was
    # downgraded to a warning and the run continued with every candidate's source_id unset,
    # which is exactly the failure mode this dry run exists to catch before a real run hits it.
    fake = _FakeClient(
        base_url="http://x", session_cookie="c", csrf_token="t", source_library_status=404
    )
    monkeypatch.setattr(run_dry_run, "SipPipelineClient", lambda *a, **k: fake)
    evidence_out = tmp_path / "evidence.json"

    exit_code = run_dry_run.main(
        [
            "--base-url",
            "http://x",
            "--articles-file",
            str(FIXTURE),
            *_SESSION_ARGS,
            "--evidence-out",
            str(evidence_out),
        ]
    )

    assert exit_code == 1
    # no evidence file - the run failed before there was anything honest to report
    assert not evidence_out.exists()
    # the run itself was still created; only the source-library step was fatal
    assert len(fake.runs) == 1


def test_main_returns_nonzero_when_an_article_fails_to_map(monkeypatch, tmp_path):
    fake = _FakeClient(base_url="http://x", session_cookie="c", csrf_token="t")
    monkeypatch.setattr(run_dry_run, "SipPipelineClient", lambda *a, **k: fake)
    bad_articles = tmp_path / "bad.json"
    bad_articles.write_text(json.dumps([{"description": "no title or url"}]))

    exit_code = run_dry_run.main(
        [
            "--base-url",
            "http://x",
            "--articles-file",
            str(bad_articles),
            *_SESSION_ARGS,
        ]
    )

    assert exit_code == 1
