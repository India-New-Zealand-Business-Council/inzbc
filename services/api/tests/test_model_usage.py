from __future__ import annotations

import json
import logging
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from services.api import model_gateway, model_usage
from services.api.model_gateway import (
    GatewayAuditError,
    GatewayCallError,
    GatewayNotConfiguredError,
    ModelGateway,
    _cost,
    _token_count,
)
from services.api.model_usage import ModelUsage, record_usage
from services.api.prompt_boundary import ProhibitedInputError, PromptSource


@pytest.fixture(autouse=True)
def configuration(tmp_path, monkeypatch):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"rules": [{
        "name": "email", "pattern": r"\S+@\S+", "replacement": "[email]",
        "example": "synthetic@example.test",
    }]}), encoding="utf-8")
    monkeypatch.setenv("REDACTION_POLICY_PATH", str(path))
    for key in ("DATABASE_URL", "SIP_MODEL_PROVIDER", "SIP_MODEL_NAME",
                "SIP_MODEL_INPUT_USD_PER_MILLION", "SIP_MODEL_OUTPUT_USD_PER_MILLION"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(model_gateway, "_RETRY_DELAY_SECONDS", 0)


class Client:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.responses = self
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def response(**usage):
    return SimpleNamespace(output_text="synthetic result", usage=SimpleNamespace(**usage))


def test_metadata_and_redacted_input_share_the_selected_provider(monkeypatch):
    monkeypatch.setenv("SIP_MODEL_INPUT_USD_PER_MILLION", "2")
    monkeypatch.setenv("SIP_MODEL_OUTPUT_USD_PER_MILLION", "4")
    client = Client([response(input_tokens=100, output_tokens=50)])
    records = []
    result = ModelGateway(client, model="test-model", provider="perplexity", usage_sink=records.append)
    output = result.complete("mail synthetic@example.test", source=PromptSource.PUBLIC_SOURCE)
    assert client.calls == [{
        "model": "test-model", "input": "mail [email]", "store": False,
        "extra_body": {"tools": []},
    }]
    assert output.provider == "perplexity"
    assert output.input_tokens == 100 and output.output_tokens == 50
    assert output.cost_usd == "0.0004"
    assert output.cost_basis == "configured_token_estimate"
    assert records[0].attempts == 1 and records[0].succeeded
    assert "synthetic@example.test" not in json.dumps(asdict(records[0]))
    assert "synthetic result" not in json.dumps(asdict(records[0]))


def test_reported_provider_cost_is_preserved_without_guessing_rates():
    client = Client([response(input_tokens=5, output_tokens=3, cost={
        "currency": "USD", "total_cost": "0.0123",
    })])
    result = ModelGateway(client, usage_sink=lambda _: None).complete(
        "public synthetic text", source=PromptSource.PUBLIC_SOURCE
    )
    assert result.cost_usd == "0.0123" and result.cost_basis == "provider_reported"


def test_missing_usage_is_unknown_not_zero():
    result = ModelGateway(Client([response()]), usage_sink=lambda _: None).complete(
        "synthetic", source=PromptSource.PUBLIC_SOURCE
    )
    assert result.input_tokens is None and result.cost_usd is None


def test_audit_failure_does_not_repeat_a_billable_provider_call():
    client = Client([response()])

    def broken_sink(_):
        raise RuntimeError("synthetic database failure")

    with pytest.raises(GatewayAuditError):
        ModelGateway(client, usage_sink=broken_sink).complete(
            "synthetic", source=PromptSource.PUBLIC_SOURCE
        )
    assert len(client.calls) == 1


def test_exhausted_retries_record_failure_without_error_or_content():
    records = []
    client = Client([RuntimeError("private detail"), RuntimeError("private detail")])
    with pytest.raises(GatewayCallError):
        ModelGateway(client, usage_sink=records.append).complete(
            "synthetic", source=PromptSource.PUBLIC_SOURCE
        )
    assert len(client.calls) == 2
    assert len(records) == 1 and records[0].attempts == 2 and not records[0].succeeded
    assert "private detail" not in json.dumps(asdict(records[0]))


def test_retry_then_success_records_attempt_count():
    records = []
    ModelGateway(Client([RuntimeError(), response()]), usage_sink=records.append).complete(
        "synthetic", source=PromptSource.PUBLIC_SOURCE
    )
    assert records[0].attempts == 2 and records[0].succeeded


@pytest.mark.parametrize("text", [None, "", "   ", 1])
def test_empty_or_wrong_typed_provider_output_is_not_success(text):
    client = Client([SimpleNamespace(output_text=text), SimpleNamespace(output_text=text)])
    with pytest.raises(GatewayCallError):
        ModelGateway(client, usage_sink=lambda _: None).complete(
            "synthetic", source=PromptSource.PUBLIC_SOURCE
        )


@pytest.mark.parametrize("provider", ["unknown", "OPENAI", "https://example.test"])
def test_unknown_provider_fails_closed(provider):
    with pytest.raises(GatewayNotConfiguredError):
        ModelGateway(provider=provider)


def test_perplexity_needs_an_explicit_model():
    with pytest.raises(GatewayNotConfiguredError, match="explicit"):
        ModelGateway(provider="perplexity")


@pytest.mark.parametrize("provider,key_name,base_url", [
    ("openai", "OPENAI_API_KEY", None),
    ("perplexity", "PERPLEXITY_API_KEY", "https://api.perplexity.ai/v1"),
])
def test_live_client_configuration_has_fixed_endpoint_and_no_nested_retries(
    monkeypatch, provider, key_name, base_url
):
    import openai

    options = []
    monkeypatch.setenv(key_name, "synthetic-test-value")
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: options.append(kwargs) or object())
    ModelGateway(model="explicit-model", provider=provider)._ensure_client()
    assert options[0]["max_retries"] == 0 and options[0]["timeout"] == 30
    assert options[0].get("base_url") == base_url


