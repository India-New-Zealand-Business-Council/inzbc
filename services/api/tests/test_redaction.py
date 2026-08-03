"""Redaction is refused rather than skipped when nothing has been decided (#37).

The point of these tests is the fail-closed direction. It is easy to write a redaction layer that
does nothing useful when unconfigured; the whole value here is that an unconfigured deployment
cannot send at all.
"""

from __future__ import annotations

import json
import re

import pytest

from services.api.model_gateway import ModelGateway
from services.api.redaction import (
    MAX_PAYLOAD_CHARS,
    POLICY_PATH_ENV,
    RedactionNotConfiguredError,
    RedactionPolicyError,
    RedactionRule,
    load_policy,
    redact,
)


def _policy_file(tmp_path, rules: list[dict]) -> str:
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"rules": rules}), encoding="utf-8")
    return str(path)


EMAIL_POLICY = {
    "name": "email",
    "pattern": r"[\w.+-]+@[\w-]+\.[\w.]+",
    "replacement": "[redacted:email]",
}

EMAIL_RULE = RedactionRule(
    name="email",
    pattern=re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    replacement="[redacted:email]",
)


class _RecordingClient:
    """Captures what would have gone to the provider."""

    def __init__(self) -> None:
        self.seen: list[str] = []
        self.responses = self

    def create(self, model: str, input: str):  # noqa: A002 - matches the provider's kwarg
        self.seen.append(input)
        return type("Response", (), {"output_text": "ok"})()


# --- the four ways this layer gave false assurance, each now refused -------------------------


def test_a_backreference_replacement_is_refused(monkeypatch, tmp_path):
    """The worst one: it sent the secret through while recording a successful redaction.

    `re.sub` expands `\\1`, so a rule capturing the email and replacing it with `\\1` emitted the
    original address and counted a hit. An audit trail saying "1 email redacted" over an unredacted
    payload is worse than having no redaction at all.
    """
    path = _policy_file(tmp_path, [
        {"name": "email", "pattern": r"([\w.+-]+@[\w-]+\.[\w.]+)", "replacement": "\\1"},
    ])
    monkeypatch.setenv(POLICY_PATH_ENV, path)
    with pytest.raises(RedactionPolicyError, match="backreference"):
        load_policy()


def test_a_rule_matching_the_empty_string_is_refused(monkeypatch, tmp_path):
    monkeypatch.setenv(POLICY_PATH_ENV, _policy_file(tmp_path, [
        {"name": "everything", "pattern": "x*", "replacement": "[redacted]"},
    ]))
    with pytest.raises(RedactionPolicyError, match="empty string"):
        load_policy()


def test_a_later_rule_cannot_put_back_what_an_earlier_one_removed():
    """Rules used to chain, so B saw A's output and could reverse it."""
    unmask = RedactionRule(name="unmask", pattern=re.compile(r"\[member\]"),
                           replacement="Alice Smith")
    mask = RedactionRule(name="member", pattern=re.compile(r"Alice Smith"),
                         replacement="[member]")

    result = redact("brief from Alice Smith", [mask, unmask])

    assert "Alice Smith" not in result.text
    assert "[member]" in result.text


def test_an_earlier_rule_cannot_stop_a_later_one_matching():
    """The accidental version of the same bug, and the more likely one.

    Masking the label first meant `Member ID: 123456` no longer matched the rule that would have
    removed the number, so the identifier survived. Matching against the original text fixes it.
    """
    label = RedactionRule(name="label", pattern=re.compile(r"Member ID:"), replacement="[label]")
    member_id = RedactionRule(name="member-id", pattern=re.compile(r"Member ID:\s*\d+"),
                              replacement="[member-id]")

    result = redact("Member ID: 123456", [label, member_id])

    assert "123456" not in result.text
    # Both rules contributed to the merged region, so both are credited.
    assert result.counts == {"label": 1, "member-id": 1}


def test_an_oversized_payload_is_refused_rather_than_scanned():
    """Python's `re` has no match timeout, so a bounded payload is the only cheap defence.

    A pathological pattern against unbounded input hangs the worker; `(a+)+$` needed only about 31
    characters to do it. Capping the input does not make a bad rule safe, and the policy doc says
    so, but it removes the unbounded case.
    """
    rule = RedactionRule(name="x", pattern=re.compile("zzz"), replacement="[redacted]")
    with pytest.raises(RedactionPolicyError, match="over the"):
        redact("a" * (MAX_PAYLOAD_CHARS + 1), [rule])


