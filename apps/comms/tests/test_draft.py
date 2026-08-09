"""Unit tests for `apps/comms/draft.py` - the pure drafting logic, no HTTP involved.

`ModelGateway.complete()` itself (redaction, provider call, retries) is proven in
`services/api/tests/test_model_gateway.py`; this file proves `generate_draft`/`build_prompt` call
it correctly and handle a blank brief, using a fake gateway that just records what it was asked
to complete.
"""

from __future__ import annotations

import pytest

from apps.comms.draft import BlankBriefError, build_prompt, generate_draft
from services.api.model_gateway import GatewayResult


class FakeGateway:
    """Records the prompt it was called with; returns a fixed `GatewayResult`."""

    def __init__(self, text: str = "a generated draft") -> None:
        self.text = text
        self.last_prompt: str | None = None

    def complete(self, prompt: str) -> GatewayResult:
        self.last_prompt = prompt
        return GatewayResult(text=self.text, model="fake-model", duration_seconds=0.0)


def test_generate_draft_returns_the_gateways_text() -> None:
    gateway = FakeGateway(text="Dear members, ...")
    result = generate_draft(gateway, "newsletter", "announce the new FTA explainer")
    assert result.text == "Dear members, ..."


def test_generate_draft_passes_the_brief_through_to_the_prompt() -> None:
    gateway = FakeGateway()
    generate_draft(gateway, "linkedin_post", "we hit 500 members this quarter")
    assert gateway.last_prompt is not None
    assert "we hit 500 members this quarter" in gateway.last_prompt


@pytest.mark.parametrize(
    ("content_type", "expected_label"),
    [
        ("newsletter", "email newsletter section"),
        ("linkedin_post", "LinkedIn post"),
        ("event_announcement", "event announcement"),
        ("member_spotlight", "member spotlight"),
    ],
)
def test_build_prompt_names_the_content_type(content_type, expected_label: str) -> None:
    prompt = build_prompt(content_type, "a brief")
    assert expected_label in prompt


def test_build_prompt_instructs_against_inventing_facts() -> None:
    # docs/modules/comms-assistant.md and CLAUDE.md both require this; asserting it here means a
    # future edit that drops the line fails a test, not just a careful re-read of the prompt.
    prompt = build_prompt("newsletter", "a brief")
    assert "do not invent" in prompt.lower()


def test_build_prompt_says_the_output_is_a_draft_for_review() -> None:
    prompt = build_prompt("newsletter", "a brief")
    assert "review" in prompt.lower()


@pytest.mark.parametrize("blank_brief", ["", "   ", "\n\t"])
def test_generate_draft_refuses_a_blank_brief(blank_brief: str) -> None:
    gateway = FakeGateway()
    with pytest.raises(BlankBriefError):
        generate_draft(gateway, "newsletter", blank_brief)
    # The refusal must happen before any call reaches the gateway - a blank brief is this
    # module's own validation failure, not something to spend a model call finding out.
    assert gateway.last_prompt is None


def test_generate_draft_propagates_gateway_errors_unchanged() -> None:
    class RaisingGateway:
        def complete(self, prompt: str) -> GatewayResult:
            raise RuntimeError("provider is down")

    with pytest.raises(RuntimeError, match="provider is down"):
        generate_draft(RaisingGateway(), "newsletter", "a brief")
