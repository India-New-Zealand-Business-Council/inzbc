from __future__ import annotations

import pytest

from services.api.model_gateway import (
    DEFAULT_MODEL,
    GatewayNotConfiguredError,
    ModelGateway,
)


def test_missing_key_fails_closed_not_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(GatewayNotConfiguredError):
        ModelGateway().complete("anything")


def test_model_defaults_to_news_agent_model_and_env_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SIP_MODEL_NAME", raising=False)
    assert ModelGateway(client=object()).model == DEFAULT_MODEL
    monkeypatch.setenv("SIP_MODEL_NAME", "gpt-5-mini")
    assert ModelGateway(client=object()).model == "gpt-5-mini"
    assert ModelGateway(client=object(), model="explicit").model == "explicit"
