from __future__ import annotations

import json


import pytest

from services.api.model_gateway import (
    DEFAULT_MODEL,
    GatewayNotConfiguredError,
    ModelGateway,
)


def test_missing_key_fails_closed_not_silent(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    # Redaction runs before the key is needed (#37), so this passes a rule set to isolate the key
    # path. The precedence between the two is pinned deliberately by
    # services/api/tests/test_redaction.py::test_redaction_happens_before_the_api_key_is_needed:
    # an unredacted payload must not be sendable even on a machine that could reach a provider.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps({"rules": [{"name": "email", "pattern": r"[\w.+-]+@[\w-]+\.[\w.]+",
                               "replacement": "[redacted]"}]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("REDACTION_POLICY_PATH", str(policy))
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
