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

import apps.sip.collector.run_dry_run as run_dry_run
from apps.sip.pipeline.client import SipApiError

FIXTURE = Path(__file__).parents[1] / "data" / "dry_run_fixture_articles.json"


@dataclass
class _FakeClient:
    base_url: str
    token: str
    source_library_status: int | None = 404
    runs: list[dict] = field(default_factory=list)
    candidates: dict[str, dict] = field(default_factory=dict)
    _next_id: int = 0

    def _new_id(self, prefix: str) -> str:
        self._next_id += 1
        return f"{prefix}-{self._next_id}"

    def create_run(self, run) -> dict:  # noqa: ANN001 - duck-typed fake
        payload = run.model_dump(mode="json", exclude_none=True)
        payload["id"] = self._new_id("run")
        self.runs.append(payload)
        return payload

    def get_source_library(self) -> list[dict]:
        if self.source_library_status is not None:
            raise SipApiError(self.source_library_status, "not found")
        return []

    def create_candidate(self, candidate, actor_id) -> dict:  # noqa: ANN001
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
    start, end = run_dry_run._locked_coverage_window(now_utc)
    end_nz = datetime.fromisoformat(end).astimezone(ZoneInfo("Pacific/Auckland"))
    assert end_nz.date() < now_utc.astimezone(ZoneInfo("Pacific/Auckland")).date()


def test_main_creates_a_dryrun_stamped_run_not_a_run_number(monkeypatch, tmp_path):
    fake = _FakeClient(base_url="http://x", token="t")
    monkeypatch.setattr(run_dry_run, "SipPipelineClient", lambda *a, **k: fake)
    evidence_out = tmp_path / "evidence.json"

    exit_code = run_dry_run.main(
        [
            "--base-url",
            "http://x",
            "--articles-file",
            str(FIXTURE),
            "--initiated-by",
            "test",
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
    assert evidence["source_library_available"] is False
    assert evidence["mandatory_source_outcomes_missing"] is None


def test_main_reports_source_library_available_when_endpoint_works(monkeypatch, tmp_path):
    fake = _FakeClient(base_url="http://x", token="t", source_library_status=None)
    monkeypatch.setattr(run_dry_run, "SipPipelineClient", lambda *a, **k: fake)
    evidence_out = tmp_path / "evidence.json"

    run_dry_run.main(
        [
            "--base-url",
            "http://x",
            "--articles-file",
            str(FIXTURE),
            "--initiated-by",
            "test",
            "--evidence-out",
            str(evidence_out),
        ]
    )

    evidence = json.loads(evidence_out.read_text())
    assert evidence["source_library_available"] is True
    # an empty source_library means every mandatory source is still missing an outcome
    assert len(evidence["mandatory_source_outcomes_missing"]) == 112


def test_main_returns_nonzero_when_an_article_fails_to_map(monkeypatch, tmp_path):
    fake = _FakeClient(base_url="http://x", token="t")
    monkeypatch.setattr(run_dry_run, "SipPipelineClient", lambda *a, **k: fake)
    bad_articles = tmp_path / "bad.json"
    bad_articles.write_text(json.dumps([{"description": "no title or url"}]))

    exit_code = run_dry_run.main(
        [
            "--base-url",
            "http://x",
            "--articles-file",
            str(bad_articles),
            "--initiated-by",
            "test",
        ]
    )

    assert exit_code == 1
