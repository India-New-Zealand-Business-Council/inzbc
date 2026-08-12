"""Boundary refusal and field minimisation (#223).

The control ADR-0006 calls primary, so these tests carry the weight the redaction suite cannot:
redaction is defence in depth against formatted identifiers, and this is what stops a name in
prose reaching a provider at all.

Both directions matter. Refusing too little sends member data. Refusing too much makes the
platform unusable and someone routes around it, which is the same outcome by a slower path.
"""

from __future__ import annotations

import json

import pytest

from services.api.model_gateway import ModelGateway
from services.api.prompt_boundary import (
    PERMITTED_SOURCES,
    ProhibitedInputError,
    PromptSource,
    check_source,
    minimise,
)


@pytest.mark.parametrize("source", sorted(PERMITTED_SOURCES, key=lambda s: s.value))
def test_a_permitted_source_passes(source: PromptSource) -> None:
    check_source(source)


@pytest.mark.parametrize(
    "source",
    [
        PromptSource.MEMBER_RECORD,
        PromptSource.CRM_NOTE,
        PromptSource.BOARD_MATERIAL,
        PromptSource.PRIVATE_MESSAGE,
    ],
)
def test_a_prohibited_source_is_refused(source: PromptSource) -> None:
    with pytest.raises(ProhibitedInputError):
        check_source(source)


def test_every_source_is_either_permitted_or_refused() -> None:
    """No member of the enum may be undecided.

    Adding a source and forgetting to classify it is the realistic mistake. Because
    `PERMITTED_SOURCES` is an allowlist the omission fails closed, so this test is about noticing
    rather than about safety: a source that silently became unusable is a bug too.
    """
    for source in PromptSource:
        if source in PERMITTED_SOURCES:
            check_source(source)
        else:
            with pytest.raises(ProhibitedInputError):
                check_source(source)


def test_the_refusal_says_what_to_do_instead() -> None:
    """An error naming only the rule sends the reader looking for a way around it."""
    with pytest.raises(ProhibitedInputError, match="minimise"):
        check_source(PromptSource.MEMBER_RECORD)


# ---------- minimise ----------


MEMBER = {
    "member_id": "M-4471",
    "name": "Priya Sharma",
    "job_title": "Chief Executive",
    "employer": "Koru Exports Ltd",
    "email": "priya@example.test",
    "sector": "dairy",
    "region": "Auckland",
}


def test_minimise_keeps_only_what_was_asked_for() -> None:
    assert minimise(MEMBER, ["sector", "region"]) == {"sector": "dairy", "region": "Auckland"}


def test_minimise_drops_the_prose_fields_regex_cannot_catch() -> None:
    """The whole reason this module exists.

    A name, a job title and an employer are exactly what the redaction policy cannot match, and
    they are dropped here by not being asked for rather than by being recognised.
    """
    kept = minimise(MEMBER, ["sector"])

    assert "Priya Sharma" not in json.dumps(kept)
    assert "Chief Executive" not in json.dumps(kept)
    assert "Koru Exports Ltd" not in json.dumps(kept)


def test_an_empty_allowlist_refuses_rather_than_sending_everything() -> None:
    """Fail closed. The likeliest cause is a caller that forgot to name its fields, and the
    fail-open reading of that slip sends the entire record."""
    with pytest.raises(ProhibitedInputError):
        minimise(MEMBER, [])


def test_naming_a_field_the_record_does_not_have_is_not_an_error() -> None:
    """The allowlist says what may be sent, not what must be present. A record legitimately
    missing an optional field should not fail the call."""
    assert minimise({"sector": "dairy"}, ["sector", "region"]) == {"sector": "dairy"}


def test_minimise_does_not_mutate_the_original() -> None:
    """Otherwise a caller could minimise a record and then read the trimmed original from the
    same variable, believing it still held everything."""
    record = dict(MEMBER)
    minimise(record, ["sector"])
    assert record == MEMBER


# ---------- the gateway actually enforces it ----------


class _RecordingClient:
    """Records what reached the provider. The assertion that matters is that nothing did."""

    def __init__(self) -> None:
        self.seen: list[str] = []

    class _Responses:
        def __init__(self, outer: _RecordingClient) -> None:
            self._outer = outer

        # `input` shadows the builtin deliberately: it is the provider SDK's keyword.
        def create(self, model: str, input: str):
            self._outer.seen.append(input)
            return type("R", (), {"output_text": "ok"})()

    @property
    def responses(self):
        return self._Responses(self)


def test_the_gateway_refuses_a_prohibited_source_before_the_provider(monkeypatch, tmp_path) -> None:
    """The point of wiring it into the gateway rather than leaving it a helper.

    `require_roles` was written, unit-tested and left unwired to any route for the whole of #42,
    so this suite asserts the connection and not only the function.
    """
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps({"rules": [{"name": "email", "pattern": r"[\w.+-]+@[\w-]+\.[\w.]+",
                               "replacement": "[redacted]",
                               "example": "mail sunil@example.test"}]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("REDACTION_POLICY_PATH", str(policy))
    client = _RecordingClient()

    with pytest.raises(ProhibitedInputError):
        ModelGateway(client=client).complete(
            "Delegation lead: Priya Sharma, Chief Executive, Koru Exports Ltd",
            source=PromptSource.MEMBER_RECORD,
        )

    assert client.seen == [], "a prohibited payload reached the provider"


def test_refusal_comes_before_the_redaction_policy_is_needed(monkeypatch) -> None:
    """Order matters: a prohibited payload is refused whether or not a policy is configured.

    If redaction ran first, an unconfigured deployment would report the missing policy and a
    configured one would report the prohibited source, so the same call would fail two different
    ways for reasons unrelated to the data. It would also mean a payload that must never be sent
    was being processed before anyone checked whether it was allowed.
    """
    monkeypatch.delenv("REDACTION_POLICY_PATH", raising=False)

    with pytest.raises(ProhibitedInputError):
        ModelGateway(client=_RecordingClient()).complete(
            "board minutes", source=PromptSource.BOARD_MATERIAL
        )


def test_source_has_no_default() -> None:
    """A default would be the value every caller ends up with, including the one that never
    thought about it. Omitting it must be an error at the call site, not a silent permit."""
    with pytest.raises(TypeError):
        ModelGateway(client=_RecordingClient()).complete("anything")
