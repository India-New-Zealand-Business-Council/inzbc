from __future__ import annotations

import re

import pytest

from services.api.redaction import RedactionRule
from services.api.model_gateway import (
    DEFAULT_MODEL,
    GatewayNotConfiguredError,
    ModelGateway,
)


def test_missing_key_fails_closed_not_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    # Redaction runs before the key is needed (#37), so this passes a rule set to isolate the key
    # path. The precedence between the two is pinned deliberately by
    # services/api/tests/test_redaction.py::test_redaction_happens_before_the_api_key_is_needed:
    # an unredacted payload must not be sendable even on a machine that could reach a provider.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    rules = [RedactionRule(name="email", pattern=re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), replacement="[redacted]")]
    with pytest.raises(GatewayNotConfiguredError):
        ModelGateway(redaction_rules=rules).complete("anything")


def test_model_defaults_to_news_agent_model_and_env_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SIP_MODEL_NAME", raising=False)
    assert ModelGateway(client=object()).model == DEFAULT_MODEL
    monkeypatch.setenv("SIP_MODEL_NAME", "gpt-5-mini")
    assert ModelGateway(client=object()).model == "gpt-5-mini"
    assert ModelGateway(client=object(), model="explicit").model == "explicit"
