"""Unit tests for `apps/comms/draft.py` - the pure drafting logic, no HTTP involved.

`ModelGateway.complete()` itself (redaction, provider call, retries) is proven in
`services/api/tests/test_model_gateway.py`; this file proves `generate_draft`/`build_prompt` call
it correctly and handle a blank brief, using a fake gateway that just records what it was asked
to complete.
"""

from __future__ import annotations

import pytest

from apps.comms.draft import BlankBriefError, Brief, build_prompt, generate_draft
from services.api.model_gateway import GatewayResult
from services.api.prompt_boundary import PromptSource


class FakeGateway:
    """Records the prompt it was called with; returns a fixed `GatewayResult`."""

    def __init__(self, text: str = "a generated draft") -> None:
        self.text = text
        self.last_prompt: str | None = None
        self.last_source: PromptSource | None = None

    def complete(self, prompt: str, *, source: PromptSource) -> GatewayResult:
        self.last_prompt = prompt
        self.last_source = source
        return GatewayResult(text=self.text, model="fake-model", duration_seconds=0.0)


def test_generate_draft_returns_the_gateways_text() -> None:
    gateway = FakeGateway(text="Dear members, ...")
    result = generate_draft(gateway, "newsletter", Brief(topic="announce the new FTA explainer"))
    assert result.text == "Dear members, ..."


def test_generate_draft_passes_the_brief_through_to_the_prompt() -> None:
    gateway = FakeGateway()
    generate_draft(gateway, "linkedin_post", Brief(topic="we hit 500 members this quarter"))
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
    prompt = build_prompt(content_type, Brief(topic="a brief"))
    assert expected_label in prompt


def test_build_prompt_instructs_against_inventing_facts() -> None:
    # docs/modules/comms-assistant.md and CLAUDE.md both require this; asserting it here means a
    # future edit that drops the line fails a test, not just a careful re-read of the prompt.
    prompt = build_prompt("newsletter", Brief(topic="a brief"))
    assert "do not invent" in prompt.lower()


def test_build_prompt_says_the_output_is_a_draft_for_review() -> None:
    prompt = build_prompt("newsletter", Brief(topic="a brief"))
    assert "review" in prompt.lower()


@pytest.mark.parametrize("blank_topic", ["", "   ", "\n\t"])
def test_generate_draft_refuses_a_blank_brief(blank_topic: str) -> None:
    gateway = FakeGateway()
    with pytest.raises(BlankBriefError):
        generate_draft(gateway, "newsletter", Brief(topic=blank_topic))
    # The refusal must happen before any call reaches the gateway - a blank brief is this
    # module's own validation failure, not something to spend a model call finding out.
    assert gateway.last_prompt is None


def test_a_blank_topic_is_still_a_brief_if_it_has_key_points() -> None:
    """Blankness is about the whole brief, not the topic alone.

    Refusing on an empty topic while key points carry real content would reject a usable brief,
    and `is_blank()` exists so that rule lives in one place rather than at each call site.
    """
    gateway = FakeGateway()
    generate_draft(gateway, "newsletter", Brief(topic="  ", key_points=("500 members reached",)))
    assert gateway.last_prompt is not None
    assert "500 members reached" in gateway.last_prompt


def test_the_rendered_brief_carries_every_field() -> None:
    brief = Brief(
        topic="FTA explainer launch",
        key_points=("tariffs drop to zero", "wool and dairy covered"),
        links=("https://example.invalid/fta",),
        tone="concise",
    )
    rendered = brief.render()
    for expected in (
        "FTA explainer launch",
        "tariffs drop to zero",
        "wool and dairy covered",
        "https://example.invalid/fta",
        "short and direct",
    ):
        assert expected in rendered


def test_generate_draft_propagates_gateway_errors_unchanged() -> None:
    class RaisingGateway:
        def complete(self, prompt: str, *, source: PromptSource) -> GatewayResult:
            raise RuntimeError("provider is down")

    with pytest.raises(RuntimeError, match="provider is down"):
        generate_draft(RaisingGateway(), "newsletter", Brief(topic="a brief"))


def test_the_draft_flow_declares_staff_authored_text() -> None:
    """The declaration is a decision, so it is asserted rather than left to the call site.

    A brief is prose a staff member typed, and #223's boundary refusal turns on which source a
    caller names. Quietly changing this to a permitted-but-wrong value, or to one that would be
    refused, should fail here rather than in production.
    """
    gateway = FakeGateway()
    generate_draft(gateway, "newsletter", Brief(topic="announce the FTA explainer"))
    assert gateway.last_source is PromptSource.STAFF_AUTHORED
