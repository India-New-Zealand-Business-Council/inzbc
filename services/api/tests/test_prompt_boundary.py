"""Boundary refusal and field minimisation (#223).

The control ADR-0006 calls primary, so these tests carry the weight the redaction suite cannot:
redaction is defence in depth against formatted identifiers, and this is what stops a name in
prose reaching a provider at all.

Both directions matter. Refusing too little sends member data. Refusing too much makes the
platform unusable and someone routes around it, which is the same outcome by a slower path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest
from pydantic import BaseModel

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


@pytest.mark.parametrize(
    "raw",
    ["public_source", "member_record", "not_a_source", 42, None],
    ids=["permitted-spelling", "prohibited-spelling", "invented", "int", "none"],
)
def test_a_bare_value_is_refused_however_it_is_spelled(raw: object) -> None:
    """`PromptSource` subclasses `str`, and that has a sharp edge this pins down.

    Two failures, one root cause. `"public_source" in PERMITTED_SOURCES` is `True` by string
    equality, so a bare string satisfied the membership test and skipped the closed set entirely.
    A bare *prohibited* string was worse: it failed on `source.value` with an `AttributeError`,
    which no caller catching `ProhibitedInputError` would see, so a refusal surfaced as a crash.

    The permitted-spelling case is the one worth keeping. It is not a bypass on its own, because a
    caller willing to write `"public_source"` could write the enum member instead. What it defeats
    is the guarantee that every value passing this check is one somebody classified.
    """
    with pytest.raises(ProhibitedInputError):
        check_source(raw)  # type: ignore[arg-type]


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


class _MemberModel(BaseModel):
    name: str
    job_title: str


@dataclass
class _MemberDataclass:
    name: str


@pytest.mark.parametrize(
    "value",
    [
        {"contact": "Priya Sharma", "title": "Chief Executive"},
        ["dairy", "Priya Sharma"],
        ("dairy", "Priya Sharma"),
        {"Priya Sharma"},
        frozenset({"Priya Sharma"}),
        b"Priya Sharma",
        bytearray(b"Priya Sharma"),
        _MemberModel(name="Priya Sharma", job_title="Chief Executive"),
        _MemberDataclass(name="Priya Sharma"),
    ],
    ids=["dict", "list", "tuple", "set", "frozenset", "bytes", "bytearray", "pydantic",
         "dataclass"],
)
def test_a_non_scalar_value_is_refused_rather_than_passed_through(value: object) -> None:
    """The first version's real hole, and the first fix's.

    Version one filtered one level deep, so allowlisting `sector` kept
    `{"sector": {"contact": "Priya Sharma, Chief Executive"}}` whole.

    Version two refused a list of container types, which is a denylist in a module that argues for
    allowlists five lines earlier. The last five cases here are what walked through it: `frozenset`
    is not a subclass of `set`, `bytes` is not a container by that test, and a pydantic model or a
    dataclass is neither. This repository is pydantic throughout, so a record holding a model is
    the likely shape rather than a contrived one.

    The check is now an allowlist of scalar types, so a type nobody thought about is refused.
    """
    with pytest.raises(ProhibitedInputError, match="non-scalar"):
        minimise({"sector": value}, ["sector"])


def test_the_scalar_types_a_record_actually_carries_still_pass() -> None:
    """Refusing must not become the common case, or callers route around it.

    Dates and decimals are here because a record legitimately carries them and requiring a caller
    to stringify a date first would be friction with no safety in return.
    """
    record = {
        "sector": "dairy", "count": 5, "share": 1.5, "active": True,
        "note": None, "value": Decimal("1.5"), "signed": date(2026, 8, 13),
    }
    assert minimise(record, list(record)) == record


def test_a_nested_field_nobody_allowlisted_is_simply_dropped() -> None:
    """Refusing must not become the common case.

    Only a nested value that survived the allowlist is a problem. One that was never asked for is
    dropped like any other field, so a record full of structure does not become unusable because
    of a subtree the caller had no interest in.
    """
    record = {"profile": {"contact": "Priya Sharma"}, "region": "Auckland"}
    assert minimise(record, ["region"]) == {"region": "Auckland"}


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
