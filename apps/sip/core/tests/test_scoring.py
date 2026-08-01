from __future__ import annotations

import re

import json

import pytest

from apps.sip.core.scoring import (
    ScoringParseError,
    ScoringRecommendation,
    build_scoring_prompt,
    score_candidate,
    to_assessment,
)
from apps.sip.pipeline.models import SignalStrength, SourceConfidence
from services.api.redaction import RedactionRule
from services.api.model_gateway import GatewayCallError, ModelGateway


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.output_text = text


class _FakeResponses:
    def __init__(self, outputs: list[object]) -> None:
        self._outputs = outputs
        self.calls: list[dict] = []

    def create(self, **kwargs) -> _FakeResponse:  # noqa: ANN003
        self.calls.append(kwargs)
        result = self._outputs.pop(0)
        if isinstance(result, Exception):
            raise result
        return _FakeResponse(result)


class _FakeClient:
    def __init__(self, outputs: list[object]) -> None:
        self.responses = _FakeResponses(outputs)


VALID_PAYLOAD = {
    "nz_relevance": 4,
    "india_relevance": 3,
    "member_relevance": 5,
    "signal": "High",
    "confidence": "Medium",
    "reason": "Tariff change with direct exporter impact.",
}

CANDIDATE = {
    "headline": "India cuts tariff on NZ wool",
    "source": "MFAT",
    "published": "2026-07-24",
    "url": "https://example.org/a",
    "summary": "Tariff eliminated day one under the FTA.",
}


# Redaction runs inside the gateway on every call (#37), so a gateway built without a policy
# refuses to send. These tests are about scoring, not redaction, so they pass an explicit
# minimal rule set; the fail-closed behaviour itself is covered in
# services/api/tests/test_redaction.py.
_TEST_REDACTION = [
    RedactionRule(
        name="email",
        pattern=re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
        replacement="[redacted:email]",
    )
]


def _gateway(outputs: list[object]) -> ModelGateway:
    return ModelGateway(client=_FakeClient(outputs), redaction_rules=_TEST_REDACTION)


def test_valid_output_parses_into_validated_recommendation() -> None:
    rec = score_candidate(_gateway([json.dumps(VALID_PAYLOAD)]), **CANDIDATE)
    assert rec.signal is SignalStrength.HIGH
    assert rec.confidence is SourceConfidence.MEDIUM
    assert rec.nz_relevance == 4


def test_prompt_carries_candidate_fields_and_contract_keys() -> None:
    prompt = build_scoring_prompt(**CANDIDATE)
    assert "India cuts tariff on NZ wool" in prompt
    for key in VALID_PAYLOAD:
        assert key in prompt


def test_non_json_output_fails_closed() -> None:
    with pytest.raises(ScoringParseError):
        score_candidate(_gateway(["High signal, trust me"]), **CANDIDATE)


def test_json_array_output_fails_closed() -> None:
    with pytest.raises(ScoringParseError):
        score_candidate(_gateway([json.dumps([VALID_PAYLOAD])]), **CANDIDATE)


def test_out_of_range_relevance_fails_closed() -> None:
    bad = dict(VALID_PAYLOAD, nz_relevance=9)
    with pytest.raises(ScoringParseError):
        score_candidate(_gateway([json.dumps(bad)]), **CANDIDATE)


def test_unknown_signal_value_fails_closed() -> None:
    bad = dict(VALID_PAYLOAD, signal="Urgent")
    with pytest.raises(ScoringParseError):
        score_candidate(_gateway([json.dumps(bad)]), **CANDIDATE)


def test_gateway_retries_once_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("services.api.model_gateway._RETRY_DELAY_SECONDS", 0)
    gateway = _gateway([RuntimeError("transient"), json.dumps(VALID_PAYLOAD)])
    rec = score_candidate(gateway, **CANDIDATE)
    assert rec.member_relevance == 5


def test_gateway_surfaces_persistent_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("services.api.model_gateway._RETRY_DELAY_SECONDS", 0)
    gateway = _gateway([RuntimeError("down"), RuntimeError("still down")])
    with pytest.raises(GatewayCallError):
        score_candidate(gateway, **CANDIDATE)


def test_to_assessment_never_sets_verification() -> None:
    rec = ScoringRecommendation(**VALID_PAYLOAD)
    assessment = to_assessment(rec)
    assert assessment.verification is None
    assert assessment.signal is SignalStrength.HIGH
    assert assessment.reason == VALID_PAYLOAD["reason"]
