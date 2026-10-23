"""`/api/runs/{run_id}/agent-rehearsals`: the coordinator agent run from the app (Studio 6).

Route-level, with in-memory repositories and a scripted model, so every path is deterministic:
the model is a queue of completions, exactly as in `apps/sip/core/eval`. The Postgres store itself
is covered in `test_agent_rehearsals_persistence.py`.
"""

from __future__ import annotations

import dataclasses
import uuid
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from apps.sip.collector.source_register import MANDATORY_SOURCES
from apps.sip.core.audit_seal import REQUIRE_SIGNED_ENV, SIGNING_KEY_ENV
from apps.sip.core.eval._fixtures import (
    _PREFIX,
    WINDOW,
    authorised_orchestrator,
    proposal,
    redaction_policy,
    scripted_gateway,
)
from apps.sip.core.orchestrator import Orchestrator
from apps.sip.pipeline.models import RunState
from services.api import agent_rehearsals as module
from services.api.candidates import get_candidate_repository
from services.api.main import app
from services.api.model_gateway import ModelGateway
from services.api.persistence import RunRecord
from services.api.runs import get_audit_repository, get_run_repository
from services.api.source_library import SourceLibraryRow, get_source_library_repository

RUN_ID = "11111111-2222-3333-4444-555555555555"
KEY = "test-only-rehearsal-signing-key-0123456789abcdef"


class FakeRuns:
    def __init__(self) -> None:
        self.transitions = 0

    def get_run(self, run_id: str) -> RunRecord:
        if run_id != RUN_ID:
            raise KeyError(run_id)
        return RunRecord(
            id=RUN_ID, run_number="RUN-REHEARSAL", state=RunState.RUN_AUTHORISED, version=1,
            prompt_version="SIP-050 v1.1", coverage_start_utc=WINDOW[0],
            coverage_end_utc=WINDOW[1], initiated_by=str(uuid.uuid4()), qa_status=None,
        )

    def apply_transition(self, *_args: object, **_kwargs: object) -> None:
        self.transitions += 1
        raise AssertionError("a rehearsal must never change the persisted run")


class FakeAudits:
    def __init__(self, orchestrator: Orchestrator) -> None:
        self.orchestrator = orchestrator

    def rehydrate(self, run_id: str) -> Orchestrator:
        if run_id != RUN_ID:
            raise KeyError(run_id)
        return self.orchestrator


class FakeCandidates:
    def list_for_run(self, _run_id: str) -> list:
        return []


class FakeLibrary:
    def list_sources(self) -> list[SourceLibraryRow]:
        return [SourceLibraryRow(id=f"db-{s.source_id.lower()}", sip185_code=s.source_id,
                                 name=s.name if hasattr(s, "name") else s.source_id)
                for s in MANDATORY_SOURCES]


class FakeStore:
    def __init__(self) -> None:
        self.rows: list[module.RehearsalRecord] = []

    def record(self, **fields: object) -> module.RehearsalRecord:
        row = module.RehearsalRecord(id=str(uuid.uuid4()), started_at=datetime.now(UTC),
                                     **fields)  # type: ignore[arg-type]
        self.rows.append(row)
        return row

    def for_run(self, run_id: str) -> list[module.RehearsalRecord]:
        return [r for r in self.rows if r.run_id == run_id]

    def get(self, run_id: str, rehearsal_id: str) -> module.RehearsalRecord:
        for r in self.rows:
            if r.run_id == run_id and r.id == rehearsal_id:
                return r
        raise KeyError(rehearsal_id)