def test_missing_perplexity_key_does_not_fall_back_to_openai(monkeypatch):
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-value")
    with pytest.raises(GatewayNotConfiguredError, match="PERPLEXITY_API_KEY"):
        ModelGateway(model="explicit-model", provider="perplexity")._ensure_client()


@pytest.mark.parametrize("value", [-1, True, "3", 3.0, None])
def test_invalid_usage_is_unknown(value):
    assert _token_count(value) is None


@pytest.mark.parametrize("value", [0, 3])
def test_valid_usage_count(value):
    assert _token_count(value) == value


@pytest.mark.parametrize("cost", ["NaN", "Infinity", "-1", "invalid", None])
def test_bad_reported_cost_is_unknown(cost):
    assert _cost(SimpleNamespace(cost={"currency": "USD", "total_cost": cost}), 1, 1) == (
        None, "unknown"
    )


@pytest.mark.parametrize("rate", ["NaN", "-1", "bad"])
def test_bad_configured_rate_is_unknown(monkeypatch, rate):
    monkeypatch.setenv("SIP_MODEL_INPUT_USD_PER_MILLION", rate)
    monkeypatch.setenv("SIP_MODEL_OUTPUT_USD_PER_MILLION", "1")
    assert _cost(None, 1, 1) == (None, "unknown")


def test_local_sink_logs_only_metadata(caplog):
    with caplog.at_level(logging.INFO, logger="services.api.model_usage"):
        record_usage(ModelUsage("openai", "test-model", 0.5, 1, True))
    assert caplog.records[-1].model_usage["model"] == "test-model"
    assert set(caplog.records[-1].model_usage) == set(ModelUsage.__dataclass_fields__)


def test_configured_database_sink_uses_existing_transactional_audit(monkeypatch):
    from contextlib import nullcontext

    writes = []
    connection = object()
    monkeypatch.setenv("DATABASE_URL", "synthetic-dsn")
    monkeypatch.setattr(model_usage.psycopg, "connect", lambda _: nullcontext(connection))
    monkeypatch.setattr(model_usage, "record_audit", lambda conn, **kwargs: writes.append((conn, kwargs)))
    record_usage(ModelUsage("openai", "test-model", 0.5, 1, True, 2, 3))
    assert writes[0][0] is connection
    assert writes[0][1]["action"] == "model.call"
    assert json.loads(writes[0][1]["new_value"])["input_tokens"] == 2


class EventStream:
    """A provider stream: iterable events plus the `close()` the SDK's Stream exposes."""

    def __init__(self, events):
        self.events = events
        self.closed = False

    def __iter__(self):
        yield from self.events

    def close(self):
        self.closed = True


def delta(text):
    return SimpleNamespace(type="response.output_text.delta", delta=text)


def completed(**usage):
    return SimpleNamespace(type="response.completed", response=response(**usage))


def test_stream_yields_redacted_call_deltas_and_records_usage_once():
    stream = EventStream([delta("Kia "), delta("ora"), completed(input_tokens=7, output_tokens=2)])
    client = Client([stream])
    records = []
    deltas = ModelGateway(client, model="test-model", usage_sink=records.append).stream(
        "mail synthetic@example.test", source=PromptSource.PUBLIC_SOURCE
    )
    assert list(deltas) == ["Kia ", "ora"]
    assert client.calls == [{
        "model": "test-model", "input": "mail [email]", "store": False, "stream": True,
    }]
    assert stream.closed
    assert len(records) == 1 and records[0].succeeded and records[0].output_tokens == 2


def test_stream_refuses_before_any_provider_call():
    client = Client([])
    with pytest.raises(ProhibitedInputError):
        ModelGateway(client, usage_sink=lambda _: None).stream(
            "synthetic", source=PromptSource.MEMBER_RECORD
        )
    assert client.calls == []


def test_abandoned_stream_closes_upstream_and_records_failure():
    stream = EventStream([delta("one"), delta("two"), completed()])
    records = []
    deltas = ModelGateway(Client([stream]), usage_sink=records.append).stream(
        "synthetic", source=PromptSource.PUBLIC_SOURCE
    )
    assert next(deltas) == "one"
    deltas.close()
    assert stream.closed
    assert len(records) == 1 and not records[0].succeeded


@pytest.mark.parametrize("ending", [
    [SimpleNamespace(type="response.failed", response=response())],
    [SimpleNamespace(type="error", message="private detail")],
    [],
])
def test_stream_without_completion_is_a_failure(ending):
    stream = EventStream([delta("partial"), *ending])
    records = []
    deltas = ModelGateway(Client([stream]), usage_sink=records.append).stream(
        "synthetic", source=PromptSource.PUBLIC_SOURCE
    )
    with pytest.raises(GatewayCallError):
        list(deltas)
    assert stream.closed
    assert len(records) == 1 and not records[0].succeeded


def test_stream_is_not_retried_when_it_fails_to_start():
    client = Client([RuntimeError("private detail")])
    records = []
    deltas = ModelGateway(client, usage_sink=records.append).stream(
        "synthetic", source=PromptSource.PUBLIC_SOURCE
    )
    with pytest.raises(GatewayCallError):
        next(deltas)
    assert len(client.calls) == 1
    assert len(records) == 1 and not records[0].succeeded
