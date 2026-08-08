"""Tests for SipPipelineClient's request-building - no live server, just what gets sent.

No test of this existed before #55: `create_run` dumped the whole `Run` model, including
server-only fields with non-None defaults (`coverage_timezone`, `state`, `production_enabled`),
which 422s against `services/api/runs.py`'s `CreateRunIn` (`extra="forbid"`) for every real
caller - a `Run()` sets `coverage_timezone` by default, so there was no way to construct one that
wouldn't trip it. Caught only by actually running the dry run against a live server.
"""

from __future__ import annotations

from apps.sip.pipeline.client import SipPipelineClient
from apps.sip.pipeline.models import Candidate, Run


def test_create_run_sends_only_the_fields_create_run_in_accepts(monkeypatch):
    """Mirrors services/api/runs.py's CreateRunIn field set exactly - if that model gains or
    drops a field, this test and the payload built here should both change together.
    """
    sent: dict = {}

    def fake_request(self, method, path, **kwargs):
        sent["method"] = method
        sent["path"] = path
        sent["json"] = kwargs.get("json")
        return {"id": "run-1", **kwargs["json"]}

    monkeypatch.setattr(SipPipelineClient, "_request", fake_request)
    client = SipPipelineClient("http://x", "token")

    client.create_run(
        Run(
            run_number="DRYRUN-1",
            coverage_start_utc="2026-08-07T19:00:00+00:00",
            coverage_end_utc="2026-08-08T19:00:00+00:00",
            prompt_version="SIP-050-v1.1",
            initiated_by="tester",
        )
    )

    assert sent["method"] == "POST"
    assert sent["path"] == "/api/runs"
    assert sent["json"] == {
        "run_number": "DRYRUN-1",
        "prompt_version": "SIP-050-v1.1",
        "coverage_start_utc": "2026-08-07T19:00:00+00:00",
        "coverage_end_utc": "2026-08-08T19:00:00+00:00",
        "initiated_by": "tester",
    }
    # the fields CreateRunIn would reject with extra="forbid" must never appear
    assert "coverage_timezone" not in sent["json"]
    assert "production_enabled" not in sent["json"]
    assert "state" not in sent["json"]
    assert "id" not in sent["json"]


def test_create_candidate_sends_actor_id_and_never_the_unaccepted_defaulted_fields(monkeypatch):
    """`Candidate.verification` defaults to `Unverified` (not None), so a naive
    `model_dump(exclude_none=True)` would still send it - `CaptureCandidateIn`
    (services/api/candidates.py) has no `verification` field and forbids extras. Same defect
    class as test_create_run_sends_only_the_fields_create_run_in_accepts, caught the same way.
    """
    sent: dict = {}

    def fake_request(self, method, path, **kwargs):
        sent["method"] = method
        sent["path"] = path
        sent["json"] = kwargs.get("json")
        return {"id": "cand-1", **kwargs["json"]}

    monkeypatch.setattr(SipPipelineClient, "_request", fake_request)
    client = SipPipelineClient("http://x", "token")

    client.create_candidate(
        Candidate(run_id="run-1", headline="Headline"),
        actor_id="actor-1",
    )

    assert sent["method"] == "POST"
    assert sent["path"] == "/api/candidates"
    assert sent["json"] == {
        "run_id": "run-1",
        "headline": "Headline",
        "actor_id": "actor-1",
    }
    assert "verification" not in sent["json"]
    assert "id" not in sent["json"]
    assert "captured_at" not in sent["json"]
