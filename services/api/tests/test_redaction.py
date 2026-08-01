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


def test_gateway_sends_the_redacted_prompt_not_the_original():
    client = _RecordingClient()
    gateway = ModelGateway(client=client, redaction_rules=[EMAIL_RULE])

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


def test_gateway_refuses_an_empty_rule_set_too():
    client = _RecordingClient()
    gateway = ModelGateway(client=client, redaction_rules=[])

    with pytest.raises(RedactionNotConfiguredError):
        gateway.complete("member sunil@example.test")

    assert client.seen == []


def test_redaction_happens_before_the_api_key_is_needed(monkeypatch):
    # Redaction runs before _ensure_client, so a missing policy surfaces on a machine with no key
    # rather than being masked by GatewayNotConfiguredError.
    monkeypatch.delenv(POLICY_PATH_ENV, raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RedactionNotConfiguredError):
        ModelGateway().complete("member sunil@example.test")