def test_a_duplicate_json_key_is_refused(monkeypatch, tmp_path):
    """Last-key-wins would let a reviewed rule be replaced by one nobody approved."""
    path = tmp_path / "dupe.json"
    path.write_text(
        '{"rules": [{"name": "email", "name": "other", "pattern": "a", "replacement": "[r]"}]}',
        encoding="utf-8",
    )
    monkeypatch.setenv(POLICY_PATH_ENV, str(path))
    with pytest.raises(RedactionPolicyError, match="duplicate key"):
        load_policy()


def test_there_is_no_way_to_hand_the_gateway_its_own_rules(monkeypatch):
    """The escape hatch is gone, not merely discouraged.

    It used to accept an injected rule set, so a list of rules matching nothing counted as
    "configured" and sent the payload with an empty audit trail. The constructor no longer takes
    one, so a caller cannot express that at all.
    """
    import inspect

    assert "redaction_rules" not in inspect.signature(ModelGateway.__init__).parameters


def test_no_policy_configured_refuses_rather_than_sending(monkeypatch):
    monkeypatch.delenv(POLICY_PATH_ENV, raising=False)
    with pytest.raises(RedactionNotConfiguredError):
        redact("anything")


def test_a_missing_policy_file_refuses(monkeypatch, tmp_path):
    monkeypatch.setenv(POLICY_PATH_ENV, str(tmp_path / "absent.json"))
    with pytest.raises(RedactionNotConfiguredError):
        redact("anything")


def test_an_empty_rule_list_is_a_mistake_not_a_decision(monkeypatch, tmp_path):
    # A policy declaring no rules is refused. Otherwise "we have not decided yet" and "nothing is
    # confidential" would be the same configuration.
    monkeypatch.setenv(POLICY_PATH_ENV, _policy_file(tmp_path, []))
    with pytest.raises(RedactionPolicyError):
        load_policy()


def test_an_invalid_pattern_is_reported_by_rule_name(monkeypatch, tmp_path):
    path = _policy_file(tmp_path, [{"name": "broken", "pattern": "([", "replacement": "x"}])
    monkeypatch.setenv(POLICY_PATH_ENV, path)
    with pytest.raises(RedactionPolicyError, match="broken"):
        load_policy()


def test_rules_apply_and_are_counted_without_quoting_the_match():
    result = redact("write to sunil@example.test and board@example.test", [EMAIL_RULE])

    assert "sunil@example.test" not in result.text
    assert "board@example.test" not in result.text
    assert result.counts == {"email": 2}
    assert result.redacted is True
    # The audit record must not carry what it redacted.
    assert "example.test" not in json.dumps(result.counts)


def test_a_clean_payload_records_no_matches_but_still_ran():
    result = redact("nothing sensitive here", [EMAIL_RULE])
    assert result.text == "nothing sensitive here"
    assert result.counts == {}
    assert result.redacted is False


def test_gateway_sends_the_redacted_prompt_not_the_original(monkeypatch, tmp_path):
    monkeypatch.setenv(POLICY_PATH_ENV, _policy_file(tmp_path, [EMAIL_POLICY]))
    client = _RecordingClient()
    gateway = ModelGateway(client=client)

    result = gateway.complete("score this: member sunil@example.test asked about dairy")

    assert client.seen, "the provider was never called"
    sent = client.seen[0]
    assert "sunil@example.test" not in sent
    assert "[redacted:email]" in sent
    assert result.redaction_counts == {"email": 1}


def test_gateway_refuses_the_call_when_no_policy_is_configured(monkeypatch):
    # The important one. A caller that forgets to configure redaction does not get an unredacted
    # send; it gets an error, and the provider is never reached.
    monkeypatch.delenv(POLICY_PATH_ENV, raising=False)
    client = _RecordingClient()
    gateway = ModelGateway(client=client)

    with pytest.raises(RedactionNotConfiguredError):
        gateway.complete("member sunil@example.test")

    assert client.seen == [], "a payload reached the provider despite no redaction policy"


def test_a_policy_declaring_no_rules_is_refused(monkeypatch, tmp_path):
    # There is no longer any way to hand the gateway an empty rule set: the injectable parameter is
    # gone precisely because "non-empty list" was not the same as "redaction configured". The
    # remaining way to express emptiness is a policy file with no rules, and that is refused.
    monkeypatch.setenv(POLICY_PATH_ENV, _policy_file(tmp_path, []))
    client = _RecordingClient()
    gateway = ModelGateway(client=client)

    with pytest.raises(RedactionPolicyError):
        gateway.complete("member sunil@example.test")

    assert client.seen == []


def test_redaction_happens_before_the_api_key_is_needed(monkeypatch):
    # Redaction runs before _ensure_client, so a missing policy surfaces on a machine with no key
    # rather than being masked by GatewayNotConfiguredError.
    monkeypatch.delenv(POLICY_PATH_ENV, raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RedactionNotConfiguredError):
        ModelGateway().complete("member sunil@example.test")
