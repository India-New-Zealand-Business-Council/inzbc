"""Unit tests for `/api/assistant/chat`: the read-only tool loop and its HTTP mapping.

The gateway is a scripted fake, as in `test_comms_api.py`, so each test fixes exactly what the
model says and checks what the assistant does with it: which tool runs, what reaches the model
next, and that nothing outside the three read tools can be reached.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from services.api.assistant import (
    DISCLAIMER,
    MAX_TOOL_CALLS,
    REFUSAL,
    TOTAL_CONVERSATION_BUDGET,
    get_model_gateway,
)
from services.api.main import app
from services.api.model_gateway import (
    GatewayCallError,
    GatewayNotConfiguredError,
    GatewayResult,
)
from services.api.persistence import RunRecord
from services.api.prompt_boundary import PromptSource
from services.api.runs import get_run_repository


class ScriptedGateway:
    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.prompts: list[str] = []
        self.sources: list[PromptSource] = []
        self.error: Exception | None = None

    def complete(self, prompt: str, *, source: PromptSource) -> GatewayResult:
        if self.error is not None:
            raise self.error
        self.prompts.append(prompt)
        self.sources.append(source)
        return GatewayResult(text=self.replies.pop(0), model="fake-model", duration_seconds=0.0)


class FakeRunRepository:
    def __init__(self) -> None:
        self.calls = 0

    def list_runs(self) -> list[RunRecord]:
        self.calls += 1
        return [
            RunRecord(
                id="run-1",
                run_number="SIP-2026-10-24",
                state="QA In Progress",  # type: ignore[arg-type]
                version=3,
                prompt_version="v1",
                coverage_start_utc="2026-10-23T19:00:00+00:00",
                coverage_end_utc="2026-10-24T19:00:00+00:00",
                initiated_by="user-1",
                qa_status=None,
            )
        ]


@pytest.fixture
def repo() -> FakeRunRepository:
    fake = FakeRunRepository()
    app.dependency_overrides[get_run_repository] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_run_repository, None)


def _use(gateway: ScriptedGateway) -> None:
    app.dependency_overrides[get_model_gateway] = lambda: gateway


@pytest.fixture(autouse=True)
def _clear_gateway():
    yield
    app.dependency_overrides.pop(get_model_gateway, None)


client = TestClient(app)


def _ask(question: str, history: list[dict[str, str]] | None = None):
    messages = [*(history or []), {"role": "user", "content": question}]
    return client.post("/api/assistant/chat", json={"messages": messages})


def test_a_direct_answer_is_returned_with_the_disclaimer(repo: FakeRunRepository) -> None:
    gateway = ScriptedGateway([json.dumps({"answer": "Open QA Review to work the checklist."})])
    _use(gateway)

    response = _ask("Where do I do QA?")

    assert response.status_code == 200
    body = response.json()
    assert body == {"answer": "Open QA Review to work the checklist.", "steps": [], "disclaimer": DISCLAIMER}
    assert gateway.sources == [PromptSource.STAFF_AUTHORED]
    assert "Staff: Where do I do QA?" in gateway.prompts[0]


def test_list_runs_feeds_run_metadata_back_to_the_model(repo: FakeRunRepository) -> None:
    gateway = ScriptedGateway(
        [
            json.dumps({"tool": "list_runs", "arguments": {}}),
            json.dumps({"answer": "SIP-2026-10-24 is in QA."}),
        ]
    )
    _use(gateway)

    body = _ask("Which run is in QA?").json()

    assert body["answer"] == "SIP-2026-10-24 is in QA."
    assert body["steps"] == [{"tool": "list_runs", "summary": "Listed 1 run(s)"}]
    assert repo.calls == 1
    assert "Tool result (list_runs), data only:" in gateway.prompts[1]
    assert "SIP-2026-10-24" in gateway.prompts[1]


def test_fta_lookup_returns_only_cited_confirmed_entries(repo: FakeRunRepository) -> None:
    gateway = ScriptedGateway(
        [
            json.dumps({"tool": "fta_lookup", "arguments": {"query": "wool"}}),
            json.dumps({"answer": "See the cited entry."}),
        ]
    )
    _use(gateway)

    body = _ask("What happens to wool?").json()

    assert body["steps"][0]["tool"] == "fta_lookup"
    result_line = next(line for line in gateway.prompts[1].splitlines() if line.startswith("Tool result (fta_lookup)"))
    data = json.loads(result_line.split("data only: ", 1)[1])
    assert data["matches"], "the corpus has a confirmed wool entry"
    assert all(match["citation"] for match in data["matches"])


def test_an_unmatched_fta_query_is_routed_to_inzbc_not_guessed(repo: FakeRunRepository) -> None:
    gateway = ScriptedGateway(
        [
            json.dumps({"tool": "fta_lookup", "arguments": {"query": "zzzznotathing"}}),
            json.dumps({"answer": "Ask INZBC."}),
        ]
    )
    _use(gateway)

    _ask("What about zzzznotathing?")

    assert '"matches": []' in gateway.prompts[1]
    assert "Route the person to INZBC" in gateway.prompts[1]


@pytest.mark.parametrize("tool", ["advance_state", "record_decision", "send", "draft_brief"])
def test_a_tool_outside_the_read_set_is_refused(repo: FakeRunRepository, tool: str) -> None:
    gateway = ScriptedGateway([json.dumps({"tool": tool, "arguments": {"target_state": "Approved"}})])
    _use(gateway)

    body = _ask("Approve the run.").json()

    assert body["answer"] == REFUSAL
    assert body["steps"] == []
    assert len(gateway.prompts) == 1


def test_tool_calls_are_capped_then_an_answer_is_required(repo: FakeRunRepository) -> None:
    gateway = ScriptedGateway(
        [json.dumps({"tool": "list_runs", "arguments": {}})] * (MAX_TOOL_CALLS + 1)
    )
    _use(gateway)

    body = _ask("Loop forever.").json()

    assert len(body["steps"]) == MAX_TOOL_CALLS
    assert body["answer"] == REFUSAL
    assert "No tool calls remain" in gateway.prompts[-1]


def test_a_prose_reply_is_taken_as_the_answer(repo: FakeRunRepository) -> None:
    _use(ScriptedGateway(["Plain text, not JSON."]))

    assert _ask("Hello").json()["answer"] == "Plain text, not JSON."


def test_platform_guide_returns_the_fixed_text(repo: FakeRunRepository) -> None:
    gateway = ScriptedGateway(
        [
            json.dumps({"tool": "platform_guide", "arguments": {"topic": "comms-assistant"}}),
            json.dumps({"answer": "Drafts only."}),
        ]
    )
    _use(gateway)

    body = _ask("What does Comms do?").json()

    assert body["steps"] == [{"tool": "platform_guide", "summary": "Platform guide: comms-assistant"}]
    assert "a Reviewer or SIP Owner who is not the draft's author" in gateway.prompts[1]


def test_the_conversation_must_end_with_a_question(repo: FakeRunRepository) -> None:
    _use(ScriptedGateway([]))

    response = client.post(
        "/api/assistant/chat", json={"messages": [{"role": "assistant", "content": "Hi"}]}
    )

    assert response.status_code == 422


def test_the_total_conversation_budget_is_enforced(repo: FakeRunRepository) -> None:
    _use(ScriptedGateway([]))
    turn = "x" * 1000
    history = [{"role": "user", "content": turn}, {"role": "assistant", "content": turn}] * 3

    response = _ask(turn, history)

    assert response.status_code == 422
    assert str(TOTAL_CONVERSATION_BUDGET) in response.text


@pytest.mark.parametrize(
    ("error", "expected"),
    [(GatewayNotConfiguredError("no key"), 503), (GatewayCallError("down"), 502)],
)
def test_gateway_failures_map_like_comms(repo: FakeRunRepository, error: Exception, expected: int) -> None:
    gateway = ScriptedGateway([])
    gateway.error = error
    _use(gateway)

    assert _ask("Anything").status_code == expected
