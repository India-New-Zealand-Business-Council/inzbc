"""Model gateway: the single server-side path for every model call on the platform.

SIP's spec (docs/sip/README.md non-negotiables) requires all model calls server-side with keys
never reaching a browser; this module is where that happens. SIP scoring, the Comms Assistant
and the FTA layer call through here rather than constructing their own clients, so provider,
model, timeout and retry policy are decided once.

The default remains OpenAI with `gpt-4.1-mini`. Perplexity is an explicitly selected second
provider through the same Responses interface; it requires its own key and an explicit model.
Usage metadata is logged without content and persisted when a database is configured.
See docs/model-gateway.md for configuration and the limits of cost estimates and audit storage.

Two controls sit here, in this order.

**Boundary refusal (#223).** Every call names a `PromptSource`, and a prohibited origin is refused
before a policy is read or a key is looked up. Per ADR-0006 this is the *primary* control: regex
redaction cannot catch a name, job title or employer in ordinary prose, so the answer for that data
is not to send it. See `prompt_boundary.py` for what this does and does not enforce.

**Redaction (#37).** Every prompt is then redacted before it reaches a provider. Both live in the
gateway rather than in each caller for the same reason the client does: a control that every caller
has to remember is a control that one caller will forget. With no policy configured the call is
refused, so a deployment that has not decided what counts as confidential sends nothing at all.

Configuration (environment):
- OPENAI_API_KEY          - required for live calls; absent -> GatewayNotConfiguredError.
- SIP_MODEL_NAME          - optional, defaults to gpt-4.1-mini.
- REDACTION_POLICY_PATH   - required; absent -> RedactionNotConfiguredError. See redaction.py.
- SIP_MODEL_PROVIDER      - openai (default) or perplexity; never an automatic fallback.
- PERPLEXITY_API_KEY      - required only when selecting perplexity.

No key, endpoint or model name is ever hardcoded beyond that default.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Generator
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from services.api.model_usage import ModelUsage, record_usage
from services.api.prompt_boundary import PromptSource, check_source
from services.api.redaction import redact

DEFAULT_MODEL = "gpt-4.1-mini"
_RETRYABLE_ATTEMPTS = 2  # one retry on a transient failure, then surface the error
_RETRY_DELAY_SECONDS = 2.0


class GatewayNotConfiguredError(RuntimeError):
    """No API key available. Raised at call time so a misconfigured deployment fails loudly
    instead of silently producing nothing - never substitute a canned response.
    """


class GatewayCallError(RuntimeError):
    """The provider call failed after retries. Callers treat this as "no recommendation", not
    as an empty answer.
    """


class GatewayAuditError(GatewayCallError):
    """Usage could not be recorded; never retry an already-completed provider call."""


@dataclass(frozen=True)
class GatewayResult:
    """A completed call: the text plus enough metadata for the audit trail."""

    text: str
    model: str
    duration_seconds: float
    # Which redaction rules fired, by name and count. Never the matched text: an audit trail that
    # quotes what it redacted has not redacted it. Empty means the policy ran and matched nothing,
    # which is different from redaction not having run, because an unredacted call cannot happen.
    redaction_counts: dict[str, int] = field(default_factory=dict)
    provider: str = "openai"
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: str | None = None
    cost_basis: str = "unknown"


class ModelGateway:
    """Thin, injectable wrapper over the provider client.

    `client` is anything exposing the OpenAI Responses API shape used by the news agent
    (`client.responses.create(model=..., input=...)` returning an object with `output_text`).
    Tests inject a fake; production omits it and the gateway builds a real client from the
    environment on first use.
    """

    def __init__(
        self,
        client: object | None = None,
        model: str | None = None,
        *,
        provider: str | None = None,
        usage_sink: Callable[[ModelUsage], None] | None = None,
    ) -> None:
        self._client = client
        self.provider = provider or os.getenv("SIP_MODEL_PROVIDER", "openai")
        if self.provider not in {"openai", "perplexity"}:
            raise GatewayNotConfiguredError("SIP_MODEL_PROVIDER must be openai or perplexity")
        configured_model = model or os.getenv("SIP_MODEL_NAME")
        if self.provider == "perplexity" and not configured_model:
            raise GatewayNotConfiguredError("Perplexity requires an explicit SIP_MODEL_NAME")
        self.model = configured_model or DEFAULT_MODEL
        self._usage_sink = usage_sink or record_usage

    def _ensure_client(self) -> object:
        if self._client is None:
            key_name = "OPENAI_API_KEY" if self.provider == "openai" else "PERPLEXITY_API_KEY"
            api_key = os.getenv(key_name)
            if not api_key:
                raise GatewayNotConfiguredError(
                    f"{key_name} is not set - the gateway will not fabricate a response."
                )
            from openai import OpenAI  # imported lazily so tests never need the package

            options = {"api_key": api_key, "timeout": 30.0, "max_retries": 0}
            if self.provider == "perplexity":
                options["base_url"] = "https://api.perplexity.ai/v1"
            self._client = OpenAI(**options)
        return self._client

    def complete(self, prompt: str, *, source: PromptSource) -> GatewayResult:
        """One prompt in, text out, with a single retry on a transient provider failure.

        `source` names where the text came from, and a prohibited origin is refused before
        anything else happens (#223, ADR-0006 §1). It is keyword-only and has **no default**: a
        default would be the value every caller ends up with, including the one that never thought
        about it, and the whole point is that a new call site cannot be written without answering
        the question.

        This is a declaration rather than a verification, and the docstring says so rather than
        implying more. By the time text reaches here the structure is gone, so nothing about the
        string reveals its origin and a caller that declares the wrong source is not caught. What
        it does buy is that the question is unavoidable and the answer is reviewable in the diff.
        The enforceable half is `minimise()`, applied before assembly.

        The prompt is then redacted, against the policy at `REDACTION_POLICY_PATH`. Refusal,
        redaction and `_ensure_client` run in that order, so a prohibited payload is refused
        without consulting a policy or a key, and a missing policy is reported even on a machine
        with no API key. Nothing unredacted can leave the process while either is being argued
        about.

        There is deliberately no way for a caller to supply its own rules. An earlier version took
        an injectable rule set so tests need not write a policy file; that made "redaction is
        configured" mean only "a non-empty list was passed", and a list of rules matching nothing
        would have sailed through with an empty audit trail. Tests now point
        `REDACTION_POLICY_PATH` at a real file, the same way production does.
        """
        check_source(source)
        redaction = redact(prompt)
        client = self._ensure_client()
        started = time.monotonic()
        last_error: Exception | None = None
        for attempt in range(_RETRYABLE_ATTEMPTS):
            try:
                request = {"model": self.model, "input": redaction.text, "store": False}
                if self.provider == "perplexity":
                    request["extra_body"] = {"tools": []}
                response = client.responses.create(**request)
                text = response.output_text
                if not isinstance(text, str) or not text.strip():
                    raise GatewayCallError("provider returned no usable text")
                break
            except GatewayNotConfiguredError:
                raise
            # Deliberately broad, rather than a narrower except: provider and network error
            # types differ by SDK version, so naming them would silently stop retrying when a
            # dependency bump renames one.
            except Exception as error:  # noqa: BLE001
                last_error = error
                if attempt + 1 < _RETRYABLE_ATTEMPTS:
                    time.sleep(_RETRY_DELAY_SECONDS)
        else:
            self._record_usage(started, _RETRYABLE_ATTEMPTS, False)
            raise GatewayCallError(
                f"model call failed after {_RETRYABLE_ATTEMPTS} attempts"
            ) from last_error
        usage = self._record_usage(started, attempt + 1, True, response)
        return GatewayResult(
            text=text, model=self.model, duration_seconds=usage.duration_seconds,
            redaction_counts=dict(redaction.counts), provider=self.provider,
            input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
            cost_usd=usage.cost_usd, cost_basis=usage.cost_basis,
        )

    def stream(self, prompt: str, *, source: PromptSource) -> Generator[str, None, None]:
        """Same controls as `complete()`, yielding text deltas as the provider produces them (#65).

        Refusal, redaction and the key check run here, eagerly, before the generator exists, so a
        caller sees those failures before it has started a response. The provider call itself
        starts on the first `next()`.

        No retry: once text has been handed to a reader, repeating the call would duplicate it and
        bill twice. Closing the generator (a reader that went away) closes the upstream stream, and
        usage is recorded once however the stream ends, as a failure unless it completed.
        """
        check_source(source)
        redaction = redact(prompt)
        client = self._ensure_client()
        return self._stream(client, redaction.text)

    def _stream(self, client: object, text: str) -> Generator[str, None, None]:
        started = time.monotonic()
        request = {"model": self.model, "input": text, "store": False, "stream": True}
        if self.provider == "perplexity":
            request["extra_body"] = {"tools": []}
        try:
            events = client.responses.create(**request)
        except Exception as error:
            self._record_usage(started, 1, False)
            raise GatewayCallError("model stream failed to start") from error
        completed = None
        emitted = False
        try:
            for event in events:
                kind = getattr(event, "type", None)
                if kind == "response.output_text.delta":
                    emitted = emitted or bool(event.delta)
                    yield event.delta
                elif kind == "response.completed":
                    completed = event.response
                elif kind in {"error", "response.failed", "response.incomplete"}:
                    raise GatewayCallError(f"provider stream ended with {kind}")
            if completed is None or not emitted:
                raise GatewayCallError("provider stream ended without usable text")
        finally:
            close = getattr(events, "close", None)
            if close is not None:
                close()
            succeeded = completed is not None and emitted
            self._record_usage(started, 1, succeeded, completed)

    def _record_usage(
        self, started: float, attempts: int, succeeded: bool, response: object | None = None
    ) -> ModelUsage:
        raw = getattr(response, "usage", None)
        input_tokens = _token_count(getattr(raw, "input_tokens", None))
        output_tokens = _token_count(getattr(raw, "output_tokens", None))
        cost, basis = _cost(raw, input_tokens, output_tokens)
        usage = ModelUsage(
            provider=self.provider, model=self.model, duration_seconds=time.monotonic() - started,
            attempts=attempts, succeeded=succeeded, input_tokens=input_tokens,
            output_tokens=output_tokens, cost_usd=cost, cost_basis=basis,
        )
        try:
            self._usage_sink(usage)
        except Exception as error:
            raise GatewayAuditError("model usage audit failed; provider call not retried") from error
        return usage


def _token_count(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _cost(raw: object, inputs: int | None, outputs: int | None) -> tuple[str | None, str]:
    reported = getattr(raw, "cost", None)
    if isinstance(reported, dict) and reported.get("currency") == "USD":
        try:
            value = Decimal(str(reported["total_cost"]))
            if value.is_finite() and value >= 0:
                return str(value), "provider_reported"
        except (KeyError, InvalidOperation, ValueError):
            pass
    if inputs is not None and outputs is not None:
        try:
            input_rate = Decimal(os.environ["SIP_MODEL_INPUT_USD_PER_MILLION"])
            output_rate = Decimal(os.environ["SIP_MODEL_OUTPUT_USD_PER_MILLION"])
            if all(rate.is_finite() and rate >= 0 for rate in (input_rate, output_rate)):
                cost = (inputs * input_rate + outputs * output_rate) / Decimal(1_000_000)
                return str(cost), "configured_token_estimate"
        except (KeyError, InvalidOperation, ValueError):
            pass
    return None, "unknown"