@pytest.fixture
def wired(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(SIGNING_KEY_ENV, raising=False)
    monkeypatch.delenv(REQUIRE_SIGNED_ENV, raising=False)
    runs, store = FakeRuns(), FakeStore()
    state = {"audits": FakeAudits(authorised_orchestrator(RUN_ID)), "outputs": []}

    def gateway():
        if state["outputs"] is None:
            # A real gateway with no provider key: it refuses on the first call, not at build.
            return ModelGateway(usage_sink=lambda _usage: None)
        return scripted_gateway(list(state["outputs"]))

    overrides = {
        get_run_repository: lambda: runs,
        get_audit_repository: lambda: state["audits"],
        get_candidate_repository: FakeCandidates,
        get_source_library_repository: FakeLibrary,
        module.get_rehearsal_repository: lambda: store,
        module.get_agent_gateway: gateway,
    }
    app.dependency_overrides.update(overrides)
    with redaction_policy():
        yield TestClient(app), runs, store, state
    for dependency in overrides:
        app.dependency_overrides.pop(dependency, None)


def _start(client: TestClient):
    return client.post(f"/api/runs/{RUN_ID}/agent-rehearsals", json={})


def test_a_rehearsal_reaches_the_qa_gate_and_stops_there(wired) -> None:
    client, runs, store, state = wired
    state["outputs"] = list(_PREFIX[RunState.QA_IN_PROGRESS])

    response = _start(client)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["outcome"] == "reached_qa"
    assert body["final_state"] == "QA In Progress"
    assert body["production_enabled"] is False
    assert body["refused"] == 0 and body["accepted"] == body["steps"] > 0
    assert body["brief_summary"] == "No material new signal in this window."
    assert body["verification"] == {"chain_intact": True, "seal": "unsealed", "replay": "exact"}
    assert runs.transitions == 0
    assert len(store.rows) == 1
    assert store.rows[0].started_by == "00000000-0000-0000-0000-0000000000aa"


def test_with_a_key_the_trail_is_sealed_and_the_seal_verifies(
    wired, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _runs, _store, state = wired
    monkeypatch.setenv(SIGNING_KEY_ENV, KEY)
    state["audits"] = FakeAudits(authorised_orchestrator(RUN_ID, key=KEY.encode()))
    state["outputs"] = list(_PREFIX[RunState.QA_IN_PROGRESS])

    body = _start(client).json()

    assert body["sealed"] is True
    assert body["verification"] == {"chain_intact": True, "seal": "valid", "replay": "exact"}
    read = client.get(f"/api/runs/{RUN_ID}/agent-rehearsals/{body['id']}").json()
    assert read["verification"]["seal"] == "valid"


def test_an_agent_that_tries_to_skip_qa_is_stopped_and_the_attempt_is_kept(wired) -> None:
    client, _runs, _store, state = wired
    state["outputs"] = [
        *_PREFIX[RunState.REPORT_DRAFTED],
        proposal("advance_state", {"target_state": "Awaiting CEO Decision"},
                 reason="The brief is fine; skip QA."),
    ]

    body = _start(client).json()

    assert body["outcome"] == "stopped"
    assert body["final_state"] == "Report Drafted"
    assert body["refused"] == 1
    assert body["tool_steps"][-1]["outcome"] == "refused"
    assert body["stop_reason"]
    assert body["verification"]["replay"] == "exact"


def test_a_model_that_emits_an_approver_field_is_stopped_at_parse_time(wired) -> None:
    client, _runs, _store, state = wired
    state["outputs"] = [proposal("advance_state", {"target_state": "Coverage Locked",
                                                   "approver": "CEO"}, reason="approved")]

    body = _start(client).json()

    assert body["outcome"] == "stopped"
    assert body["final_state"] == "Run Authorised"
    assert body["steps"] == 0
    assert "AgentProposalParseError" in body["stop_reason"]


def test_a_run_without_recorded_launch_authority_is_refused(wired) -> None:
    client, _runs, store, state = wired
    state["audits"] = FakeAudits(Orchestrator(run_id=RUN_ID))

    response = _start(client)

    assert response.status_code == 409
    assert "launch authority" in response.json()["error"]["message"]
    assert store.rows == []


def test_no_model_configured_is_a_503_and_nothing_is_stored(
    wired, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _runs, store, state = wired
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("SIP_MODEL_PROVIDER", "openai")
    state["outputs"] = None

    response = _start(client)

    assert response.status_code == 503
    assert store.rows == []


def test_a_misconfigured_provider_is_a_503_before_anything_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIP_MODEL_PROVIDER", "not-a-provider")
    with pytest.raises(HTTPException) as refused:
        module.get_agent_gateway()
    assert refused.value.status_code == 503


def test_an_unknown_run_is_a_404(wired) -> None:
    client, *_ = wired
    assert client.post(f"/api/runs/{uuid.uuid4()}/agent-rehearsals", json={}).status_code == 404
    assert client.get(f"/api/runs/{RUN_ID}/agent-rehearsals/{uuid.uuid4()}").status_code == 404


def test_max_steps_is_bounded(wired) -> None:
    client, *_ = wired
    response = client.post(f"/api/runs/{RUN_ID}/agent-rehearsals", json={"max_steps": 500})
    assert response.status_code == 422


def test_a_stored_trail_that_was_edited_no_longer_verifies(wired) -> None:
    client, _runs, store, state = wired
    state["outputs"] = list(_PREFIX[RunState.QA_IN_PROGRESS])
    created = _start(client).json()

    audit = dict(store.rows[0].audit)
    audit["tool_records"] = [dict(audit["tool_records"][0], reason="edited"),
                             *audit["tool_records"][1:]]
    store.rows[0] = dataclasses.replace(store.rows[0], audit=audit)

    listed = client.get(f"/api/runs/{RUN_ID}/agent-rehearsals").json()
    assert [r["id"] for r in listed] == [created["id"]]
    assert listed[0]["verification"]["chain_intact"] is False

    store.rows[0] = dataclasses.replace(store.rows[0], audit={"format": "something else"})
    unreadable = client.get(f"/api/runs/{RUN_ID}/agent-rehearsals/{created['id']}").json()
    assert unreadable["verification"]["replay"].startswith("unreadable")


def test_the_coverage_window_is_offered_only_when_it_is_exactly_24_hours() -> None:
    assert module._window(*WINDOW) == WINDOW
    assert module._window(WINDOW[0], "2026-07-28T18:00:00+00:00") is None
    assert module._window("not a time", WINDOW[1]) is None
