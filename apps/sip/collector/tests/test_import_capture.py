"""All import tests are synthetic; none touches a live SIP server."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from apps.sip.collector import capture_manifest, import_capture
from apps.sip.collector.source_register import MANDATORY_SOURCES
from apps.sip.pipeline.models import SourceOutcome

RUN_ID = "11111111-1111-1111-1111-111111111111"


@dataclass
class FakeClient:
    state: str = "Scanning"
    source_gap: bool = False
    no_evidence: bool = False
    existing: list[dict] = field(default_factory=list)
    fail_at: int | None = None
    requested: int = 0

    def get_run(self, run_id: str) -> dict:
        assert run_id == RUN_ID
        return {
            "id": RUN_ID,
            "run_number": "RUN-20261026-01",
            "state": self.state,
            "coverage_start_utc": "2026-10-24T18:00:00+00:00",
            "coverage_end_utc": "2026-10-25T18:00:00+00:00",
        }

    def get_source_library(self) -> list[dict]:
        rows = [
            {
                "id": f"db-{source.source_id}",
                "sip185_code": source.source_id,
                "name": source.name,
            }
            for source in MANDATORY_SOURCES
        ]
        rows.append({"id": "extra", "sip185_code": None, "name": "Synthetic Feed"})
        return rows

    def list_source_checks(self, run_id: str) -> list[dict]:
        assert run_id == RUN_ID
        codes = MANDATORY_SOURCES[:-1] if self.source_gap else MANDATORY_SOURCES
        return [
            {
                "run_id": RUN_ID,
                "source_id": f"db-{source.source_id}",
                "outcome": next(iter(SourceOutcome)).value,
                "notes": "" if self.no_evidence else "Human checked; evidence: synthetic only",
            }
            for source in codes
        ]

    def list_candidates(self, run_id: str) -> list[dict]:
        assert run_id == RUN_ID
        return self.existing

    def create_candidate(self, candidate) -> dict:
        self.requested += 1
        if self.fail_at == self.requested:
            raise RuntimeError("synthetic remote write failure")
        result = {"id": f"test-candidate-{self.requested}", **candidate.model_dump()}
        self.existing.append(result)
        return result


@pytest.fixture
def capture(tmp_path: Path) -> Path:
    articles = [{
        "title": "India and New Zealand discuss an FTA",
        "url": "https://example.org/trade-1",
        "source": "Synthetic Feed",
        "description": "Only a synthetic fixture",
        "published": "2026-10-25T02:00:00+00:00",
        "score": 30,
        "nz_relevance_score": 10,
        "sectors": ["Trade and FTA"],
    }]
    data = {
        "schema_version": 1,
        "kind": "INZBC_SIP_REVIEW_CAPTURE",
        "production_run": False,
        "sip185_outcomes_confirmed": False,
        "locked_sip184_window": False,
        "fetch_started_utc": "2026-10-25T10:00:00+00:00",
        "fetch_finished_utc": "2026-10-25T10:01:00+00:00",
        "rolling_fetch_hours": 24,
        "raw_article_count": len(articles),
        "article_count": len(articles),
        "coverage_state": "observed",
        "coverage_gaps": [],
        "source_fetch_health": {
            "Synthetic Feed": {
                "fetch_outcome": "ok",
                "queries_failed": 0,
                "queries_total": 0,
            }
        },
        "articles": articles,
        "articles_sha256": hashlib.sha256(
            capture_manifest._canonical_bytes(articles)
        ).hexdigest(),
        "operator_notice": "synthetic only",
    }
    path = tmp_path / "synthetic-capture.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _change(path: Path, operation) -> Path:
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    operation(snapshot)
    snapshot["article_count"] = len(snapshot["articles"])
    snapshot["raw_article_count"] = len(snapshot["articles"])
    snapshot["articles_sha256"] = hashlib.sha256(
        capture_manifest._canonical_bytes(snapshot["articles"])
    ).hexdigest()
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    return path


def test_preview_is_read_only_even_with_complete_112_source_evidence(capture: Path) -> None:
    client = FakeClient()
    plan = import_capture.prepare_capture(client, RUN_ID, capture)
    assert len(MANDATORY_SOURCES) == 112
    assert client.requested == 0
    assert len(plan.candidates) == 1
    assert plan.candidates[0].source_id == "extra"
    assert plan.candidates[0].in_coverage_window is True
    assert plan.summary()["production_run_executed"] is False


@pytest.mark.parametrize(("changes", "message"), [
    ({"state": "Draft"}, "Scanning"),
    ({"source_gap": True}, "mandatory SIP-185 outcomes"),
    ({"no_evidence": True}, "evidence notes"),
    ({"existing": [{"id": "already"}]}, "already has candidates"),
])
def test_incomplete_run_or_evidence_never_writes(
    capture: Path, changes: dict, message: str
) -> None:
    client = FakeClient(**changes)
    with pytest.raises(ValueError, match=message):
        import_capture.prepare_capture(client, RUN_ID, capture)
    assert client.requested == 0


def test_incomplete_fetch_coverage_is_not_sip185_approval(capture: Path) -> None:
    _change(capture, lambda s: (
        s["source_fetch_health"]["Synthetic Feed"].update(fetch_outcome="partial"),
        s.update(coverage_state="incomplete", coverage_gaps=["Synthetic Feed"]),
    ))
    with pytest.raises(ValueError, match="incomplete fetch coverage"):
        import_capture.prepare_capture(FakeClient(), RUN_ID, capture)


@pytest.mark.parametrize(("operation", "message"), [
    (lambda s: s["articles"][0].update(published=""), "unknown publication"),
    (lambda s: s["articles"][0].update(
        published="2026-10-26T18:01:00+00:00"
    ), "outside locked"),
    (lambda s: s["articles"][0].update(
        source="Unknown External Source"
    ), "unresolved"),
    (lambda s: s["articles"].append(deepcopy(s["articles"][0])), "duplicate URL"),
])
def test_unsafe_capture_items_rejected_before_any_write(
    capture: Path, operation, message: str
) -> None:
    _change(capture, operation)
    client = FakeClient()
    with pytest.raises(ValueError, match=message):
        import_capture.prepare_capture(client, RUN_ID, capture)
    assert client.requested == 0


def test_explicit_commit_requires_exact_run_and_human_confirmation(capture: Path) -> None:
    client = FakeClient()
    plan = import_capture.prepare_capture(client, RUN_ID, capture)
    for number, confirmation in [
        ("WRONG", True), (plan.run_number, False),
    ]:
        with pytest.raises(ValueError, match="exact run number"):
            import_capture.apply_capture(
                client, plan, confirmed_run_number=number, sip191_reviewed=confirmation
            )
    assert client.requested == 0
    result = import_capture.apply_capture(
        client, plan, confirmed_run_number=plan.run_number, sip191_reviewed=True
    )
    assert result["created"] == 1
    assert client.requested == 1
    with pytest.raises(ValueError, match="run now contains candidates"):
        import_capture.apply_capture(
            client, plan, confirmed_run_number=plan.run_number, sip191_reviewed=True
        )
    assert client.requested == 1


def test_import_aborts_on_partial_http_write_and_requires_reconciliation(capture: Path) -> None:
    client = FakeClient(fail_at=2)
    _change(capture, lambda s: s["articles"].append({
        **s["articles"][0],
        "title": "Second synthetic trade item",
        "url": "https://example.org/trade-2",
    }))
    plan = import_capture.prepare_capture(client, RUN_ID, capture)
    with pytest.raises(RuntimeError, match="after 1 writes"):
        import_capture.apply_capture(
            client, plan, confirmed_run_number=plan.run_number, sip191_reviewed=True
        )
    assert len(client.existing) == 1
    with pytest.raises(ValueError, match="run now contains candidates"):
        import_capture.apply_capture(
            client, plan, confirmed_run_number=plan.run_number, sip191_reviewed=True
        )


def test_cannot_override_dst_ambiguity_through_capture_plan(capture: Path) -> None:
    client = FakeClient()
    start = "2026-09-25T19:00:00+00:00"
    end = "2026-09-26T18:00:00+00:00"
    with pytest.raises(ValueError, match="DST SOP conflict"):
        import_capture._run_window({
            "coverage_start_utc": start,
            "coverage_end_utc": end,
        })
    assert client.requested == 0
